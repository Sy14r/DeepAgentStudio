"""
CodeAct Executor Service.

Implements the true CodeAct paradigm where agents write executable Python code
as their action language, with tool functions available directly in the execution namespace.

Based on:
- Wang et al., "Executable Code Actions Elicit Better LLM Agents" (ICML 2024)
- The CodeAct architecture: Agent → Code → Execute → Observation → Iterate

Key differences from ReAct:
- Agent outputs Python code blocks instead of using LangChain tool-calling
- Code is executed directly with tool functions injected into namespace
- Observations are stdout/stderr/return values from code execution
- More flexible: loops, conditionals, error handling in agent's code
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from io import StringIO
import re
import sys
import json
import math
import random
import time as time_module
import datetime
import collections
import logging
import traceback

from sqlalchemy.orm import Session as DBSession
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain.callbacks.base import BaseCallbackHandler

from .workspace import WorkspaceService, get_workspace_service
from .web_tools import web_search, web_fetch
from ..models.session import SpanType, SpanStatus

logger = logging.getLogger(__name__)


# Safe builtins allowed in CodeAct execution
CODEACT_SAFE_BUILTINS = {
    # Type constructors
    "bool": bool,
    "int": int,
    "float": float,
    "str": str,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "frozenset": frozenset,
    "bytes": bytes,
    "bytearray": bytearray,

    # Built-in functions
    "abs": abs,
    "all": all,
    "any": any,
    "bin": bin,
    "callable": callable,
    "chr": chr,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "format": format,
    "hasattr": hasattr,
    "hash": hash,
    "hex": hex,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "iter": iter,
    "len": len,
    "map": map,
    "max": max,
    "min": min,
    "next": next,
    "oct": oct,
    "ord": ord,
    "pow": pow,
    "print": print,  # Captured to stdout
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "sorted": sorted,
    "sum": sum,
    "zip": zip,

    # Exceptions for error handling
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    "AttributeError": AttributeError,
    "RuntimeError": RuntimeError,
    "StopIteration": StopIteration,

    # Constants
    "True": True,
    "False": False,
    "None": None,
}


@dataclass
class CodeExecutionResult:
    """Result of executing a code block"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    error_message: str = ""
    error_type: str = ""


@dataclass
class CodeActStep:
    """A single step in CodeAct execution"""
    step_type: str  # "llm_response", "code_execution", "error"
    content: str
    code: str = ""
    execution_result: Optional[CodeExecutionResult] = None


@dataclass
class CodeActResult:
    """Result of CodeAct execution"""
    success: bool
    output: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    tokens_input: int = 0
    tokens_output: int = 0
    error_message: str = ""
    error_type: str = ""


