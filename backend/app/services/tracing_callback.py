"""
LangChain Callback Handler for Hierarchical Tracing.

Automatically captures all LangChain operations as hierarchical spans
using the SpanRecorder service. This enables LangSmith/Langfuse-style
observability for agent executions.

Implements Phases 2-3 of ENHANCED_TRACING_SPEC.md.

Phase 2: Span recording to database
Phase 3: Real-time WebSocket streaming of span events
"""
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
import asyncio
import logging
import traceback

from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult, ChatGeneration, Generation
from langchain.schema import AgentAction, AgentFinish
from langchain_core.agents import AgentActionMessageLog

from sqlalchemy.orm import Session as DBSession


def _serialize_for_json(obj: Any) -> Any:
    """
    Recursively serialize an object for JSON storage.

    Handles LangChain objects like ToolAgentAction, AgentAction, AgentFinish,
    and other non-JSON-serializable types.

    Args:
        obj: Object to serialize

    Returns:
        JSON-serializable version of the object
    """
    # Handle None
    if obj is None:
        return None

    # Handle basic types
    if isinstance(obj, (str, int, float, bool)):
        return obj

    # Handle UUID
    if isinstance(obj, UUID):
        return str(obj)

    # Handle datetime
    if isinstance(obj, datetime):
        return obj.isoformat()

    # Handle Decimal
    if isinstance(obj, Decimal):
        return float(obj)

    # Handle LangChain AgentAction and subclasses (including ToolAgentAction)
    if isinstance(obj, AgentAction):
        result = {
            "type": type(obj).__name__,
            "tool": obj.tool,
            "tool_input": _serialize_for_json(obj.tool_input),
            "log": obj.log
        }
        # Handle AgentActionMessageLog which has additional message_log field
        if hasattr(obj, "message_log"):
            result["message_log"] = _serialize_for_json(obj.message_log)
        return result

    # Handle AgentFinish
    if isinstance(obj, AgentFinish):
        return {
            "type": "AgentFinish",
            "return_values": _serialize_for_json(obj.return_values),
            "log": obj.log
        }

    # Handle LangChain messages
    if hasattr(obj, "content") and hasattr(obj, "type"):
        result = {
            "type": getattr(obj, "type", type(obj).__name__),
            "content": _serialize_for_json(getattr(obj, "content", None))
        }
        if hasattr(obj, "additional_kwargs"):
            result["additional_kwargs"] = _serialize_for_json(obj.additional_kwargs)
        if hasattr(obj, "tool_calls"):
            result["tool_calls"] = _serialize_for_json(obj.tool_calls)
        return result

    # Handle lists
    if isinstance(obj, list):
        return [_serialize_for_json(item) for item in obj]

    # Handle dicts
    if isinstance(obj, dict):
        return {str(k): _serialize_for_json(v) for k, v in obj.items()}

    # Handle objects with __dict__
    if hasattr(obj, "__dict__"):
        return {
            "type": type(obj).__name__,
            "data": _serialize_for_json(obj.__dict__)
        }

    # Fallback: convert to string
    try:
        return str(obj)
    except Exception:
        return f"<non-serializable: {type(obj).__name__}>"

from ..models.session import SpanType, SpanStatus
from .span_recorder import SpanRecorder

from ..utils.model_pricing import calculate_cost, get_provider_from_model

logger = logging.getLogger(__name__)


