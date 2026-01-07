"""
Streaming Agent Executor Service.

Provides WebSocket-based real-time streaming of agent execution events.
Extends the base AgentExecutorService to add streaming capability while
maintaining backward compatibility with the REST API.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import asyncio
import logging
import time

from sqlalchemy.orm import Session as DBSession
from fastapi import WebSocket

# LangChain imports
from langchain.agents import AgentExecutor as LangChainAgentExecutor
from langchain.agents import create_react_agent, create_tool_calling_agent
from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.tools import BaseTool

# Local imports
from ..models.agent import Agent, AgentVersion
from ..models.agent_type import ExecutionStrategy
from ..models.session import Session, SessionStatus, TraceStepType
from .agent_executor import (
    AgentExecutorService,
    ExecutionResult,
    AgentNotFoundError,
    AgentConfigurationError,
    AgentExecutionTimeoutError,
    REACT_PROMPT_TEMPLATE,
    supports_tool_calling,
)
from .session_recorder import SessionRecorder, create_session_recorder
from .streaming_callback import StreamingWebSocketCallbackHandler
from .memory import ConversationMemoryService
from .mcp_client import MCPConnectionPool
from .mcp_tool_wrapper import create_mcp_tools_for_agent, MCPToolWrapper
from .workspace_tools import create_workspace_tools, WORKSPACE_TOOL_NAMES
from .web_tools import create_web_tools, WEB_TOOL_CLASSES
from .tool_wrapper import is_workspace_tool_class, WORKSPACE_TOOL_CLASSES, is_web_tool_class
from .image_generation_tools import create_image_generation_tools, IMAGE_GENERATION_TOOL_CLASSES

logger = logging.getLogger(__name__)


class StreamingAgentExecutorService(AgentExecutorService):
    """
    Agent executor service with WebSocket streaming support.

    Inherits from AgentExecutorService and adds the ability to stream
    execution events (tool calls, results, errors) via WebSocket in real-time.

    Usage:
        service = StreamingAgentExecutorService(db=db, user_id=user.id)
        result = await service.invoke_streaming(
            agent_id=1,
            input_message="What is 2+2?",
            websocket=websocket,
            session_id=None
        )
    """

    async def invoke_streaming(
        self,
        agent_id: int,
        input_message: str,
        websocket: WebSocket,
        session_id: Optional[int] = None,
        config_override: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        attachments: Optional[List[Any]] = None
    ) -> ExecutionResult:
        """
        Invoke agent with real-time streaming via WebSocket.

        Streams events as they occur during execution:
        - session_start: When session begins
        - tool_call: When agent decides to use a tool
        - tool_result: When tool completes
        - error: When an error occurs
        - final_answer: When agent produces final output
        - session_end: When session completes

        Args:
            agent_id: ID of the agent to invoke
            input_message: User's input message
            websocket: FastAPI WebSocket connection for streaming
            session_id: Optional existing session ID to continue
            config_override: Optional configuration overrides
            timeout_seconds: Optional execution timeout

        Returns:
            ExecutionResult with output and execution details
        """
        start_time = time.time()
        loop = asyncio.get_event_loop()

        # Load agent (using parent's methods)
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

        # Initialize MCP pool for cleanup in finally
        mcp_pool = None

        try:
            # Start session
            session = recorder.start_session(
                title=f"Streaming execution of {agent.name}",
                metadata={"input_preview": input_message[:100], "streaming": True}
            )

            # Send session_start event
            await self._send_event(websocket, "session_start", session.id, {
                "agent_id": agent_id,
                "agent_name": agent.name
            })

            # Record user message
            recorder.record_user_message(input_message)

            # Create streaming callback handler
            streaming_callback = StreamingWebSocketCallbackHandler(
                websocket=websocket,
                session_id=session.id,
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
                # Check if any tool_ids are workspace tools
                from ..models import Tool
                workspace_tool_requested = self.db.query(Tool).filter(
                    Tool.id.in_(tool_ids),
                    Tool.langchain_class.in_(list(WORKSPACE_TOOL_CLASSES.keys()) if hasattr(self, '_workspace_tool_classes_imported') else [
                        "WorkspaceFileRead", "WorkspaceFileWrite", "WorkspaceFileEdit",
                        "WorkspaceFileList", "WorkspaceFileSearch",
                        "WorkspaceTaskManager", "WorkspaceScratchpad"
                    ])
                ).first()

                if workspace_tool_requested:
                    # Create workspace tools with session context
                    workspace_tools = create_workspace_tools(self.db, session.id)
                    recorder.record_trace_step(
                        TraceStepType.THOUGHT,
                        content=f"Created {len(workspace_tools)} workspace tools for session {session.id}"
                    )

            # Load web tools if any web tool IDs are in config
            web_tools = []
            if tool_ids:
                # Check if any tool_ids are web tools
                from ..models import Tool
                web_tool_requested = self.db.query(Tool).filter(
                    Tool.id.in_(tool_ids),
                    Tool.langchain_class.in_(list(WEB_TOOL_CLASSES.keys()))
                ).first()

                if web_tool_requested:
                    # Create web tools
                    web_tools = create_web_tools()
                    recorder.record_trace_step(
                        TraceStepType.THOUGHT,
                        content=f"Created {len(web_tools)} web tools for research"
                    )

            # Load image generation tools if any image tool IDs are in config
            image_tools = []
            if tool_ids:
                # Check if any tool_ids are image generation tools
                from ..models import Tool
                image_tool_requested = self.db.query(Tool).filter(
                    Tool.id.in_(tool_ids),
                    Tool.langchain_class.in_(list(IMAGE_GENERATION_TOOL_CLASSES.keys()))
                ).first()

                if image_tool_requested:
                    # Create image generation tools with session and user context
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

            # Load chat history if continuing session
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

            # Execute with streaming callbacks
            result = await self._execute_agent_streaming(
                execution_strategy=agent.agent_type_config.execution_strategy,
                llm=llm,
                tools=all_tools,
                input_message=input_message,
                config=config,
                recorder=recorder,
                timeout_seconds=effective_timeout,
                chat_history=chat_history,
                streaming_callback=streaming_callback,
                attachments=attachments
            )

            # Calculate metrics
            total_latency = int((time.time() - start_time) * 1000)

            # Send final_answer event with content_blocks for multimodal output
            await self._send_event(websocket, "final_answer", session.id, {
                "output": result.output,
                "content_blocks": result.content_blocks or [],
                "token_usage": {
                    "input_tokens": result.tokens_input,
                    "output_tokens": result.tokens_output,
                    "total_tokens": result.tokens_input + result.tokens_output
                },
                "latency_ms": total_latency
            })

            # Record and finish session
            recorder.record_assistant_message(
                result.output or "",
                content_blocks=result.content_blocks
            )
            recorder.finish_session(
                status=SessionStatus.COMPLETED,
                output=result.output,
                tokens_input=result.tokens_input,
                tokens_output=result.tokens_output
            )

            # Send session_end event
            await self._send_event(websocket, "session_end", session.id, {
                "success": True,
                "total_steps": streaming_callback.step_number
            })

            return ExecutionResult(
                success=True,
                output=result.output,
                content_blocks=result.content_blocks,
                session_id=session.id,
                tokens_input=result.tokens_input,
                tokens_output=result.tokens_output,
                total_latency_ms=total_latency,
                steps=result.steps
            )

        except AgentExecutionTimeoutError as e:
            total_latency = int((time.time() - start_time) * 1000)

            # Send error event
            await self._send_event(websocket, "error", recorder.session_id, {
                "error": str(e),
                "error_type": "timeout"
            })

            recorder.fail_session(str(e), error_type="timeout")

            # Send session_end
            await self._send_event(websocket, "session_end", recorder.session_id, {
                "success": False,
                "total_steps": 0
            })

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
            logger.exception(f"Streaming agent execution failed: {str(e)}")

            # Send error event
            try:
                await self._send_event(websocket, "error", recorder.session_id or 0, {
                    "error": str(e),
                    "error_type": error_type
                })
            except Exception:
                pass

            try:
                recorder.fail_session(str(e), error_type=error_type)
            except Exception:
                pass

            # Send session_end
            try:
                await self._send_event(websocket, "session_end", recorder.session_id or 0, {
                    "success": False,
                    "total_steps": 0
                })
            except Exception:
                pass

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
                except Exception as cleanup_error:
                    logger.warning(f"Error closing MCP connections: {cleanup_error}")

    async def _send_event(
        self,
        websocket: WebSocket,
        event_type: str,
        session_id: int,
        payload: Dict[str, Any]
    ) -> None:
        """
        Send a WebSocket event.

        Args:
            websocket: WebSocket connection
            event_type: Type of event
            session_id: Session ID
            payload: Event data
        """
        event = {
            "type": event_type,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload
        }
        try:
            await websocket.send_json(event)
        except Exception as e:
            logger.error(f"Failed to send WebSocket event: {e}")

    async def _execute_agent_streaming(
        self,
        execution_strategy: ExecutionStrategy,
        llm,
        tools: List[BaseTool],
        input_message: str,
        config: Dict[str, Any],
        recorder: SessionRecorder,
        timeout_seconds: int,
        chat_history: List,
        streaming_callback: StreamingWebSocketCallbackHandler,
        attachments: Optional[List[Any]] = None
    ) -> ExecutionResult:
        """
        Execute agent with streaming callbacks.

        Runs the synchronous LangChain agent in a thread pool to avoid
        blocking the async event loop, while still capturing events
        via the streaming callback handler.
        """
        loop = asyncio.get_event_loop()

        def run_agent():
            """Synchronous agent execution function for thread pool."""
            model_name = config.get("llm_config", {}).get("model", "")
            system_prompt = config.get("system_prompt", "You are a helpful assistant.")

            # Helper to check for image attachments
            def has_image_attachments():
                if not attachments:
                    return False
                for att in attachments:
                    att_type = att.get('type') if isinstance(att, dict) else getattr(att, 'type', None)
                    if att_type == 'image':
                        return True
                return False

            # Determine agent type based on model capabilities
            use_tool_calling = supports_tool_calling(model_name) and tools
            has_images = has_image_attachments()

            # Debug logging for image attachment handling
            logger.info(f"Agent execution routing: strategy={execution_strategy}, model={model_name}")
            logger.info(f"  has_images={has_images}, use_tool_calling={use_tool_calling}, supports_tc={supports_tool_calling(model_name)}")
            logger.info(f"  tools_count={len(tools) if tools else 0}, attachments_count={len(attachments) if attachments else 0}")

            if execution_strategy == ExecutionStrategy.conversational:
                # Conversational agent - no tools
                return self._run_conversational(
                    llm, input_message, system_prompt, chat_history, attachments
                )

            elif use_tool_calling:
                # Tool-calling agent for modern models
                return self._run_tool_calling_agent(
                    llm, tools, input_message, system_prompt,
                    config, chat_history, streaming_callback, attachments
                )

            elif has_images and supports_tool_calling(model_name):
                # Image attachments with vision-capable model but no tools
                # Use conversational path for proper multimodal support
                # (tool-calling agent prompt templates don't handle multimodal content)
                logger.info(f"Using conversational mode for image attachments (no tools)")
                return self._run_conversational(
                    llm, input_message, system_prompt, chat_history, attachments
                )

            else:
                # Text-based ReAct agent for older models (no multimodal support)
                return self._run_text_react_agent(
                    llm, tools, input_message, config,
                    chat_history, streaming_callback
                )

        # Run in thread pool to avoid blocking
        result = await loop.run_in_executor(None, run_agent)

        # Record steps to database (callback already sent events)
        for step in result.get("steps", []):
            if step.get("step_type") == "tool_call":
                recorder.record_tool_call(
                    tool_name=step["tool_name"],
                    tool_input=step.get("tool_input", {})
                )
                recorder.record_tool_result(
                    tool_name=step["tool_name"],
                    tool_output=str(step.get("tool_output", ""))
                )

        return ExecutionResult(
            success=True,
            output=result.get("output", ""),
            content_blocks=result.get("content_blocks", []),
            tokens_input=result.get("tokens_input", 0),
            tokens_output=result.get("tokens_output", 0),
            steps=result.get("steps", [])
        )

    def _run_tool_calling_agent(
        self,
        llm,
        tools: List[BaseTool],
        input_message: str,
        system_prompt: str,
        config: Dict[str, Any],
        chat_history: List,
        streaming_callback: StreamingWebSocketCallbackHandler,
        attachments: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Run tool-calling agent (synchronous, for thread pool).
        """
        # Create multimodal content if there are image attachments
        message_content = self._create_multimodal_content(input_message, attachments)

        # Check if we have multimodal content (list of content parts)
        has_multimodal = isinstance(message_content, list)

        if has_multimodal:
            # For multimodal messages, add the human message directly to chat history
            # because prompt template interpolation stringifies list content
            full_chat_history = list(chat_history) + [HumanMessage(content=message_content)]

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])

            agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)

            executor = LangChainAgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                max_iterations=config.get("max_iterations", 10),
                return_intermediate_steps=True,
                callbacks=[streaming_callback]
            )

            # Execute with chat history containing the multimodal message
            result = executor.invoke({
                "chat_history": full_chat_history
            })
        else:
            # Original path for text-only messages
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])

            agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)

            executor = LangChainAgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                max_iterations=config.get("max_iterations", 10),
                return_intermediate_steps=True,
                callbacks=[streaming_callback]
            )

            result = executor.invoke({
                "input": message_content,
                "chat_history": chat_history
            })

        # Extract steps and content blocks for database recording
        steps = []
        content_blocks = []
        for action, observation in result.get("intermediate_steps", []):
            tool_input = action.tool_input
            if not isinstance(tool_input, dict):
                tool_input = {"input": str(tool_input)}

            steps.append({
                "step_type": "tool_call",
                "tool_name": action.tool,
                "tool_input": tool_input,
                "tool_output": str(observation)
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

        return {
            "output": output,
            "content_blocks": content_blocks if content_blocks else [],
            "steps": steps,
            "tokens_input": len(input_message.split()) * 2,
            "tokens_output": len(output.split()) * 2
        }

    def _run_text_react_agent(
        self,
        llm,
        tools: List[BaseTool],
        input_message: str,
        config: Dict[str, Any],
        chat_history: List,
        streaming_callback: StreamingWebSocketCallbackHandler
    ) -> Dict[str, Any]:
        """
        Run text-based ReAct agent (synchronous, for thread pool).
        """
        system_prompt = config.get("system_prompt", "")
        prompt_template = config.get("prompt_template", REACT_PROMPT_TEMPLATE)

        if system_prompt:
            prompt_template = f"{system_prompt}\n\n{prompt_template}"

        # Prepend chat history
        if chat_history:
            history_text = "\n".join([
                f"{'Human' if hasattr(msg, 'type') and msg.type == 'human' else 'Assistant'}: {msg.content}"
                for msg in chat_history
            ])
            input_message = f"Previous conversation:\n{history_text}\n\nCurrent question: {input_message}"

        prompt = PromptTemplate.from_template(prompt_template)

        # Create ReAct agent
        agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

        # Create executor with streaming callback
        executor = LangChainAgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=config.get("max_iterations", 10),
            handle_parsing_errors=True,
            return_intermediate_steps=True,
            callbacks=[streaming_callback]
        )

        # Execute
        result = executor.invoke({"input": input_message})

        # Extract steps and content blocks
        steps = []
        content_blocks = []
        for action, observation in result.get("intermediate_steps", []):
            tool_input = action.tool_input
            if not isinstance(tool_input, dict):
                tool_input = {"input": str(tool_input)}

            steps.append({
                "step_type": "tool_call",
                "tool_name": action.tool,
                "tool_input": tool_input,
                "tool_output": str(observation)
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

        return {
            "output": output,
            "content_blocks": content_blocks if content_blocks else [],
            "steps": steps,
            "tokens_input": len(input_message.split()) * 2,
            "tokens_output": len(output.split()) * 2
        }

    def _run_conversational(
        self,
        llm,
        input_message: str,
        system_prompt: str,
        chat_history: List,
        attachments: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Run conversational agent without tools (synchronous, for thread pool).
        """
        messages = [SystemMessage(content=system_prompt)]
        for msg in chat_history:
            messages.append(msg)

        # Create multimodal content if there are image attachments
        message_content = self._create_multimodal_content(input_message, attachments)
        messages.append(HumanMessage(content=message_content))

        response = llm.invoke(messages)
        output = response.content if hasattr(response, 'content') else str(response)

        tokens_input = 0
        tokens_output = 0
        if hasattr(response, 'usage_metadata'):
            usage = response.usage_metadata
            tokens_input = getattr(usage, 'input_tokens', 0)
            tokens_output = getattr(usage, 'output_tokens', 0)

        return {
            "output": output,
            "steps": [],
            "tokens_input": tokens_input,
            "tokens_output": tokens_output
        }
