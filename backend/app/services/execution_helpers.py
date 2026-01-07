"""
Execution Helpers for Custom Strategy Code.

Provides safe, tracked access to LLM and tools from user-defined strategy code.
This is the primary API that custom strategies interact with.
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging

from langchain_core.language_models import BaseChatModel
from langchain.tools import BaseTool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage

logger = logging.getLogger(__name__)


@dataclass
class ExecutionStep:
    """A single step in the execution trace"""
    step_type: str  # "thought", "tool_call", "tool_result", "llm_call", "error"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_type": self.step_type,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ExecutionResult:
    """Result of custom strategy execution"""
    output: str
    tokens_input: int = 0
    tokens_output: int = 0
    steps: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExecutionHelpers:
    """
    Helper class providing safe, tracked access to LLM and tools for custom strategies.

    This class is injected into the custom strategy execution namespace and provides:
    - Tracked LLM calls with token counting
    - Safe tool execution
    - Step recording for debugging/tracing
    - Streaming support

    Usage in custom strategy code:
        def execute(llm, tools, input_message, chat_history, config, helpers):
            # Record reasoning
            helpers.record_thought("Processing user input...")

            # Make LLM call with tracking
            response = helpers.call_llm([
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": input_message}
            ])

            # Call a tool by name
            result = helpers.call_tool("calculator", {"expression": "2+2"})

            # Return result
            return ExecutionResult(output=response, ...)
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: List[BaseTool],
        stream_callback: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize execution helpers.

        Args:
            llm: LangChain chat model instance
            tools: List of LangChain BaseTool instances
            stream_callback: Optional callback for streaming tokens
        """
        self._llm = llm
        self._tools = {tool.name: tool for tool in tools}
        self._tools_list = tools
        self._stream_callback = stream_callback
        self._steps: List[ExecutionStep] = []
        self._tokens_input = 0
        self._tokens_output = 0

    def record_thought(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a reasoning/thought step.

        Args:
            content: The thought content to record
            metadata: Optional additional metadata
        """
        step = ExecutionStep(
            step_type="thought",
            content=content,
            metadata=metadata or {}
        )
        self._steps.append(step)
        logger.debug(f"Recorded thought: {content[:100]}...")

    def record_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a tool call step (called automatically by call_tool).

        Args:
            tool_name: Name of the tool being called
            tool_input: Input parameters for the tool
            metadata: Optional additional metadata
        """
        step = ExecutionStep(
            step_type="tool_call",
            content=f"Calling {tool_name}",
            metadata={
                "tool_name": tool_name,
                "tool_input": tool_input,
                **(metadata or {})
            }
        )
        self._steps.append(step)

    def record_tool_result(
        self,
        tool_name: str,
        result: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a tool result step (called automatically by call_tool).

        Args:
            tool_name: Name of the tool that returned the result
            result: The tool's output
            metadata: Optional additional metadata
        """
        step = ExecutionStep(
            step_type="tool_result",
            content=result[:1000] if len(result) > 1000 else result,
            metadata={
                "tool_name": tool_name,
                "full_length": len(result),
                **(metadata or {})
            }
        )
        self._steps.append(step)

    def call_llm(self, messages: List[Dict[str, str]]) -> str:
        """
        Make an LLM call with tracking.

        Args:
            messages: List of message dicts with "role" and "content" keys
                      Roles: "system", "user", "assistant"

        Returns:
            The LLM's response as a string

        Example:
            response = helpers.call_llm([
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello!"}
            ])
        """
        # Convert dict messages to LangChain message objects
        lc_messages: List[BaseMessage] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        # Record the call
        step = ExecutionStep(
            step_type="llm_call",
            content=f"LLM call with {len(messages)} messages",
            metadata={
                "message_count": len(messages),
                "last_message_preview": messages[-1]["content"][:200] if messages else ""
            }
        )
        self._steps.append(step)

        # Make the call
        try:
            response = self._llm.invoke(lc_messages)

            # Extract token usage if available
            if hasattr(response, "response_metadata"):
                usage = response.response_metadata.get("usage", {})
                if usage:
                    self._tokens_input += usage.get("prompt_tokens", 0)
                    self._tokens_output += usage.get("completion_tokens", 0)

            # Handle streaming callback
            content = response.content if hasattr(response, "content") else str(response)
            if self._stream_callback:
                self._stream_callback(content)

            return content

        except Exception as e:
            error_step = ExecutionStep(
                step_type="error",
                content=f"LLM call failed: {str(e)}",
                metadata={"error_type": type(e).__name__}
            )
            self._steps.append(error_step)
            raise

    def call_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Execute a tool by name with tracking.

        Args:
            tool_name: Name of the tool to call
            tool_input: Input parameters for the tool

        Returns:
            The tool's result as a string

        Raises:
            ValueError: If tool not found

        Example:
            result = helpers.call_tool("calculator", {"expression": "2 + 2"})
        """
        if tool_name not in self._tools:
            available = list(self._tools.keys())
            raise ValueError(f"Tool '{tool_name}' not found. Available: {available}")

        tool = self._tools[tool_name]

        # Record the call
        self.record_tool_call(tool_name, tool_input)

        try:
            # Execute the tool
            result = tool.invoke(tool_input)

            # Convert to string if needed
            result_str = str(result) if not isinstance(result, str) else result

            # Record the result
            self.record_tool_result(tool_name, result_str)

            return result_str

        except Exception as e:
            error_msg = f"Tool '{tool_name}' failed: {str(e)}"
            error_step = ExecutionStep(
                step_type="error",
                content=error_msg,
                metadata={
                    "tool_name": tool_name,
                    "error_type": type(e).__name__
                }
            )
            self._steps.append(error_step)
            raise ValueError(error_msg) from e

    def stream_token(self, token: str) -> None:
        """
        Emit a streaming token to the client.

        Args:
            token: Token string to stream
        """
        if self._stream_callback:
            self._stream_callback(token)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            BaseTool instance or None if not found
        """
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        """
        List available tools with their descriptions.

        Returns:
            List of dicts with "name" and "description" keys
        """
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self._tools_list
        ]

    def get_token_usage(self) -> Dict[str, int]:
        """
        Get current token usage.

        Returns:
            Dict with "input" and "output" token counts
        """
        return {
            "input": self._tokens_input,
            "output": self._tokens_output
        }

    def get_recorded_steps(self) -> List[Dict[str, Any]]:
        """
        Get all recorded execution steps.

        Returns:
            List of step dicts with type, content, timestamp, metadata
        """
        return [step.to_dict() for step in self._steps]

    def format_tools_for_prompt(self) -> str:
        """
        Format available tools for inclusion in a prompt.

        Returns:
            Formatted string describing available tools
        """
        lines = []
        for tool in self._tools_list:
            lines.append(f"- {tool.name}: {tool.description}")
        return "\n".join(lines)

    def create_result(
        self,
        output: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Create an ExecutionResult with current state.

        Args:
            output: The final output string
            metadata: Optional additional metadata

        Returns:
            ExecutionResult instance
        """
        return ExecutionResult(
            output=output,
            tokens_input=self._tokens_input,
            tokens_output=self._tokens_output,
            steps=self.get_recorded_steps(),
            metadata=metadata or {}
        )