class DeepAgentTracingCallback(BaseCallbackHandler):
    """
    LangChain callback handler that records all operations as hierarchical spans.

    Automatically captures:
    - LLM calls with tokens, model info, and cost
    - Tool invocations with inputs/outputs
    - Chain executions
    - Agent reasoning steps
    - Retriever queries
    - Errors with stack traces

    Also streams span events via WebSocket for real-time UI updates:
    - span_start: When a span begins
    - span_end: When a span completes (success or error)

    Usage:
        recorder = SpanRecorder(db, session_id)
        callback = DeepAgentTracingCallback(
            recorder,
            websocket=websocket,  # Optional for real-time streaming
            loop=asyncio.get_event_loop()
        )
        executor = AgentExecutor(..., callbacks=[callback])

    The callback maintains a span stack to properly nest child spans
    under their parents, creating a hierarchical trace tree.
    """

    def __init__(
        self,
        recorder: SpanRecorder,
        capture_inputs: bool = True,
        capture_outputs: bool = True,
        include_raw_prompts: bool = False,
        websocket=None,
        loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        """
        Initialize tracing callback handler.

        Args:
            recorder: SpanRecorder instance for creating spans
            capture_inputs: Whether to capture operation inputs
            capture_outputs: Whether to capture operation outputs
            include_raw_prompts: Whether to include raw prompt text (can be large)
            websocket: Optional WebSocket for real-time span streaming
            loop: Event loop for async WebSocket operations
        """
        super().__init__()
        self.recorder = recorder
        self.capture_inputs = capture_inputs
        self.capture_outputs = capture_outputs
        self.include_raw_prompts = include_raw_prompts
        self.websocket = websocket
        self.loop = loop

        # Map run_id -> span for tracking nested operations
        self._run_spans: Dict[str, Any] = {}

        # Track model info for cost calculation
        self._run_model_info: Dict[str, Dict[str, Any]] = {}

        # Track span context for WebSocket events
        self._span_contexts: Dict[str, Any] = {}

    # ========== WebSocket Event Methods ==========

    async def _send_ws_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Send an event through the WebSocket."""
        if not self.websocket:
            return

        event = {
            "type": event_type,
            "session_id": self.recorder.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload
        }
        try:
            await self.websocket.send_json(event)
            logger.debug(f"Sent span WebSocket event: {event_type}")
        except Exception as e:
            logger.error(f"Failed to send span WebSocket event: {e}")

    def _send_ws_event_sync(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Synchronous wrapper to send events from sync callbacks."""
        if not self.websocket or not self.loop:
            return

        try:
            future = asyncio.run_coroutine_threadsafe(
                self._send_ws_event(event_type, payload),
                self.loop
            )
            # Wait briefly for send to complete
            future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Failed to send sync span event: {e}")

    def _emit_span_start(
        self,
        span_id: int,
        span_type: SpanType,
        name: str,
        parent_span_id: Optional[int] = None,
        depth: int = 0,
        input_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Emit span_start WebSocket event."""
        self._send_ws_event_sync("span_start", {
            "span_id": span_id,
            "trace_id": str(self.recorder.trace_id),
            "parent_span_id": parent_span_id,
            "span_type": span_type.value,
            "name": name,
            "depth": depth,
            "input": input_data,
            "metadata": metadata
        })

    def _emit_span_end(
        self,
        span_id: int,
        status: SpanStatus,
        duration_ms: Optional[int] = None,
        output: Optional[Dict[str, Any]] = None,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None,
        cost_usd: Optional[float] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Emit span_end WebSocket event."""
        self._send_ws_event_sync("span_end", {
            "span_id": span_id,
            "status": status.value,
            "duration_ms": duration_ms,
            "output": output,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "cost_usd": cost_usd,
            "error_message": error_message
        })

    def _get_run_id_str(self, run_id: Optional[UUID]) -> str:
        """Convert run_id to string for dict key."""
        return str(run_id) if run_id else "unknown"

    # ========== Chain Callbacks ==========

    def _get_parent_span_id_and_depth(self, parent_run_id: Optional[UUID]) -> tuple:
        """
        Get parent span ID and depth from parent_run_id.

        Uses LangChain's parent_run_id to establish proper parent-child relationships
        instead of relying on a span stack which can get out of sync.
        """
        if parent_run_id:
            parent_key = self._get_run_id_str(parent_run_id)
            parent_span = self._run_spans.get(parent_key)
            if parent_span:
                return parent_span.id, parent_span.depth + 1
        return None, 0

    def _find_active_root_span(self) -> tuple:
        """
        Find the most likely parent span when parent_run_id is not available.

        This is a fallback for callbacks like on_agent_action that sometimes
        don't receive a parent_run_id from LangChain. Returns the first
        (lowest depth) active chain span as the parent.

        Returns:
            Tuple of (parent_span_id, depth) or (None, 0) if no active spans
        """
        if not self._run_spans:
            return None, 0

        # Find active chain spans sorted by depth (prefer lower depth as parent)
        chain_spans = [
            span for span in self._run_spans.values()
            if hasattr(span, 'span_type') and span.span_type in (SpanType.CHAIN, SpanType.AGENT)
        ]

        if not chain_spans:
            # Fall back to any active span
            chain_spans = list(self._run_spans.values())

        if chain_spans:
            # Sort by depth to get the root-most chain (lowest depth)
            chain_spans.sort(key=lambda s: s.depth if hasattr(s, 'depth') else 0)
            parent_span = chain_spans[0]
            return parent_span.id, parent_span.depth + 1

        return None, 0

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: Optional[UUID] = None,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Called when a chain starts running."""
        run_key = self._get_run_id_str(run_id)
        # Handle case where serialized is None
        if serialized:
            chain_name = serialized.get("name", serialized.get("id", ["Chain"])[-1])
        else:
            chain_name = "Chain"

        # Determine span type based on chain name
        span_type = SpanType.CHAIN
        if "agent" in chain_name.lower():
            span_type = SpanType.AGENT

        input_data = _serialize_for_json(inputs) if self.capture_inputs else None

        # Get parent span from parent_run_id (LangChain's built-in parent tracking)
        parent_span_id, depth = self._get_parent_span_id_and_depth(parent_run_id)

        # Create span using start_span (not context manager)
        span = self.recorder.start_span(
            span_type=span_type,
            name=chain_name,
            parent_span_id=parent_span_id,
            depth=depth,
            input_data=input_data,
            tags=tags,
            metadata=metadata
        )
        self._run_spans[run_key] = span

        # Emit WebSocket event
        self._emit_span_start(
            span_id=span.id,
            span_type=span_type,
            name=chain_name,
            parent_span_id=parent_span_id,
            depth=depth,
            input_data=input_data,
            metadata=metadata
        )

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: Optional[UUID] = None,
        parent_run_id: Optional[UUID] = None,
        **kwargs
    ) -> None:
        """Called when a chain finishes."""
        run_key = self._get_run_id_str(run_id)
        span = self._run_spans.pop(run_key, None)

        if span:
            output_data = _serialize_for_json(outputs) if self.capture_outputs else None
            self.recorder.end_span(span, status=SpanStatus.SUCCESS, output=output_data)

            # Emit WebSocket event
            self._emit_span_end(
                span_id=span.id,
                status=SpanStatus.SUCCESS,
                duration_ms=span.duration_ms,
                output=output_data
            )

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: Optional[UUID] = None,
        parent_run_id: Optional[UUID] = None,
        **kwargs
    ) -> None:
        """Called when a chain errors."""
        run_key = self._get_run_id_str(run_id)
        span = self._run_spans.pop(run_key, None)

        if span:
            self.recorder.end_span(
                span,
                status=SpanStatus.ERROR,
                error_message=str(error),
                error_type=type(error).__name__
            )

            # Emit WebSocket event
            self._emit_span_end(
                span_id=span.id,
                status=SpanStatus.ERROR,
                duration_ms=span.duration_ms,
                error_message=str(error)
            )
        else:
            # Record standalone error
            self.recorder.record_error(error, include_stack=True)

    # ========== LLM Callbacks ==========

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: Optional[UUID] = None,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        invocation_params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Called when LLM starts processing."""
        run_key = self._get_run_id_str(run_id)

        # Extract model info
        model_name = "unknown"
        model_provider = "unknown"
        model_params = {}

        if invocation_params:
            model_name = invocation_params.get("model_name", invocation_params.get("model", "unknown"))
            model_params = {
                k: v for k, v in invocation_params.items()
                if k in ["temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty"]
            }

        if serialized:
            if "name" in serialized:
                model_name = serialized["name"]
            if "kwargs" in serialized:
                model_name = serialized["kwargs"].get("model_name", model_name)

        model_provider = get_provider_from_model(model_name)

        # Store model info for cost calculation in on_llm_end
        self._run_model_info[run_key] = {
            "model_name": model_name,
            "model_provider": model_provider,
            "model_params": model_params
        }

        # Prepare input data
        input_data = None
        if self.capture_inputs:
            if self.include_raw_prompts:
                input_data = {"prompts": prompts}
            else:
                input_data = {"prompt_count": len(prompts), "total_chars": sum(len(p) for p in prompts)}

        # Get parent span from parent_run_id (LangChain's built-in parent tracking)
        parent_span_id, depth = self._get_parent_span_id_and_depth(parent_run_id)

        # Create span using start_span
        span = self.recorder.start_span(
            span_type=SpanType.LLM,
            name=model_name,
            parent_span_id=parent_span_id,
            depth=depth,
            input_data=input_data,
            tags=tags,
            metadata=metadata,
            model_name=model_name,
            model_provider=model_provider,
            model_parameters=model_params
        )
        self._run_spans[run_key] = span

        # Emit WebSocket event
        self._emit_span_start(
            span_id=span.id,
            span_type=SpanType.LLM,
            name=model_name,
            parent_span_id=parent_span_id,
            depth=depth,
            input_data=input_data,
            metadata={"model_provider": model_provider, "model_params": model_params}
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: Optional[UUID] = None,
        parent_run_id: Optional[UUID] = None,
        **kwargs
    ) -> None:
        """Called when LLM finishes processing."""
        run_key = self._get_run_id_str(run_id)
        span = self._run_spans.pop(run_key, None)
        model_info = self._run_model_info.pop(run_key, {})

        if span:
            # Extract token usage from multiple possible locations
            tokens_input = 0
            tokens_output = 0

            # Method 1: Check llm_output (standard non-streaming location)
            if response.llm_output:
                token_usage = response.llm_output.get("token_usage", {})
                tokens_input = token_usage.get("prompt_tokens", 0)
                tokens_output = token_usage.get("completion_tokens", 0)

                # Try alternative field names
                if tokens_input == 0:
                    tokens_input = token_usage.get("input_tokens", 0)
                if tokens_output == 0:
                    tokens_output = token_usage.get("output_tokens", 0)

            # Method 2: Check generations for usage_metadata (streaming location)
            if (tokens_input == 0 and tokens_output == 0) and response.generations:
                for gen_list in response.generations:
                    for gen in gen_list:
                        # Check ChatGeneration's message for usage_metadata
                        if hasattr(gen, "message") and hasattr(gen.message, "usage_metadata"):
                            usage_meta = gen.message.usage_metadata
                            if usage_meta:
                                # usage_metadata can be a dict or an object
                                if isinstance(usage_meta, dict):
                                    tokens_input = usage_meta.get("input_tokens", 0) or 0
                                    tokens_output = usage_meta.get("output_tokens", 0) or 0
                                else:
                                    tokens_input = getattr(usage_meta, "input_tokens", 0) or 0
                                    tokens_output = getattr(usage_meta, "output_tokens", 0) or 0
                                break
                        # Also check response_metadata
                        if hasattr(gen, "message") and hasattr(gen.message, "response_metadata"):
                            resp_meta = gen.message.response_metadata or {}
                            if "token_usage" in resp_meta:
                                usage = resp_meta["token_usage"]
                                tokens_input = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
                                tokens_output = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)
                                break
                    if tokens_input > 0 or tokens_output > 0:
                        break

            logger.info(f"LLM token usage final: input={tokens_input}, output={tokens_output}")

            # Calculate cost
            model_name = model_info.get("model_name", "unknown")
            cost = calculate_cost(model_name, tokens_input, tokens_output)

            # Capture output
            output_data = None
            if self.capture_outputs and response.generations:
                output_texts = []
                for gen_list in response.generations:
                    for gen in gen_list:
                        if hasattr(gen, "text"):
                            output_texts.append(gen.text)
                        elif hasattr(gen, "message") and hasattr(gen.message, "content"):
                            output_texts.append(gen.message.content)
                output_data = {"content": output_texts[0] if len(output_texts) == 1 else output_texts}

            # End the span
            self.recorder.end_span(
                span,
                status=SpanStatus.SUCCESS,
                output=output_data,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_usd=cost
            )

            # Emit WebSocket event
            self._emit_span_end(
                span_id=span.id,
                status=SpanStatus.SUCCESS,
                duration_ms=span.duration_ms,
                output=output_data,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_usd=float(cost)
            )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: Optional[UUID] = None,
        parent_run_id: Optional[UUID] = None,
        **kwargs
    ) -> None:
        """Called when LLM encounters an error."""
        run_key = self._get_run_id_str(run_id)
        span = self._run_spans.pop(run_key, None)
        self._run_model_info.pop(run_key, None)

        if span:
            self.recorder.end_span(
                span,
                status=SpanStatus.ERROR,
                error_message=str(error),
                error_type=type(error).__name__
            )

            # Emit WebSocket event
            self._emit_span_end(
                span_id=span.id,
                status=SpanStatus.ERROR,
                duration_ms=span.duration_ms,
                error_message=str(error)
            )
        else:
            self.recorder.record_error(error, include_stack=True)

    # ========== Tool Callbacks ==========

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: Optional[UUID] = None,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Called when tool execution starts."""
        run_key = self._get_run_id_str(run_id)
        tool_name = serialized.get("name", "unknown_tool") if serialized else "unknown_tool"

        # Prepare input data
        input_data = None
        if self.capture_inputs:
            if inputs:
                input_data = _serialize_for_json(inputs)
            else:
                input_data = {"input": input_str}

        # Get parent span from parent_run_id (LangChain's built-in parent tracking)
        parent_span_id, depth = self._get_parent_span_id_and_depth(parent_run_id)

        # Create span using start_span
        span = self.recorder.start_span(
            span_type=SpanType.TOOL,
            name=tool_name,
            parent_span_id=parent_span_id,
            depth=depth,
            input_data=input_data,
            tags=tags,
            metadata=metadata,
            tool_name=tool_name
        )
        self._run_spans[run_key] = span

        # Emit WebSocket event
        self._emit_span_start(
            span_id=span.id,
            span_type=SpanType.TOOL,
            name=tool_name,
            parent_span_id=parent_span_id,
            depth=depth,
            input_data=input_data,
            metadata=metadata
        )

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: Optional[UUID] = None,
        parent_run_id: Optional[UUID] = None,
        **kwargs
    ) -> None:
        """Called when tool execution completes."""
        run_key = self._get_run_id_str(run_id)
        span = self._run_spans.pop(run_key, None)

        if span:
            # Try to parse JSON output, then serialize for storage
            output_data = None
            if self.capture_outputs:
                try:
                    import json
                    parsed = json.loads(output) if isinstance(output, str) else output
                    output_data = _serialize_for_json(parsed)
                except (json.JSONDecodeError, TypeError):
                    output_data = {"result": _serialize_for_json(output)}

            # End the span
            self.recorder.end_span(span, status=SpanStatus.SUCCESS, output=output_data)

            # Emit WebSocket event
            self._emit_span_end(
                span_id=span.id,
                status=SpanStatus.SUCCESS,
                duration_ms=span.duration_ms,
                output=output_data
            )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: Optional[UUID] = None,
        parent_run_id: Optional[UUID] = None,
        **kwargs
    ) -> None:
        """Called when tool execution fails."""
        run_key = self._get_run_id_str(run_id)
        span = self._run_spans.pop(run_key, None)

        if span:
            self.recorder.end_span(
                span,
                status=SpanStatus.ERROR,
                error_message=str(error),
                error_type=type(error).__name__
            )

            # Emit WebSocket event
            self._emit_span_end(
                span_id=span.id,
                status=SpanStatus.ERROR,
                duration_ms=span.duration_ms,
                error_message=str(error)
            )
        else:
            self.recorder.record_error(error, include_stack=True)

    # ========== Agent Callbacks ==========

    def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: Optional[UUID] = None,
        parent_run_id: Optional[UUID] = None,
        **kwargs
    ) -> None:
        """Called when agent decides to use a tool."""
        # Record agent's thought/reasoning as a thought span with proper parent tracking
        if action.log:
            thought_text = f"Planning to use tool: {action.tool}\n\nReasoning: {action.log}"

            # Get parent span from parent_run_id, with fallback to active root span
            parent_span_id, depth = self._get_parent_span_id_and_depth(parent_run_id)
            if parent_span_id is None:
                # Fallback: find the active root chain when parent_run_id not provided
                parent_span_id, depth = self._find_active_root_span()

            # Create and immediately close the thought span
            span = self.recorder.start_span(
                span_type=SpanType.THOUGHT,
                name="Agent Thought",
                parent_span_id=parent_span_id,
                depth=depth,
                input_data={"thought": thought_text}
            )
            self.recorder.end_span(span, status=SpanStatus.SUCCESS)

    def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: Optional[UUID] = None,
        parent_run_id: Optional[UUID] = None,
        **kwargs
    ) -> None:
        """Called when agent completes execution."""
        # Record final answer reasoning if available with proper parent tracking
        if finish.log:
            thought_text = f"Final answer reasoning:\n\n{finish.log}"

            # Get parent span from parent_run_id, with fallback to active root span
            parent_span_id, depth = self._get_parent_span_id_and_depth(parent_run_id)
            if parent_span_id is None:
                # Fallback: find the active root chain when parent_run_id not provided
                parent_span_id, depth = self._find_active_root_span()

            # Create and immediately close the thought span
            span = self.recorder.start_span(
                span_type=SpanType.THOUGHT,
                name="Agent Thought",
                parent_span_id=parent_span_id,
                depth=depth,
                input_data={"thought": thought_text}
            )
            self.recorder.end_span(span, status=SpanStatus.SUCCESS)

    # ========== Retriever Callbacks ==========

    def on_retriever_start(
        self,
        serialized: Dict[str, Any],
        query: str,
        *,
        run_id: Optional[UUID] = None,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Called when retriever starts."""
        run_key = self._get_run_id_str(run_id)
        retriever_name = serialized.get("name", "Retriever") if serialized else "Retriever"

        input_data = {"query": query} if self.capture_inputs else None

        # Get parent span from parent_run_id (LangChain's built-in parent tracking)
        parent_span_id, depth = self._get_parent_span_id_and_depth(parent_run_id)

        # Create span using start_span
        span = self.recorder.start_span(
            span_type=SpanType.RETRIEVER,
            name=retriever_name,
            parent_span_id=parent_span_id,
            depth=depth,
            input_data=input_data,
            tags=tags,
            metadata=metadata
        )
        self._run_spans[run_key] = span

        # Emit WebSocket event
        self._emit_span_start(
            span_id=span.id,
            span_type=SpanType.RETRIEVER,
            name=retriever_name,
            parent_span_id=parent_span_id,
            depth=depth,
            input_data=input_data,
            metadata=metadata
        )

    def on_retriever_end(
        self,
        documents: List[Any],
        *,
        run_id: Optional[UUID] = None,
        parent_run_id: Optional[UUID] = None,
        **kwargs
    ) -> None:
        """Called when retriever finishes."""
        run_key = self._get_run_id_str(run_id)
        span = self._run_spans.pop(run_key, None)

        if span:
            # Summarize documents (don't store full content)
            output_data = None
            if self.capture_outputs:
                doc_summaries = []
                for doc in documents:
                    summary = {
                        "content_length": len(doc.page_content) if hasattr(doc, "page_content") else 0,
                        "metadata": doc.metadata if hasattr(doc, "metadata") else {}
                    }
                    doc_summaries.append(summary)
                output_data = {"documents": doc_summaries, "count": len(documents)}

            # End the span
            self.recorder.end_span(span, status=SpanStatus.SUCCESS, output=output_data)

            # Emit WebSocket event
            self._emit_span_end(
                span_id=span.id,
                status=SpanStatus.SUCCESS,
                duration_ms=span.duration_ms,
                output=output_data
            )

    def on_retriever_error(
        self,
        error: BaseException,
        *,
        run_id: Optional[UUID] = None,
        parent_run_id: Optional[UUID] = None,
        **kwargs
    ) -> None:
        """Called when retriever errors."""
        run_key = self._get_run_id_str(run_id)
        span = self._run_spans.pop(run_key, None)

        if span:
            self.recorder.end_span(
                span,
                status=SpanStatus.ERROR,
                error_message=str(error),
                error_type=type(error).__name__
            )

            # Emit WebSocket event
            self._emit_span_end(
                span_id=span.id,
                status=SpanStatus.ERROR,
                duration_ms=span.duration_ms,
                error_message=str(error)
            )
        else:
            self.recorder.record_error(error, include_stack=True)


def create_tracing_callback(
    db: DBSession,
    session_id: int,
    capture_inputs: bool = True,
    capture_outputs: bool = True,
    include_raw_prompts: bool = False,
    websocket=None,
    loop: Optional[asyncio.AbstractEventLoop] = None
) -> DeepAgentTracingCallback:
    """
    Factory function to create a tracing callback.

    Args:
        db: Database session
        session_id: Session ID for span association
        capture_inputs: Whether to capture operation inputs
        capture_outputs: Whether to capture operation outputs
        include_raw_prompts: Whether to include raw prompt text
        websocket: Optional WebSocket for real-time span streaming (Phase 3)
        loop: Event loop for async WebSocket operations

    Returns:
        Configured DeepAgentTracingCallback instance
    """
    from .span_recorder import create_span_recorder

    recorder = create_span_recorder(db, session_id)
    return DeepAgentTracingCallback(
        recorder=recorder,
        capture_inputs=capture_inputs,
        capture_outputs=capture_outputs,
        include_raw_prompts=include_raw_prompts,
        websocket=websocket,
        loop=loop
    )