class CodeActToolNamespace:
    """
    Creates a namespace of tool functions for CodeAct execution.

    Wraps workspace tools and web tools as simple Python functions
    that can be called directly from agent-generated code.
    """

    def __init__(
        self,
        db: DBSession,
        session_id: int,
        additional_tools: Optional[List] = None
    ):
        """
        Initialize the tool namespace.

        Args:
            db: Database session
            session_id: Session ID for workspace context
            additional_tools: Optional list of additional LangChain tools
        """
        self.db = db
        self.session_id = session_id
        self.workspace_service = get_workspace_service(db)
        self.additional_tools = additional_tools or []

        # Ensure workspace exists
        self.workspace_service.create_workspace(session_id)

    def get_namespace(self) -> Dict[str, Callable]:
        """
        Get the complete namespace of available functions.

        Returns:
            Dictionary mapping function names to callable functions
        """
        namespace = {}

        # Add workspace tools
        namespace.update(self._create_workspace_functions())

        # Add web tools
        namespace.update(self._create_web_functions())

        # Add any additional tools as simple functions
        for tool in self.additional_tools:
            namespace[tool.name] = self._wrap_langchain_tool(tool)

        return namespace

    def _create_workspace_functions(self) -> Dict[str, Callable]:
        """Create workspace tool functions with session context baked in."""
        ws = self.workspace_service
        sid = self.session_id

        def file_read(path: str, start_line: int = None, end_line: int = None) -> str:
            """Read contents of a file from the workspace."""
            result = ws.read_file(sid, path, start_line, end_line)
            if result.success:
                return result.data["content"]
            else:
                raise IOError(f"file_read error: {result.error}")

        def file_write(path: str, content: str, create_dirs: bool = True) -> str:
            """Write content to a file in the workspace."""
            result = ws.write_file(sid, path, content, create_dirs)
            if result.success:
                return result.data["message"]
            else:
                raise IOError(f"file_write error: {result.error}")

        def file_edit(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
            """Edit a file using string replacement."""
            result = ws.edit_file(sid, path, old_string, new_string, replace_all)
            if result.success:
                return result.data["message"]
            else:
                raise IOError(f"file_edit error: {result.error}")

        def file_list(pattern: str = "*", include_hidden: bool = False) -> str:
            """List files in workspace matching a pattern. Returns JSON string."""
            result = ws.list_files(sid, pattern, include_hidden)
            if result.success:
                return json.dumps(result.data, indent=2)
            else:
                raise IOError(f"file_list error: {result.error}")

        def file_search(pattern: str, file_pattern: str = "**/*",
                       max_results: int = 50, context_lines: int = 2) -> str:
            """Search file contents using regex. Returns JSON string."""
            result = ws.search_files(sid, pattern, file_pattern, max_results, context_lines)
            if result.success:
                return json.dumps(result.data, indent=2)
            else:
                raise IOError(f"file_search error: {result.error}")

        def task_manager(action: str, task_id: int = None, title: str = None,
                        description: str = None, status: str = None, notes: str = None) -> str:
            """Manage a task list. Actions: list, add, update, complete, remove."""
            if action == "list":
                result = ws.get_tasks(sid)
                if result.success:
                    tasks = result.data["tasks"]
                    if not tasks:
                        return "No tasks in list."
                    return json.dumps({"tasks": tasks}, indent=2)
                raise RuntimeError(f"task_manager error: {result.error}")

            elif action == "add":
                if not title:
                    raise ValueError("task_manager add requires 'title'")
                result = ws.add_task(sid, title, description)
                if result.success:
                    tasks_result = ws.get_tasks(sid)
                    return json.dumps({
                        "message": result.data["message"],
                        "tasks": tasks_result.data["tasks"] if tasks_result.success else []
                    }, indent=2)
                raise RuntimeError(f"task_manager error: {result.error}")

            elif action == "update":
                if task_id is None:
                    raise ValueError("task_manager update requires 'task_id'")
                result = ws.update_task(sid, task_id, status, notes, description)
                if result.success:
                    tasks_result = ws.get_tasks(sid)
                    return json.dumps({
                        "message": result.data["message"],
                        "tasks": tasks_result.data["tasks"] if tasks_result.success else []
                    }, indent=2)
                raise RuntimeError(f"task_manager error: {result.error}")

            elif action == "complete":
                if task_id is None:
                    raise ValueError("task_manager complete requires 'task_id'")
                result = ws.complete_task(sid, task_id, notes)
                if result.success:
                    tasks_result = ws.get_tasks(sid)
                    return json.dumps({
                        "message": result.data["message"],
                        "tasks": tasks_result.data["tasks"] if tasks_result.success else []
                    }, indent=2)
                raise RuntimeError(f"task_manager error: {result.error}")

            elif action == "remove":
                if task_id is None:
                    raise ValueError("task_manager remove requires 'task_id'")
                result = ws.remove_task(sid, task_id)
                if result.success:
                    tasks_result = ws.get_tasks(sid)
                    return json.dumps({
                        "message": result.data["message"],
                        "tasks": tasks_result.data["tasks"] if tasks_result.success else []
                    }, indent=2)
                raise RuntimeError(f"task_manager error: {result.error}")

            else:
                raise ValueError(f"Unknown action '{action}'. Use: list, add, update, complete, remove")

        def scratchpad(action: str, content: str = None, section: str = "default") -> str:
            """Manage working notes. Actions: read, write, append, clear."""
            if action == "read":
                if section == "all":
                    result = ws.get_all_scratchpads(sid)
                    if result.success:
                        sections = result.data["sections"]
                        if not sections:
                            return "Scratchpad is empty."
                        output = "# Scratchpad Contents\n\n"
                        for sec, text in sections.items():
                            output += f"## {sec}\n\n{text}\n\n"
                        return output
                else:
                    result = ws.get_scratchpad(sid, section)
                    if result.success:
                        content_val = result.data["content"]
                        if not content_val:
                            return f"Section '{section}' is empty."
                        return content_val
                raise RuntimeError(f"scratchpad error: {result.error}")

            elif action == "write":
                if content is None:
                    raise ValueError("scratchpad write requires 'content'")
                result = ws.write_scratchpad(sid, content, section)
                if result.success:
                    return result.data["message"]
                raise RuntimeError(f"scratchpad error: {result.error}")

            elif action == "append":
                if content is None:
                    raise ValueError("scratchpad append requires 'content'")
                result = ws.append_scratchpad(sid, content, section)
                if result.success:
                    return result.data["message"]
                raise RuntimeError(f"scratchpad error: {result.error}")

            elif action == "clear":
                result = ws.clear_scratchpad(sid, section if section != "default" else None)
                if result.success:
                    return result.data["message"]
                raise RuntimeError(f"scratchpad error: {result.error}")

            else:
                raise ValueError(f"Unknown action '{action}'. Use: read, write, append, clear")

        return {
            "file_read": file_read,
            "file_write": file_write,
            "file_edit": file_edit,
            "file_list": file_list,
            "file_search": file_search,
            "task_manager": task_manager,
            "scratchpad": scratchpad,
        }

    def _create_web_functions(self) -> Dict[str, Callable]:
        """Create web tool functions."""
        return {
            "web_search": web_search,
            "web_fetch": web_fetch,
        }

    def _wrap_langchain_tool(self, tool) -> Callable:
        """Wrap a LangChain tool as a simple callable function."""
        def wrapped_tool(**kwargs):
            result = tool.invoke(kwargs)
            return str(result) if not isinstance(result, str) else result
        wrapped_tool.__doc__ = tool.description
        wrapped_tool.__name__ = tool.name
        return wrapped_tool


class CodeActExecutor:
    """
    Executes the CodeAct loop: LLM generates code → execute → observe → iterate.

    The agent writes Python code in markdown code blocks, which is extracted
    and executed with tool functions available in the namespace. Output (stdout,
    return values, errors) becomes the observation for the next iteration.
    """

    # Pattern to extract Python code blocks from LLM response
    # Handles various formats:
    # - ```python\ncode```
    # - ```\ncode```
    # - ```python code``` (no newline)
    # - ```py\ncode```
    CODE_BLOCK_PATTERN = re.compile(
        r'```(?:python|py)?\s*\n?(.*?)```',
        re.DOTALL | re.IGNORECASE
    )

    def __init__(
        self,
        llm: BaseChatModel,
        tool_namespace: CodeActToolNamespace,
        max_iterations: int = 15,
        execution_timeout: float = 30.0,
        on_llm_response: Optional[Callable[[str], None]] = None,
        on_code_execution: Optional[Callable[[str, CodeExecutionResult], None]] = None,
        tracing_callback: Optional[BaseCallbackHandler] = None
    ):
        """
        Initialize the CodeAct executor.

        Args:
            llm: LangChain chat model instance
            tool_namespace: CodeActToolNamespace with available functions
            max_iterations: Maximum number of code→observe iterations
            execution_timeout: Timeout per code block execution (seconds)
            on_llm_response: Optional callback when LLM responds
            on_code_execution: Optional callback when code is executed
            tracing_callback: Optional tracing callback for hierarchical span recording
        """
        self.llm = llm
        self.tool_namespace = tool_namespace
        self.max_iterations = max_iterations
        self.execution_timeout = execution_timeout
        self.on_llm_response = on_llm_response
        self.on_code_execution = on_code_execution
        self.tracing_callback = tracing_callback

        # Get span recorder from tracing callback if available
        self._span_recorder = getattr(tracing_callback, 'recorder', None) if tracing_callback else None

        self._tokens_input = 0
        self._tokens_output = 0

    def execute(
        self,
        input_message: str,
        system_prompt: str,
        chat_history: Optional[List[BaseMessage]] = None
    ) -> CodeActResult:
        """
        Execute the CodeAct loop.

        Args:
            input_message: User's input message
            system_prompt: System prompt for the agent
            chat_history: Optional previous conversation history

        Returns:
            CodeActResult with final output and execution steps
        """
        if chat_history is None:
            chat_history = []

        # Build initial messages
        messages = [
            SystemMessage(content=system_prompt),
            *chat_history,
            HumanMessage(content=input_message)
        ]

        steps: List[CodeActStep] = []

        # Create root span for the entire CodeAct execution
        root_span = None
        if self._span_recorder:
            try:
                root_span = self._span_recorder.start_span(
                    span_type=SpanType.CHAIN,
                    name="CodeAct Execution",
                    depth=0,
                    input_data={"message": input_message[:500], "max_iterations": self.max_iterations}
                )
                logger.debug(f"Started CodeAct root span: {root_span.id}")
            except Exception as e:
                logger.warning(f"Failed to start root span: {e}")

        # Prepare callbacks for LLM invocation
        llm_callbacks = [self.tracing_callback] if self.tracing_callback else None

        try:
            for iteration in range(self.max_iterations):
                logger.info(f"CodeAct iteration {iteration + 1}/{self.max_iterations}")

                # Get LLM response (with tracing callback for automatic LLM span recording)
                try:
                    response = self.llm.invoke(messages, config={"callbacks": llm_callbacks} if llm_callbacks else None)
                    response_text = response.content if hasattr(response, 'content') else str(response)

                    # Track token usage
                    if hasattr(response, 'response_metadata'):
                        usage = response.response_metadata.get('usage', {})
                        self._tokens_input += usage.get('prompt_tokens', 0)
                        self._tokens_output += usage.get('completion_tokens', 0)

                except Exception as e:
                    logger.exception(f"LLM call failed in CodeAct: {e}")
                    self._end_root_span(root_span, SpanStatus.ERROR, error_message=str(e), error_type=type(e).__name__)
                    return CodeActResult(
                        success=False,
                        output="",
                        steps=[s._asdict() if hasattr(s, '_asdict') else vars(s) for s in steps],
                        tokens_input=self._tokens_input,
                        tokens_output=self._tokens_output,
                        error_message=str(e),
                        error_type=type(e).__name__
                    )

                # Callback for streaming/logging
                if self.on_llm_response:
                    self.on_llm_response(response_text)

                # Log the response for debugging
                logger.debug(f"CodeAct LLM response (first 500 chars): {response_text[:500]}")

                # Extract code blocks from response
                code_blocks = self._extract_code_blocks(response_text)
                logger.info(f"CodeAct found {len(code_blocks)} code blocks")

                # If no code blocks, this is the final answer
                if not code_blocks:
                    # Log when no code blocks found to help debug
                    if '```' in response_text:
                        logger.warning(f"CodeAct: Response contains ``` but no code blocks extracted. Response: {response_text[:300]}")
                    steps.append(CodeActStep(
                        step_type="llm_response",
                        content=response_text
                    ))
                    self._end_root_span(root_span, SpanStatus.SUCCESS, output={"response": response_text[:500]})
                    return CodeActResult(
                        success=True,
                        output=response_text,
                        steps=self._steps_to_dicts(steps),
                        tokens_input=self._tokens_input,
                        tokens_output=self._tokens_output
                    )

                # Add LLM response to messages
                messages.append(AIMessage(content=response_text))

                # Execute each code block and collect observations
                observations = []
                for code_idx, code in enumerate(code_blocks):
                    # Create TOOL span for code execution
                    code_span = None
                    if self._span_recorder and root_span:
                        try:
                            code_span = self._span_recorder.start_span(
                                span_type=SpanType.TOOL,
                                name=f"Code Execution #{iteration + 1}.{code_idx + 1}",
                                parent_span_id=root_span.id,
                                depth=1,
                                tool_name="python_exec",
                                input_data={"code": code[:1000]}
                            )
                        except Exception as e:
                            logger.warning(f"Failed to start code execution span: {e}")

                    exec_result = self._execute_code(code)
                    logger.info(f"CodeAct code exec result: success={exec_result.success}, stdout_len={len(exec_result.stdout)}, error={exec_result.error_message[:100] if exec_result.error_message else 'none'}")

                    # End code execution span
                    if code_span:
                        try:
                            self._span_recorder.end_span(
                                code_span,
                                status=SpanStatus.SUCCESS if exec_result.success else SpanStatus.ERROR,
                                output={
                                    "stdout": exec_result.stdout[:500] if exec_result.stdout else "",
                                    "stderr": exec_result.stderr[:200] if exec_result.stderr else "",
                                    "success": exec_result.success
                                },
                                error_message=exec_result.error_message if not exec_result.success else None,
                                error_type=exec_result.error_type if not exec_result.success else None
                            )
                        except Exception as e:
                            logger.warning(f"Failed to end code execution span: {e}")

                    steps.append(CodeActStep(
                        step_type="code_execution",
                        content=response_text,
                        code=code,
                        execution_result=exec_result
                    ))

                    # Callback for streaming
                    if self.on_code_execution:
                        self.on_code_execution(code, exec_result)

                    # Format observation
                    observation = self._format_observation(exec_result)
                    observations.append(observation)

                # Combine observations and add as user message (observation)
                combined_observation = "\n\n".join(observations)
                messages.append(HumanMessage(content=f"[Observation]\n{combined_observation}"))

            # Max iterations reached
            logger.warning(f"CodeAct reached max iterations ({self.max_iterations})")
            self._end_root_span(root_span, SpanStatus.SUCCESS, output={"reason": "max_iterations_reached"})
            return CodeActResult(
                success=True,
                output=f"Reached maximum iterations ({self.max_iterations}). Last response may be incomplete.",
                steps=self._steps_to_dicts(steps),
                tokens_input=self._tokens_input,
                tokens_output=self._tokens_output
            )
        except Exception as e:
            # Catch any unexpected exceptions and ensure root span is ended
            logger.exception(f"Unexpected error in CodeAct execution: {e}")
            self._end_root_span(root_span, SpanStatus.ERROR, error_message=str(e), error_type=type(e).__name__)
            raise

    def _end_root_span(
        self,
        span,
        status: SpanStatus,
        output: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None
    ) -> None:
        """Helper to end the root span with proper error handling."""
        if span and self._span_recorder:
            try:
                self._span_recorder.end_span(
                    span,
                    status=status,
                    output=output,
                    tokens_input=self._tokens_input,
                    tokens_output=self._tokens_output,
                    error_message=error_message,
                    error_type=error_type
                )
                logger.debug(f"Ended CodeAct root span: {span.id} with status {status.value}")
            except Exception as e:
                logger.warning(f"Failed to end root span: {e}")

    def _extract_code_blocks(self, text: str) -> List[str]:
        """Extract Python code blocks from markdown text."""
        matches = self.CODE_BLOCK_PATTERN.findall(text)
        # Filter out empty or whitespace-only blocks
        return [code.strip() for code in matches if code.strip()]

    def _execute_code(self, code: str) -> CodeExecutionResult:
        """
        Execute a code block in a sandboxed environment.

        Args:
            code: Python code to execute

        Returns:
            CodeExecutionResult with stdout, stderr, return value, or error
        """
        # Capture stdout/stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        captured_stdout = StringIO()
        captured_stderr = StringIO()

        try:
            sys.stdout = captured_stdout
            sys.stderr = captured_stderr

            # Create execution namespace
            namespace = self._create_execution_namespace()

            # Execute the code
            exec(code, namespace)

            stdout_value = captured_stdout.getvalue()
            stderr_value = captured_stderr.getvalue()

            # Check for a 'result' variable in namespace (optional return)
            return_value = namespace.get('result', None)

            return CodeExecutionResult(
                success=True,
                stdout=stdout_value,
                stderr=stderr_value,
                return_value=return_value
            )

        except Exception as e:
            return CodeExecutionResult(
                success=False,
                stdout=captured_stdout.getvalue(),
                stderr=captured_stderr.getvalue(),
                error_message=str(e),
                error_type=type(e).__name__
            )

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _create_execution_namespace(self) -> Dict[str, Any]:
        """Create a sandboxed execution namespace with tools and safe builtins."""
        namespace = {
            "__builtins__": CODEACT_SAFE_BUILTINS.copy(),
        }

        # Add allowed modules
        namespace["json"] = json
        namespace["math"] = math
        namespace["re"] = re
        namespace["datetime"] = datetime
        namespace["collections"] = collections
        namespace["random"] = random
        namespace["time"] = time_module

        # Add tool functions
        namespace.update(self.tool_namespace.get_namespace())

        return namespace

    def _format_observation(self, result: CodeExecutionResult) -> str:
        """Format execution result as observation text."""
        parts = []

        if result.success:
            if result.stdout:
                parts.append(f"stdout:\n{result.stdout}")
            if result.stderr:
                parts.append(f"stderr:\n{result.stderr}")
            if result.return_value is not None:
                parts.append(f"result: {result.return_value}")
            if not parts:
                parts.append("(code executed successfully with no output)")
        else:
            parts.append(f"Error ({result.error_type}): {result.error_message}")
            if result.stdout:
                parts.append(f"stdout before error:\n{result.stdout}")

        return "\n".join(parts)

    def _steps_to_dicts(self, steps: List[CodeActStep]) -> List[Dict[str, Any]]:
        """Convert steps to dictionaries for serialization."""
        result = []
        for step in steps:
            step_dict = {
                "step_type": step.step_type,
                "content": step.content[:500] if step.content else "",  # Truncate for storage
            }
            if step.code:
                step_dict["code"] = step.code
            if step.execution_result:
                step_dict["execution_result"] = {
                    "success": step.execution_result.success,
                    "stdout": step.execution_result.stdout[:1000] if step.execution_result.stdout else "",
                    "stderr": step.execution_result.stderr[:500] if step.execution_result.stderr else "",
                    "error_message": step.execution_result.error_message,
                    "error_type": step.execution_result.error_type,
                }
            result.append(step_dict)
        return result


def create_codeact_executor(
    db: DBSession,
    session_id: int,
    llm: BaseChatModel,
    additional_tools: Optional[List] = None,
    max_iterations: int = 15,
    on_llm_response: Optional[Callable[[str], None]] = None,
    on_code_execution: Optional[Callable[[str, CodeExecutionResult], None]] = None,
    tracing_callback: Optional[BaseCallbackHandler] = None
) -> CodeActExecutor:
    """
    Factory function to create a CodeAct executor.

    Args:
        db: Database session
        session_id: Session ID for workspace context
        llm: LangChain chat model instance
        additional_tools: Optional list of additional LangChain tools
        max_iterations: Maximum iterations (default 15)
        on_llm_response: Optional callback for LLM responses
        on_code_execution: Optional callback for code execution
        tracing_callback: Optional tracing callback for hierarchical span recording

    Returns:
        Configured CodeActExecutor instance
    """
    tool_namespace = CodeActToolNamespace(
        db=db,
        session_id=session_id,
        additional_tools=additional_tools
    )

    return CodeActExecutor(
        llm=llm,
        tool_namespace=tool_namespace,
        max_iterations=max_iterations,
        on_llm_response=on_llm_response,
        on_code_execution=on_code_execution,
        tracing_callback=tracing_callback
    )
