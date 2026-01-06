"""
Agent Executor Service for Running LangChain Agents.

This is the core service that orchestrates agent execution:
- Loads agent configuration from database
- Creates LLM instance via LLMProviderAdapter
- Loads and wraps tools via ToolLoader
- Creates appropriate LangChain agent (ReAct or Plan-and-Execute)
- Executes agent with session recording
- Handles errors and returns structured results
"""
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from sqlalchemy.orm import Session as DBSession
import logging
import time

# LangChain imports
from langchain.agents import AgentExecutor as LangChainAgentExecutor
from langchain.agents import create_react_agent, create_tool_calling_agent
from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.tools import BaseTool

# Local imports
from ..models.agent import Agent, AgentVersion, AgentType
from ..models.mcp_server import MCPServerConfig
from ..models.session import Session, SessionStatus, TraceStepType
from .llm_adapter import LLMProviderAdapter, LLMAdapterError, create_llm_from_agent_config
from .tool_wrapper import ToolLoader, load_agent_tools
from .mcp_client import MCPConnectionPool
from .mcp_tool_wrapper import create_mcp_tools_for_agent, MCPToolWrapper
from .session_recorder import SessionRecorder, create_session_recorder
from .memory import ConversationMemoryService
from ..encryption import decrypt_api_key
import json
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of agent execution"""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    session_id: Optional[int] = None
    tokens_input: int = 0
    tokens_output: int = 0
    total_latency_ms: int = 0
    steps: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.steps is None:
            self.steps = []


class AgentExecutorError(Exception):
    """Base exception for agent executor errors"""
    pass


class AgentNotFoundError(AgentExecutorError):
    """Exception raised when agent is not found"""
    pass


class AgentConfigurationError(AgentExecutorError):
    """Exception raised when agent configuration is invalid"""
    pass


class AgentExecutionTimeoutError(AgentExecutorError):
    """Exception raised when agent execution times out"""
    pass


# Default ReAct prompt template
REACT_PROMPT_TEMPLATE = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""


# Models that support tool calling (function calling)
# These models should use create_tool_calling_agent instead of create_react_agent
TOOL_CALLING_MODELS = {
    # OpenAI models with tool calling support
    "gpt-4", "gpt-4-turbo", "gpt-4-turbo-preview", "gpt-4o", "gpt-4o-mini",
    "gpt-3.5-turbo", "gpt-3.5-turbo-0125", "gpt-3.5-turbo-1106",
    # o1/o3 series
    "o1", "o1-preview", "o1-mini", "o3", "o3-mini",
    # Anthropic models with tool calling support
    "claude-3-5-sonnet-20241022", "claude-3-sonnet-20240229",
    "claude-3-opus-20240229", "claude-3-haiku-20240307",
    "claude-3-5-haiku-20241022",
}


def supports_tool_calling(model_name: str) -> bool:
    """
    Check if a model supports native tool calling (function calling).

    Args:
        model_name: The model name/ID

    Returns:
        True if the model supports tool calling
    """
    model_lower = model_name.lower()

    # Check exact matches first
    if model_lower in TOOL_CALLING_MODELS:
        return True

    # Check prefixes for model families
    # GPT-4 variants
    if model_lower.startswith(("gpt-4", "gpt-3.5-turbo")):
        return True

    # o1/o3 series
    if model_lower.startswith(("o1", "o3")):
        return True

    # Claude 3 models
    if model_lower.startswith("claude-3"):
        return True

    return False


class AgentExecutorService:
    """
    Service for executing LangChain agents.

    This service handles the complete lifecycle of agent execution:
    1. Load agent and version configuration
    2. Create LLM instance
    3. Load and wrap tools
    4. Build LangChain agent
    5. Execute with session recording
    6. Return structured result

    Usage:
        service = AgentExecutorService(db, user_id=1)
        result = service.invoke(
            agent_id=1,
            input_message="What is the weather in Tokyo?",
            session_id=None  # Creates new session
        )
        if result.success:
            print(f"Answer: {result.output}")
        else:
            print(f"Error: {result.error}")
    """

    def __init__(
        self,
        db: DBSession,
        user_id: int
    ):
        """
        Initialize agent executor service.

        Args:
            db: Database session
            user_id: User ID for access control
        """
        self.db = db
        self.user_id = user_id

    def invoke(
        self,
        agent_id: int,
        input_message: str,
        session_id: Optional[int] = None,
        config_override: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None
    ) -> ExecutionResult:
        """
        Invoke an agent with a message (sync wrapper for async invoke).

        Args:
            agent_id: ID of the agent to invoke
            input_message: User's input message
            session_id: Optional existing session ID to continue
            config_override: Optional configuration overrides
            timeout_seconds: Optional execution timeout (default from agent config)

        Returns:
            ExecutionResult with output or error
        """
        # Run the async version in an event loop
        try:
            loop = asyncio.get_running_loop()
            # Already in async context - use run_coroutine_threadsafe
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.invoke_async(
                        agent_id, input_message, session_id,
                        config_override, timeout_seconds
                    )
                )
                return future.result()
        except RuntimeError:
            # No running loop - create one
            return asyncio.run(
                self.invoke_async(
                    agent_id, input_message, session_id,
                    config_override, timeout_seconds
                )
            )

    async def invoke_async(
        self,
        agent_id: int,
        input_message: str,
        session_id: Optional[int] = None,
        config_override: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None
    ) -> ExecutionResult:
        """
        Invoke an agent with a message (async version with MCP support).

        Args:
            agent_id: ID of the agent to invoke
            input_message: User's input message
            session_id: Optional existing session ID to continue
            config_override: Optional configuration overrides
            timeout_seconds: Optional execution timeout (default from agent config)

        Returns:
            ExecutionResult with output or error

        Raises:
            AgentNotFoundError: If agent not found
            AgentConfigurationError: If agent misconfigured
        """
        start_time = time.time()
        mcp_pool = None

        # Load agent
        agent = self._load_agent(agent_id)
        version = self._get_agent_version(agent)
        config = self._merge_config(version.config, config_override)

        # Determine timeout
        effective_timeout = timeout_seconds or config.get("timeout_seconds", 30)

        # Create session recorder
        recorder = create_session_recorder(
            db=self.db,
            agent_id=agent_id,
            user_id=self.user_id,
            agent_version_id=version.id,
            session_id=session_id
        )

        try:
            # Start or resume session
            session = recorder.start_session(
                title=f"Execution of {agent.name}",
                metadata={"input_preview": input_message[:100]}
            )

            # Record user message
            recorder.record_user_message(input_message)

            # Create LLM
            llm = self._create_llm(config)
            recorder.record_trace_step(
                TraceStepType.THOUGHT,
                content=f"Created LLM: {config.get('llm_config', {}).get('model', 'unknown')}"
            )

            # Load regular tools
            tools = self._load_tools(agent_id, config)

            # Load MCP tools (if any MCP servers are assigned)
            mcp_pool = MCPConnectionPool()
            mcp_tools = await self._load_mcp_tools(agent_id, mcp_pool, recorder)

            # Combine all tools
            all_tools = tools + mcp_tools

            if all_tools:
                regular_count = len(tools)
                mcp_count = len(mcp_tools)
                tool_names = [t.name for t in all_tools]
                recorder.record_trace_step(
                    TraceStepType.THOUGHT,
                    content=f"Loaded {len(all_tools)} tools ({regular_count} regular, {mcp_count} MCP): {tool_names}"
                )

            # Load chat history if continuing a session
            chat_history = []
            if session_id:
                memory_config = config.get("memory_config", {"type": "buffer", "context_window": 10})
                memory_service = ConversationMemoryService(self.db)
                chat_history = memory_service.load_chat_history(session_id, memory_config)
                if chat_history:
                    recorder.record_trace_step(
                        TraceStepType.THOUGHT,
                        content=f"Loaded {len(chat_history)} messages from chat history"
                    )

            # Build and execute agent
            result = self._execute_agent(
                agent_type=agent.agent_type,
                llm=llm,
                tools=all_tools,
                input_message=input_message,
                config=config,
                recorder=recorder,
                timeout_seconds=effective_timeout,
                chat_history=chat_history
            )

            # Calculate metrics
            total_latency = int((time.time() - start_time) * 1000)

            # Record assistant message and finish session
            recorder.record_assistant_message(result.output or "")
            recorder.finish_session(
                status=SessionStatus.COMPLETED,
                output=result.output,
                tokens_input=result.tokens_input,
                tokens_output=result.tokens_output
            )

            return ExecutionResult(
                success=True,
                output=result.output,
                session_id=session.id,
                tokens_input=result.tokens_input,
                tokens_output=result.tokens_output,
                total_latency_ms=total_latency,
                steps=result.steps
            )

        except AgentExecutionTimeoutError as e:
            total_latency = int((time.time() - start_time) * 1000)
            recorder.fail_session(str(e), error_type="timeout")
            return ExecutionResult(
                success=False,
                error=str(e),
                error_type="timeout",
                session_id=recorder.session_id,
                total_latency_ms=total_latency
            )

        except Exception as e:
            total_latency = int((time.time() - start_time) * 1000)
            error_type = type(e).__name__
            logger.exception(f"Agent execution failed: {str(e)}")

            try:
                recorder.fail_session(str(e), error_type=error_type)
            except Exception:
                pass  # Session might not have started

            return ExecutionResult(
                success=False,
                error=str(e),
                error_type=error_type,
                session_id=recorder.session_id if recorder._session else None,
                total_latency_ms=total_latency
            )

        finally:
            # Clean up MCP connections
            if mcp_pool:
                try:
                    await mcp_pool.close_all()
                except Exception as e:
                    logger.warning(f"Error closing MCP connections: {e}")

    def _load_agent(self, agent_id: int) -> Agent:
        """Load agent from database with access validation"""
        agent = self.db.query(Agent).filter(
            Agent.id == agent_id,
            Agent.user_id == self.user_id,
            Agent.is_active == True
        ).first()

        if not agent:
            raise AgentNotFoundError(f"Agent {agent_id} not found or not accessible")

        return agent

    def _get_agent_version(self, agent: Agent) -> AgentVersion:
        """Get the current version of an agent"""
        if agent.current_version:
            return agent.current_version

        # Fallback to latest version
        version = self.db.query(AgentVersion).filter(
            AgentVersion.agent_id == agent.id
        ).order_by(AgentVersion.version_number.desc()).first()

        if not version:
            raise AgentConfigurationError(
                f"Agent {agent.id} has no versions configured"
            )

        return version

    def _merge_config(
        self,
        base_config: Dict[str, Any],
        override: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge base configuration with overrides"""
        if not override:
            return base_config

        merged = dict(base_config)

        # Deep merge for nested configs
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value

        return merged

    def _create_llm(self, config: Dict[str, Any]):
        """Create LLM instance from configuration"""
        llm_config = config.get("llm_config", {})

        if not llm_config.get("provider_id"):
            raise AgentConfigurationError(
                "Agent configuration missing provider_id in llm_config"
            )

        return create_llm_from_agent_config(
            db=self.db,
            user_id=self.user_id,
            llm_config=llm_config
        )

    def _load_tools(
        self,
        agent_id: int,
        config: Dict[str, Any]
    ) -> List[BaseTool]:
        """Load regular tools for the agent (non-MCP)"""
        tool_loader = ToolLoader(self.db)

        # First try to load tools assigned to the agent
        tools = tool_loader.load_tools_for_agent(agent_id, self.user_id)

        # Also load tools specified in config by ID
        tool_ids = config.get("tool_ids", [])
        if tool_ids:
            config_tools = tool_loader.load_tools_by_ids(tool_ids, self.user_id)
            # Add tools not already in the list
            existing_names = {t.name for t in tools}
            for tool in config_tools:
                if tool.name not in existing_names:
                    tools.append(tool)

        return tools

    def _get_mcp_servers_for_agent(self, agent_id: int) -> List[MCPServerConfig]:
        """Get MCP servers assigned to an agent"""
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return []

        # Load MCP servers through the relationship
        return [s for s in agent.mcp_servers if s.is_active]

    def _decrypt_mcp_env_vars(
        self,
        servers: List[MCPServerConfig]
    ) -> Dict[int, Dict[str, str]]:
        """Decrypt environment variables for MCP servers"""
        result = {}
        for server in servers:
            if server.encrypted_env_vars:
                try:
                    decrypted = decrypt_api_key(server.encrypted_env_vars)
                    result[server.id] = json.loads(decrypted)
                except Exception as e:
                    logger.warning(f"Failed to decrypt env vars for MCP server {server.id}: {e}")
        return result

    async def _load_mcp_tools(
        self,
        agent_id: int,
        mcp_pool: MCPConnectionPool,
        recorder: SessionRecorder
    ) -> List[MCPToolWrapper]:
        """Load MCP tools for the agent asynchronously"""
        mcp_servers = self._get_mcp_servers_for_agent(agent_id)

        if not mcp_servers:
            return []

        # Decrypt environment variables
        decrypted_env_vars = self._decrypt_mcp_env_vars(mcp_servers)

        # Create MCP tools
        mcp_tools, errors = await create_mcp_tools_for_agent(
            configs=mcp_servers,
            connection_pool=mcp_pool,
            decrypted_env_vars=decrypted_env_vars
        )

        # Log any errors
        for server_id, error_msg in errors.items():
            recorder.record_trace_step(
                TraceStepType.ERROR,
                content=f"Failed to connect to MCP server {server_id}: {error_msg}"
            )

        return mcp_tools

    def _execute_agent(
        self,
        agent_type: AgentType,
        llm,
        tools: List[BaseTool],
        input_message: str,
        config: Dict[str, Any],
        recorder: SessionRecorder,
        timeout_seconds: int,
        chat_history: List = None
    ) -> ExecutionResult:
        """Execute the appropriate agent type"""
        if chat_history is None:
            chat_history = []

        if agent_type == AgentType.REACT:
            return self._execute_react_agent(
                llm, tools, input_message, config, recorder, timeout_seconds, chat_history
            )
        elif agent_type == AgentType.PLAN_AND_EXECUTE:
            return self._execute_plan_and_execute_agent(
                llm, tools, input_message, config, recorder, timeout_seconds, chat_history
            )
        elif agent_type == AgentType.CONVERSATIONAL:
            return self._execute_conversational_agent(
                llm, tools, input_message, config, recorder, timeout_seconds, chat_history
            )
        else:
            raise AgentConfigurationError(
                f"Unsupported agent type: {agent_type}"
            )

    def _execute_react_agent(
        self,
        llm,
        tools: List[BaseTool],
        input_message: str,
        config: Dict[str, Any],
        recorder: SessionRecorder,
        timeout_seconds: int,
        chat_history: List = None
    ) -> ExecutionResult:
        """Execute ReAct agent (uses tool-calling for supported models)"""
        if chat_history is None:
            chat_history = []

        # Get model name from config
        model_name = config.get("llm_config", {}).get("model", "")
        system_prompt = config.get("system_prompt", "You are a helpful assistant.")

        # Check if model supports native tool calling
        use_tool_calling = supports_tool_calling(model_name)

        if use_tool_calling and tools:
            logger.info(f"Using tool-calling agent for model {model_name}")
            return self._execute_tool_calling_agent(
                llm, tools, input_message, system_prompt, config, recorder, timeout_seconds, chat_history
            )
        else:
            logger.info(f"Using text-based ReAct agent for model {model_name}")
            return self._execute_text_react_agent(
                llm, tools, input_message, config, recorder, timeout_seconds, chat_history
            )

    def _execute_tool_calling_agent(
        self,
        llm,
        tools: List[BaseTool],
        input_message: str,
        system_prompt: str,
        config: Dict[str, Any],
        recorder: SessionRecorder,
        timeout_seconds: int,
        chat_history: List = None
    ) -> ExecutionResult:
        """Execute agent using native tool calling (function calling) API"""
        if chat_history is None:
            chat_history = []

        # Create chat prompt for tool-calling agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Create tool-calling agent
        agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)

        # Create executor
        executor = LangChainAgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=config.get("max_iterations", 10),
            max_execution_time=timeout_seconds,
            return_intermediate_steps=True
        )

        # Execute with chat history
        result = executor.invoke({"input": input_message, "chat_history": chat_history})

        # Extract steps
        steps = []
        intermediate_steps = result.get("intermediate_steps", [])
        for action, observation in intermediate_steps:
            # Record tool call
            recorder.record_tool_call(
                tool_name=action.tool,
                tool_input=action.tool_input if isinstance(action.tool_input, dict) else {"input": action.tool_input}
            )
            # Record tool result
            recorder.record_tool_result(
                tool_name=action.tool,
                tool_output=str(observation)
            )
            steps.append({
                "step_type": "tool_call",
                "tool_name": action.tool,
                "tool_input": action.tool_input if isinstance(action.tool_input, dict) else {"input": action.tool_input},
                "tool_output": str(observation),
                "content": None,
                "latency_ms": None,
            })

        output = result.get("output", "")

        # Estimate token usage (rough approximation)
        tokens_input = len(input_message.split()) * 2
        tokens_output = len(output.split()) * 2

        return ExecutionResult(
            success=True,
            output=output,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            steps=steps
        )

    def _execute_text_react_agent(
        self,
        llm,
        tools: List[BaseTool],
        input_message: str,
        config: Dict[str, Any],
        recorder: SessionRecorder,
        timeout_seconds: int,
        chat_history: List = None
    ) -> ExecutionResult:
        """Execute text-based ReAct agent (for models without tool calling)"""
        if chat_history is None:
            chat_history = []

        # Get or create prompt
        system_prompt = config.get("system_prompt", "")
        prompt_template = config.get("prompt_template", REACT_PROMPT_TEMPLATE)

        if system_prompt:
            prompt_template = f"{system_prompt}\n\n{prompt_template}"

        # Prepend chat history to input if available
        if chat_history:
            history_text = "\n".join([
                f"{'Human' if hasattr(msg, 'type') and msg.type == 'human' else 'Assistant'}: {msg.content}"
                for msg in chat_history
            ])
            input_message = f"Previous conversation:\n{history_text}\n\nCurrent question: {input_message}"

        prompt = PromptTemplate.from_template(prompt_template)

        # Create ReAct agent
        agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

        # Create executor with callbacks for tracing
        executor = LangChainAgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=config.get("max_iterations", 10),
            max_execution_time=timeout_seconds,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )

        # Execute
        result = executor.invoke({"input": input_message})

        # Extract steps
        steps = []
        intermediate_steps = result.get("intermediate_steps", [])
        for action, observation in intermediate_steps:
            # Record tool call
            recorder.record_tool_call(
                tool_name=action.tool,
                tool_input=action.tool_input if isinstance(action.tool_input, dict) else {"input": action.tool_input}
            )
            # Record tool result
            recorder.record_tool_result(
                tool_name=action.tool,
                tool_output=str(observation)
            )
            steps.append({
                "step_type": "tool_call",
                "tool_name": action.tool,
                "tool_input": action.tool_input if isinstance(action.tool_input, dict) else {"input": action.tool_input},
                "tool_output": str(observation),
                "content": None,
                "latency_ms": None,
            })

        output = result.get("output", "")

        # Estimate token usage (rough approximation)
        tokens_input = len(input_message.split()) * 2  # Rough estimate
        tokens_output = len(output.split()) * 2

        return ExecutionResult(
            success=True,
            output=output,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            steps=steps
        )

    def _execute_plan_and_execute_agent(
        self,
        llm,
        tools: List[BaseTool],
        input_message: str,
        config: Dict[str, Any],
        recorder: SessionRecorder,
        timeout_seconds: int,
        chat_history: List = None
    ) -> ExecutionResult:
        """Execute Plan-and-Execute agent"""
        if chat_history is None:
            chat_history = []

        try:
            from langchain_experimental.plan_and_execute import (
                PlanAndExecute,
                load_agent_executor,
                load_chat_planner
            )
        except ImportError:
            raise AgentConfigurationError(
                "langchain-experimental not installed. Required for Plan-and-Execute agents."
            )

        # Prepend chat history to input if available
        if chat_history:
            history_text = "\n".join([
                f"{'Human' if hasattr(msg, 'type') and msg.type == 'human' else 'Assistant'}: {msg.content}"
                for msg in chat_history
            ])
            input_message = f"Previous conversation:\n{history_text}\n\nCurrent question: {input_message}"

        # Create planner and executor
        planner = load_chat_planner(llm)
        executor_agent = load_agent_executor(llm, tools, verbose=True)

        # Create Plan-and-Execute agent
        agent = PlanAndExecute(
            planner=planner,
            executor=executor_agent,
            verbose=True
        )

        # Record that we're using plan-and-execute
        recorder.record_thought("Using Plan-and-Execute strategy")

        # Execute with timeout handling
        start_time = time.time()
        try:
            result = agent.run(input_message)
        except Exception as e:
            if time.time() - start_time > timeout_seconds:
                raise AgentExecutionTimeoutError(
                    f"Agent execution timed out after {timeout_seconds}s"
                )
            raise

        # Estimate token usage
        tokens_input = len(input_message.split()) * 2
        tokens_output = len(result.split()) * 2

        return ExecutionResult(
            success=True,
            output=result,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            steps=[]
        )

    def _execute_conversational_agent(
        self,
        llm,
        tools: List[BaseTool],
        input_message: str,
        config: Dict[str, Any],
        recorder: SessionRecorder,
        timeout_seconds: int,
        chat_history: List = None
    ) -> ExecutionResult:
        """Execute Conversational agent (simple chat without tools)"""
        if chat_history is None:
            chat_history = []

        system_prompt = config.get("system_prompt", "You are a helpful assistant.")

        # Build messages list with system prompt, chat history, and current message
        messages = [SystemMessage(content=system_prompt)]

        # Add chat history
        for msg in chat_history:
            messages.append(msg)

        # Add current user message
        messages.append(HumanMessage(content=input_message))

        # Simple LLM invocation
        response = llm.invoke(messages)

        output = response.content if hasattr(response, 'content') else str(response)

        # Get token usage if available
        tokens_input = 0
        tokens_output = 0
        if hasattr(response, 'usage_metadata'):
            usage = response.usage_metadata
            tokens_input = getattr(usage, 'input_tokens', 0)
            tokens_output = getattr(usage, 'output_tokens', 0)

        return ExecutionResult(
            success=True,
            output=output,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            steps=[]
        )


def invoke_agent(
    db: DBSession,
    user_id: int,
    agent_id: int,
    input_message: str,
    session_id: Optional[int] = None,
    config_override: Optional[Dict[str, Any]] = None,
    timeout_seconds: Optional[int] = None
) -> ExecutionResult:
    """
    Convenience function to invoke an agent.

    Args:
        db: Database session
        user_id: User ID
        agent_id: Agent ID
        input_message: User's input message
        session_id: Optional existing session ID
        config_override: Optional config overrides
        timeout_seconds: Optional timeout

    Returns:
        ExecutionResult
    """
    service = AgentExecutorService(db, user_id)
    return service.invoke(
        agent_id=agent_id,
        input_message=input_message,
        session_id=session_id,
        config_override=config_override,
        timeout_seconds=timeout_seconds
    )
