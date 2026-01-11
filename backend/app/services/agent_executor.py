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
from ..models.agent import Agent, AgentVersion
from ..models.agent_type import ExecutionStrategy
from ..models.mcp_server import MCPServerConfig
from ..models.session import Session, SessionStatus, TraceStepType
from .llm_adapter import LLMProviderAdapter, LLMAdapterError, create_llm_from_agent_config
from .tool_wrapper import ToolLoader, load_agent_tools, WORKSPACE_TOOL_CLASSES
from .mcp_client import MCPConnectionPool
from .mcp_tool_wrapper import create_mcp_tools_for_agent, MCPToolWrapper
from .session_recorder import SessionRecorder, create_session_recorder
from .tracing_callback import create_tracing_callback
from .memory import ConversationMemoryService
from .workspace_tools import create_workspace_tools, WORKSPACE_TOOL_NAMES
from .web_tools import create_web_tools, WEB_TOOL_CLASSES
from .prompt_service import PromptService, PromptNotFoundError, PromptResolutionResult
from ..encryption import decrypt_api_key
import json
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of agent execution"""
    success: bool
    output: Optional[str] = None
    content_blocks: Optional[List[Dict[str, Any]]] = None  # Multimodal content blocks
    error: Optional[str] = None
    error_type: Optional[str] = None
    session_id: Optional[int] = None
    tokens_input: int = 0
    tokens_output: int = 0
    total_latency_ms: int = 0
    cost: float = 0.0  # Cost in USD calculated from model pricing
    steps: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.steps is None:
            self.steps = []
        if self.content_blocks is None:
            self.content_blocks = []


@dataclass
class ExecutionContext:
    """
    Prepared execution context containing all resources needed for agent execution.

    This dataclass centralizes all the setup that's common between streaming
    and non-streaming execution paths, ensuring tracing is always enabled
    and reducing code duplication.
    """
    # Core resources
    agent: Any  # Agent model
    version: Any  # AgentVersion model
    config: Dict[str, Any]
    session: Any  # Session model
    recorder: Any  # SessionRecorder

    # Execution resources
    llm: Any  # LangChain LLM instance
    tools: List[Any]  # Combined list of all tools
    chat_history: List[Any]

    # Callbacks - tracing is always present
    tracing_callback: Any  # DeepAgentTracingCallback - always created

    # Optional MCP pool for cleanup
    mcp_pool: Optional[Any] = None

    # Timeout
    timeout_seconds: int = 30


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

    async def _prepare_execution(
        self,
        agent_id: int,
        input_message: str,
        session_id: Optional[int] = None,
        config_override: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        session_title: Optional[str] = None,
        session_metadata: Optional[Dict[str, Any]] = None,
        websocket: Optional[Any] = None,
        loop: Optional[Any] = None
    ) -> ExecutionContext:
        """
        Prepare all resources needed for agent execution.

        This method centralizes the common setup code that was previously
        duplicated between invoke_async() and invoke_streaming(). It always
        creates a tracing callback to ensure spans are recorded.

        Args:
            agent_id: ID of the agent to invoke
            input_message: User's input message
            session_id: Optional existing session ID to continue
            config_override: Optional configuration overrides
            timeout_seconds: Optional execution timeout
            session_title: Optional custom session title
            session_metadata: Optional additional session metadata
            websocket: Optional WebSocket for streaming span events
            loop: Optional event loop for async callback operations

        Returns:
            ExecutionContext with all prepared resources

        Raises:
            AgentNotFoundError: If agent not found
            AgentConfigurationError: If agent misconfigured
        """
        # Load agent and configuration
        agent = self._load_agent(agent_id)
        version = self._get_agent_version(agent)
        config = self._merge_config(version.config, config_override)
        effective_timeout = timeout_seconds or config.get("timeout_seconds", 30)

        # Create session recorder
        recorder = create_session_recorder(
            db=self.db,
            agent_id=agent_id,
            user_id=self.user_id,
            agent_version_id=version.id,
            session_id=session_id
        )

        # Build session metadata
        metadata = {"input_preview": input_message[:100]}
        if session_metadata:
            metadata.update(session_metadata)

        # Start or resume session
        session = recorder.start_session(
            title=session_title or f"Execution of {agent.name}",
            metadata=metadata
        )

        # Record user message
        recorder.record_user_message(input_message)

        # Create tracing callback - ALWAYS created to ensure spans are recorded
        # This is the core change: tracing is now a built-in part of the execution engine
        tracing_callback = create_tracing_callback(
            db=self.db,
            session_id=session.id,
            capture_inputs=True,
            capture_outputs=True,
            include_raw_prompts=False,
            websocket=websocket,
            loop=loop
        )

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

        # Load workspace tools if any workspace tool IDs are in config
        workspace_tools = []
        tool_ids = config.get("tool_ids", [])
        if tool_ids:
            from ..models import Tool
            workspace_tool_requested = self.db.query(Tool).filter(
                Tool.id.in_(tool_ids),
                Tool.langchain_class.in_(list(WORKSPACE_TOOL_CLASSES.keys()))
            ).first()

            if workspace_tool_requested:
                workspace_tools = create_workspace_tools(self.db, session.id)
                recorder.record_trace_step(
                    TraceStepType.THOUGHT,
                    content=f"Created {len(workspace_tools)} workspace tools for session {session.id}"
                )

        # Load web tools if any web tool IDs are in config
        web_tools = []
        if tool_ids:
            from ..models import Tool
            web_tool_requested = self.db.query(Tool).filter(
                Tool.id.in_(tool_ids),
                Tool.langchain_class.in_(list(WEB_TOOL_CLASSES.keys()))
            ).first()

            if web_tool_requested:
                web_tools = create_web_tools()
                recorder.record_trace_step(
                    TraceStepType.THOUGHT,
                    content=f"Created {len(web_tools)} web tools for research"
                )

        # Load image generation tools if any image tool IDs are in config
        image_tools = []
        if tool_ids:
            from ..models import Tool
            from .image_generation_tools import create_image_generation_tools, IMAGE_GENERATION_TOOL_CLASSES
            image_tool_requested = self.db.query(Tool).filter(
                Tool.id.in_(tool_ids),
                Tool.langchain_class.in_(list(IMAGE_GENERATION_TOOL_CLASSES.keys()))
            ).first()

            if image_tool_requested:
                image_tools = create_image_generation_tools(self.db, session.id, self.user_id)
                recorder.record_trace_step(
                    TraceStepType.THOUGHT,
                    content=f"Created {len(image_tools)} image generation tools"
                )

        # Combine all tools
        all_tools = tools + mcp_tools + workspace_tools + web_tools + image_tools

        if all_tools:
            regular_count = len(tools)
            mcp_count = len(mcp_tools)
            workspace_count = len(workspace_tools)
            web_count = len(web_tools)
            image_count = len(image_tools)
            tool_names = [t.name for t in all_tools]
            recorder.record_trace_step(
                TraceStepType.THOUGHT,
                content=f"Loaded {len(all_tools)} tools ({regular_count} regular, {mcp_count} MCP, {workspace_count} workspace, {web_count} web, {image_count} image): {tool_names}"
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

        return ExecutionContext(
            agent=agent,
            version=version,
            config=config,
            session=session,
            recorder=recorder,
            llm=llm,
            tools=all_tools,
            chat_history=chat_history,
            tracing_callback=tracing_callback,
            mcp_pool=mcp_pool,
            timeout_seconds=effective_timeout
        )

    def invoke(
        self,
        agent_id: int,
        input_message: str,
        session_id: Optional[int] = None,
        config_override: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        attachments: Optional[List[Any]] = None
    ) -> ExecutionResult:
        """
        Invoke an agent with a message (sync wrapper for async invoke).

        Args:
            agent_id: ID of the agent to invoke
            input_message: User's input message
            session_id: Optional existing session ID to continue
            config_override: Optional configuration overrides
            timeout_seconds: Optional execution timeout (default from agent config)
            attachments: Optional list of attachments (images, text files, etc.)

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
                        config_override, timeout_seconds, attachments
                    )
                )
                return future.result()
        except RuntimeError:
            # No running loop - create one
            return asyncio.run(
                self.invoke_async(
                    agent_id, input_message, session_id,
                    config_override, timeout_seconds, attachments
                )
            )

    async def invoke_async(
        self,
        agent_id: int,
        input_message: str,
        session_id: Optional[int] = None,
        config_override: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        attachments: Optional[List[Any]] = None,
        session_title: Optional[str] = None,
        session_metadata: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Invoke an agent with a message (async version with MCP support).

        Uses the shared _prepare_execution() method to set up all resources,
        ensuring tracing is always enabled.

        Args:
            agent_id: ID of the agent to invoke
            input_message: User's input message
            session_id: Optional existing session ID to continue
            config_override: Optional configuration overrides
            timeout_seconds: Optional execution timeout (default from agent config)
            attachments: Optional list of attachments (images, text files, etc.)
            session_title: Optional custom session title (defaults to "Execution of {agent.name}")
            session_metadata: Optional additional session metadata

        Returns:
            ExecutionResult with output or error

        Raises:
            AgentNotFoundError: If agent not found
            AgentConfigurationError: If agent misconfigured
        """
        start_time = time.time()
        ctx: Optional[ExecutionContext] = None

        try:
            # Prepare all execution resources (includes tracing callback)
            ctx = await self._prepare_execution(
                agent_id=agent_id,
                input_message=input_message,
                session_id=session_id,
                config_override=config_override,
                timeout_seconds=timeout_seconds,
                session_title=session_title,
                session_metadata=session_metadata
            )

            # Build and execute agent in a thread pool to avoid blocking the event loop
            # The LangChain .invoke() calls are synchronous and would block other async operations
            result = await asyncio.to_thread(
                self._execute_agent,
                execution_strategy=ctx.agent.agent_type_config.execution_strategy,
                llm=ctx.llm,
                tools=ctx.tools,
                input_message=input_message,
                config=ctx.config,
                recorder=ctx.recorder,
                timeout_seconds=ctx.timeout_seconds,
                chat_history=ctx.chat_history,
                attachments=attachments,
                tracing_callback=ctx.tracing_callback
            )

            # Calculate metrics
            total_latency = int((time.time() - start_time) * 1000)

            # Get actual token totals and cost from LLM spans (more accurate than estimates)
            actual_tokens = {"tokens_input": 0, "tokens_output": 0, "total_tokens": 0, "cost_usd": 0.0}
            if ctx.tracing_callback and hasattr(ctx.tracing_callback, 'recorder'):
                actual_tokens = ctx.tracing_callback.recorder.get_token_totals()

            # Use actual tokens if available, fall back to result values
            tokens_input = actual_tokens.get("tokens_input", 0) or result.tokens_input
            tokens_output = actual_tokens.get("tokens_output", 0) or result.tokens_output
            cost = actual_tokens.get("cost_usd", 0.0)

            # Record assistant message and finish session
            ctx.recorder.record_assistant_message(result.output or "")
            ctx.recorder.finish_session(
                status=SessionStatus.COMPLETED,
                output=result.output,
                tokens_input=tokens_input,
                tokens_output=tokens_output
            )

            return ExecutionResult(
                success=True,
                output=result.output,
                content_blocks=result.content_blocks,
                session_id=ctx.session.id,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                total_latency_ms=total_latency,
                cost=cost,
                steps=result.steps
            )

        except AgentExecutionTimeoutError as e:
            total_latency = int((time.time() - start_time) * 1000)
            if ctx:
                ctx.recorder.fail_session(str(e), error_type="timeout")
            return ExecutionResult(
                success=False,
                error=str(e),
                error_type="timeout",
                session_id=ctx.session.id if ctx else None,
                total_latency_ms=total_latency
            )

        except Exception as e:
            total_latency = int((time.time() - start_time) * 1000)
            error_type = type(e).__name__
            logger.exception(f"Agent execution failed: {str(e)}")

            if ctx:
                try:
                    ctx.recorder.fail_session(str(e), error_type=error_type)
                except Exception:
                    pass  # Session might not have started

            return ExecutionResult(
                success=False,
                error=str(e),
                error_type=error_type,
                session_id=ctx.session.id if ctx else None,
                total_latency_ms=total_latency
            )

        finally:
            # Clean up MCP connections
            if ctx and ctx.mcp_pool:
                try:
                    await ctx.mcp_pool.close_all()
                except Exception as e:
                    logger.warning(f"Error closing MCP connections: {e}")

    def _load_agent(self, agent_id: int) -> Agent:
        """Load agent from database with access validation"""
        from sqlalchemy import or_
        agent = self.db.query(Agent).filter(
            Agent.id == agent_id,
            Agent.is_active == True,
            # Allow access to user's own agents OR built-in agents
            or_(Agent.user_id == self.user_id, Agent.is_builtin == True)
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

    def _resolve_system_prompt(
        self,
        config: Dict[str, Any],
        default: str = "You are a helpful assistant."
    ) -> tuple:
        """
        Resolve the system prompt from config.

        Priority:
        1. If prompt_id is provided, load and render the prompt template
        2. Otherwise, use system_prompt from config
        3. Fall back to default

        Args:
            config: Agent configuration dictionary
            default: Default prompt if nothing else is configured

        Returns:
            Tuple of (resolved_system_prompt: str, prompt_version_id: Optional[int])
        """
        prompt_id = config.get("prompt_id")
        prompt_variables = config.get("prompt_variables", {})

        if prompt_id:
            try:
                prompt_service = PromptService(self.db)
                result = prompt_service.resolve_prompt(
                    prompt_id=prompt_id,
                    variables=prompt_variables,
                    user_id=self.user_id,
                    increment_usage=True
                )
                logger.info(f"Resolved prompt_id={prompt_id} (version_id={result.version_id}) for agent execution")
                return (result.rendered, result.version_id)
            except PromptNotFoundError as e:
                logger.warning(f"Prompt {prompt_id} not found, falling back to system_prompt: {e}")
            except Exception as e:
                logger.error(f"Error resolving prompt {prompt_id}: {e}")

        # Fall back to system_prompt config or default
        return (config.get("system_prompt") or default, None)

    def _create_llm(self, config: Dict[str, Any]):
        """Create LLM instance from configuration"""
        from ..models.llm_provider import LLMProviderConfig, LLMProviderType

        llm_config = config.get("llm_config", {})

        # If no provider_id, try to find user's provider by type
        if not llm_config.get("provider_id"):
            provider_type_str = llm_config.get("provider")
            if provider_type_str:
                # Look up user's provider of this type
                try:
                    provider_type = LLMProviderType(provider_type_str.lower())
                except ValueError:
                    raise AgentConfigurationError(
                        f"Unknown provider type: {provider_type_str}"
                    )

                provider_config = self.db.query(LLMProviderConfig).filter(
                    LLMProviderConfig.user_id == self.user_id,
                    LLMProviderConfig.provider_type == provider_type,
                    LLMProviderConfig.is_active == True
                ).first()

                if provider_config:
                    # Merge provider_id into llm_config
                    llm_config = dict(llm_config)
                    llm_config["provider_id"] = provider_config.id
                else:
                    raise AgentConfigurationError(
                        f"No active {provider_type_str} provider found. "
                        f"Please configure an LLM provider in Settings."
                    )
            else:
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

    def _create_multimodal_content(
        self,
        text_message: str,
        attachments: Optional[List[Any]] = None
    ) -> Union[str, List[Dict[str, Any]]]:
        """
        Create multimodal message content from text and attachments.

        For vision-capable models (GPT-4o, etc.), images are sent as base64 data URLs.
        Text/code attachments are already appended to the message by the frontend.

        Args:
            text_message: The text message content
            attachments: Optional list of attachments (can be Pydantic models or dicts)

        Returns:
            Either a plain string (no images) or a list of content blocks (with images)
        """
        if not attachments:
            return text_message

        # Helper to get attribute from object or dict
        def get_attr(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        # Check if there are any image attachments
        image_attachments = [
            att for att in attachments
            if get_attr(att, 'type') == 'image' and get_attr(att, 'content')
        ]

        if not image_attachments:
            # No images, just return text (text content already appended by frontend)
            return text_message

        # Build multimodal content with text and images
        content = [{"type": "text", "text": text_message}]

        for attachment in image_attachments:
            # The content should be a base64 data URL like "data:image/png;base64,..."
            image_url = get_attr(attachment, 'content')
            if not image_url.startswith("data:"):
                # Add data URL prefix if missing
                mime_type = get_attr(attachment, 'mimeType', 'image/png')
                image_url = f"data:{mime_type};base64,{image_url}"

            content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })
            logger.info(f"Added image attachment: {get_attr(attachment, 'name', 'unknown')}")

        return content

    def _execute_agent(
        self,
        execution_strategy: ExecutionStrategy,
        llm,
        tools: List[BaseTool],
        input_message: str,
        config: Dict[str, Any],
        recorder: SessionRecorder,
        timeout_seconds: int,
        chat_history: List = None,
        attachments: Optional[List[Any]] = None,
        tracing_callback=None
    ) -> ExecutionResult:
        """Execute the appropriate agent type based on execution strategy"""
        if chat_history is None:
            chat_history = []

        if execution_strategy == ExecutionStrategy.react:
            return self._execute_react_agent(
                llm, tools, input_message, config, recorder, timeout_seconds, chat_history, attachments, tracing_callback
            )
        elif execution_strategy == ExecutionStrategy.plan_and_execute:
            return self._execute_plan_and_execute_agent(
                llm, tools, input_message, config, recorder, timeout_seconds, chat_history, tracing_callback
            )
        elif execution_strategy == ExecutionStrategy.conversational:
            return self._execute_conversational_agent(
                llm, tools, input_message, config, recorder, timeout_seconds, chat_history, attachments, tracing_callback
            )
        else:
            raise AgentConfigurationError(
                f"Unsupported execution strategy: {execution_strategy}"
            )

    def _execute_react_agent(
        self,
        llm,
        tools: List[BaseTool],
        input_message: str,
        config: Dict[str, Any],
        recorder: SessionRecorder,
        timeout_seconds: int,
        chat_history: List = None,
        attachments: Optional[List[Any]] = None,
        tracing_callback=None
    ) -> ExecutionResult:
        """Execute ReAct agent (uses tool-calling for supported models)"""
        if chat_history is None:
            chat_history = []

        # Get model name from config
        model_name = config.get("llm_config", {}).get("model", "")
        system_prompt, prompt_version_id = self._resolve_system_prompt(config)

        # Check if model supports native tool calling
        use_tool_calling = supports_tool_calling(model_name)

        # Helper to check for image attachments
        def has_image_attachments():
            if not attachments:
                return False
            for att in attachments:
                att_type = att.get('type') if isinstance(att, dict) else getattr(att, 'type', None)
                if att_type == 'image':
                    return True
            return False

        has_images = has_image_attachments()

        if use_tool_calling and tools:
            logger.info(f"Using tool-calling agent for model {model_name}")
            return self._execute_tool_calling_agent(
                llm, tools, input_message, system_prompt, config, recorder, timeout_seconds, chat_history, attachments, tracing_callback
            )
        elif has_images and use_tool_calling:
            # Image attachments with vision-capable model but no tools
            # Use conversational path for proper multimodal support
            # (tool-calling agent prompt templates don't handle multimodal content)
            logger.info(f"Using conversational mode for model {model_name} (image attachments, no tools)")
            return self._execute_conversational_agent(
                llm, input_message, system_prompt, config, recorder, timeout_seconds, chat_history, attachments, tracing_callback
            )
        else:
            logger.info(f"Using text-based ReAct agent for model {model_name}")
            return self._execute_text_react_agent(
                llm, tools, input_message, config, recorder, timeout_seconds, chat_history, tracing_callback
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
        chat_history: List = None,
        attachments: Optional[List[Any]] = None,
        tracing_callback=None
    ) -> ExecutionResult:
        """Execute agent using native tool calling (function calling) API"""
        if chat_history is None:
            chat_history = []

        # Create multimodal content if there are image attachments
        message_content = self._create_multimodal_content(input_message, attachments)

        # Create chat prompt for tool-calling agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Create tool-calling agent
        agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)

        # Create executor with tracing callback
        callbacks = [tracing_callback] if tracing_callback else None
        executor = LangChainAgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=config.get("max_iterations", 10),
            max_execution_time=timeout_seconds,
            return_intermediate_steps=True,
            callbacks=callbacks
        )

        # Execute with chat history - use multimodal content for input
        result = executor.invoke({"input": message_content, "chat_history": chat_history})

        # Extract steps and content blocks
        steps = []
        content_blocks = []
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

            # Extract content_block from tool result if present
            try:
                import json
                obs_data = json.loads(observation) if isinstance(observation, str) else observation
                if isinstance(obs_data, dict) and "content_block" in obs_data:
                    content_blocks.append(obs_data["content_block"])
            except (json.JSONDecodeError, TypeError):
                pass  # Not JSON or doesn't contain content_block

        output = result.get("output", "")

        # Estimate token usage (rough approximation)
        tokens_input = len(input_message.split()) * 2
        tokens_output = len(output.split()) * 2

        return ExecutionResult(
            success=True,
            output=output,
            content_blocks=content_blocks if content_blocks else None,
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
        chat_history: List = None,
        tracing_callback=None
    ) -> ExecutionResult:
        """Execute text-based ReAct agent (for models without tool calling)"""
        if chat_history is None:
            chat_history = []

        # Get or create prompt
        system_prompt, _ = self._resolve_system_prompt(config, default="")
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

        # Create executor with tracing callback
        callbacks = [tracing_callback] if tracing_callback else None
        executor = LangChainAgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=config.get("max_iterations", 10),
            max_execution_time=timeout_seconds,
            callbacks=callbacks,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )

        # Execute
        result = executor.invoke({"input": input_message})

        # Extract steps and content blocks
        steps = []
        content_blocks = []
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

            # Extract content_block from tool result if present
            try:
                import json
                obs_data = json.loads(observation) if isinstance(observation, str) else observation
                if isinstance(obs_data, dict) and "content_block" in obs_data:
                    content_blocks.append(obs_data["content_block"])
            except (json.JSONDecodeError, TypeError):
                pass  # Not JSON or doesn't contain content_block

        output = result.get("output", "")

        # Estimate token usage (rough approximation)
        tokens_input = len(input_message.split()) * 2  # Rough estimate
        tokens_output = len(output.split()) * 2

        return ExecutionResult(
            success=True,
            output=output,
            content_blocks=content_blocks if content_blocks else None,
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
        chat_history: List = None,
        tracing_callback=None  # Note: plan-and-execute doesn't fully support callbacks yet
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
        chat_history: List = None,
        attachments: Optional[List[Any]] = None,
        tracing_callback=None
    ) -> ExecutionResult:
        """Execute Conversational agent (simple chat without tools)"""
        if chat_history is None:
            chat_history = []

        system_prompt, _ = self._resolve_system_prompt(config)

        # Build messages list with system prompt, chat history, and current message
        messages = [SystemMessage(content=system_prompt)]

        # Add chat history
        for msg in chat_history:
            messages.append(msg)

        # Create multimodal content if there are image attachments
        message_content = self._create_multimodal_content(input_message, attachments)

        # Add current user message (with multimodal content if images present)
        messages.append(HumanMessage(content=message_content))

        # Simple LLM invocation with tracing callback
        invoke_config = {}
        if tracing_callback:
            invoke_config["callbacks"] = [tracing_callback]
        response = llm.invoke(messages, config=invoke_config)

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
