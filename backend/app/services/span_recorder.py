"""
Span Recorder Service for Enhanced Tracing System.

This service provides a hierarchical span recording interface with:
- Context manager support for automatic span lifecycle
- Thread-safe nested span tracking
- Automatic timing (start/end timestamps, duration)
- Parent-child relationship management

Implements Phase 1 of ENHANCED_TRACING_SPEC.md.
"""
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
from contextlib import contextmanager
from decimal import Decimal
from uuid import UUID, uuid4
import threading
import time
import logging

from sqlalchemy.orm import Session as DBSession

from ..models.session import Span, SpanType, SpanStatus
from ..schemas.span import SpanCreate, SpanUpdate

logger = logging.getLogger(__name__)


class SpanRecorderError(Exception):
    """Exception raised when span recording fails"""
    pass


class SpanContext:
    """
    Context manager for a single span.

    Provides methods to update span data during execution
    and automatically handles timing and completion.
    """

    def __init__(
        self,
        recorder: "SpanRecorder",
        span: Span
    ):
        self._recorder = recorder
        self._span = span
        self._start_time = time.time()

    @property
    def span(self) -> Span:
        """Get the underlying span object"""
        return self._span

    @property
    def id(self) -> int:
        """Get span ID"""
        return self._span.id

    def set_input(self, input_data: Dict[str, Any]) -> None:
        """Set the span input data"""
        self._span.input = input_data
        self._recorder._db.commit()

    def set_output(self, output_data: Dict[str, Any]) -> None:
        """Set the span output data"""
        self._span.output = output_data
        self._recorder._db.commit()

    def set_tokens(
        self,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None
    ) -> None:
        """Set token usage for LLM spans"""
        if input_tokens is not None:
            self._span.tokens_input = input_tokens
        if output_tokens is not None:
            self._span.tokens_output = output_tokens
        if total_tokens is not None:
            self._span.tokens_total = total_tokens
        elif input_tokens is not None or output_tokens is not None:
            # Auto-calculate total if not provided
            self._span.tokens_total = (input_tokens or 0) + (output_tokens or 0)
        self._recorder._db.commit()

    def set_cost(self, cost_usd: Union[float, Decimal]) -> None:
        """Set cost for LLM spans"""
        self._span.cost_usd = Decimal(str(cost_usd))
        self._recorder._db.commit()

    def set_model(
        self,
        model_name: str,
        provider: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> None:
        """Set model information for LLM spans"""
        self._span.model_name = model_name
        if provider:
            self._span.model_provider = provider
        if parameters:
            self._span.model_parameters = parameters
        self._recorder._db.commit()

    def set_error(
        self,
        message: str,
        error_type: Optional[str] = None,
        stack_trace: Optional[str] = None
    ) -> None:
        """Set error information"""
        self._span.error_message = message
        self._span.error_type = error_type
        self._span.error_stack = stack_trace
        self._span.status = SpanStatus.ERROR
        self._recorder._db.commit()

    def add_tag(self, tag: str) -> None:
        """Add a tag to the span"""
        if self._span.tags is None:
            self._span.tags = []
        if tag not in self._span.tags:
            self._span.tags = self._span.tags + [tag]  # Create new list to trigger SQLAlchemy change detection
        self._recorder._db.commit()

    def set_tags(self, tags: List[str]) -> None:
        """Set all tags for the span"""
        self._span.tags = tags
        self._recorder._db.commit()

    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata key-value pair"""
        if self._span.meta is None:
            self._span.meta = {}
        meta = dict(self._span.meta)
        meta[key] = value
        self._span.meta = meta
        self._recorder._db.commit()

    def update_metadata(self, data: Dict[str, Any]) -> None:
        """Update metadata with multiple key-value pairs"""
        if self._span.meta is None:
            self._span.meta = {}
        meta = dict(self._span.meta)
        meta.update(data)
        self._span.meta = meta
        self._recorder._db.commit()

    def _complete(self, status: SpanStatus = SpanStatus.SUCCESS) -> None:
        """Complete the span with timing and status"""
        end_time = time.time()
        duration_ms = int((end_time - self._start_time) * 1000)

        self._span.ended_at = datetime.now(timezone.utc)
        self._span.duration_ms = duration_ms

        # Only update status if not already set to error
        if self._span.status != SpanStatus.ERROR:
            self._span.status = status

        self._recorder._db.commit()
        logger.debug(
            f"Completed span {self._span.id} ({self._span.span_type.value}: {self._span.name}) "
            f"status={self._span.status.value} duration={duration_ms}ms"
        )


class SpanRecorder:
    """
    Service for recording hierarchical spans.

    Provides a thread-safe interface for recording spans with
    automatic parent-child relationship management.

    Usage:
        recorder = SpanRecorder(db, session_id=123)

        async with recorder.span(SpanType.AGENT, "Power Agent") as agent_span:
            agent_span.set_input({"message": "Hello"})

            async with recorder.span(SpanType.LLM, "gpt-4o") as llm_span:
                llm_span.set_model("gpt-4o", provider="openai")
                result = await llm.invoke(...)
                llm_span.set_output({"content": result})
                llm_span.set_tokens(input=100, output=50)

            async with recorder.span(SpanType.TOOL, "Web Search") as tool_span:
                tool_span.set_input({"query": "AI news"})
                result = await tool.invoke(...)
                tool_span.set_output(result)

            agent_span.set_output({"response": "Here's what I found..."})
    """

    def __init__(
        self,
        db: DBSession,
        session_id: int,
        trace_id: Optional[UUID] = None
    ):
        """
        Initialize span recorder.

        Args:
            db: Database session
            session_id: Session ID this trace belongs to
            trace_id: Optional trace ID (UUID). Generated if not provided.
        """
        self._db = db
        self._session_id = session_id
        self._trace_id = trace_id or uuid4()

        # Thread-local storage for span stack (supports nested spans)
        self._local = threading.local()

        # Global span order counter for this trace
        self._span_order = 0
        self._order_lock = threading.Lock()

    @property
    def trace_id(self) -> UUID:
        """Get the trace ID for this recorder"""
        return self._trace_id

    @property
    def session_id(self) -> int:
        """Get the session ID"""
        return self._session_id

    @property
    def current_span(self) -> Optional[Span]:
        """Get the current span (top of stack)"""
        stack = getattr(self._local, 'span_stack', [])
        return stack[-1] if stack else None

    @property
    def root_span(self) -> Optional[Span]:
        """Get the root span (bottom of stack)"""
        stack = getattr(self._local, 'span_stack', [])
        return stack[0] if stack else None

    def _get_span_stack(self) -> List[Span]:
        """Get the span stack for current thread"""
        if not hasattr(self._local, 'span_stack'):
            self._local.span_stack = []
        return self._local.span_stack

    def _push_span(self, span: Span) -> None:
        """Push a span onto the stack"""
        stack = self._get_span_stack()
        stack.append(span)

    def _pop_span(self) -> Optional[Span]:
        """Pop a span from the stack"""
        stack = self._get_span_stack()
        return stack.pop() if stack else None

    def _next_order(self) -> int:
        """Get next span order (thread-safe)"""
        with self._order_lock:
            order = self._span_order
            self._span_order += 1
            return order

    @contextmanager
    def span(
        self,
        span_type: SpanType,
        name: str,
        input_data: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> SpanContext:
        """
        Create a new span as a context manager.

        Args:
            span_type: Type of span (agent, llm, tool, etc.)
            name: Human-readable span name
            input_data: Optional input data
            tags: Optional tags for filtering
            metadata: Optional custom metadata
            **kwargs: Additional span fields (tool_name, model_name, etc.)

        Yields:
            SpanContext for updating span during execution

        Example:
            with recorder.span(SpanType.LLM, "GPT-4 Call") as span:
                span.set_input({"messages": [...]})
                result = await llm.invoke(...)
                span.set_output({"content": result})
        """
        # Determine parent and depth
        parent_span = self.current_span
        parent_span_id = parent_span.id if parent_span else None
        depth = (parent_span.depth + 1) if parent_span else 0

        # Create span
        span = self.start_span(
            span_type=span_type,
            name=name,
            parent_span_id=parent_span_id,
            depth=depth,
            input_data=input_data,
            tags=tags,
            metadata=metadata,
            **kwargs
        )

        context = SpanContext(self, span)
        self._push_span(span)

        try:
            yield context
            context._complete(SpanStatus.SUCCESS)
        except Exception as e:
            # Mark span as error
            context.set_error(
                message=str(e),
                error_type=type(e).__name__
            )
            context._complete(SpanStatus.ERROR)
            raise
        finally:
            self._pop_span()

    def start_span(
        self,
        span_type: SpanType,
        name: str,
        parent_span_id: Optional[int] = None,
        depth: int = 0,
        input_data: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None,
        model_name: Optional[str] = None,
        model_provider: Optional[str] = None,
        model_parameters: Optional[Dict[str, Any]] = None
    ) -> Span:
        """
        Manually start a span (for use with callbacks).

        Args:
            span_type: Type of span
            name: Human-readable name
            parent_span_id: Parent span ID (for hierarchy)
            depth: Nesting depth
            input_data: Optional input data
            tags: Optional tags
            metadata: Optional metadata
            tool_name: Tool name (for tool spans)
            model_name: Model name (for LLM spans)
            model_provider: Model provider (for LLM spans)
            model_parameters: Model parameters (for LLM spans)

        Returns:
            Created Span object
        """
        span = Span(
            session_id=self._session_id,
            trace_id=self._trace_id,
            parent_span_id=parent_span_id,
            span_order=self._next_order(),
            depth=depth,
            span_type=span_type,
            name=name,
            started_at=datetime.now(timezone.utc),
            status=SpanStatus.RUNNING,
            input=input_data,
            tags=tags or [],
            meta=metadata or {},
            tool_name=tool_name,
            model_name=model_name,
            model_provider=model_provider,
            model_parameters=model_parameters
        )

        self._db.add(span)
        self._db.commit()
        self._db.refresh(span)

        logger.debug(
            f"Started span {span.id} ({span_type.value}: {name}) "
            f"trace={self._trace_id} parent={parent_span_id} depth={depth}"
        )

        return span

    def end_span(
        self,
        span: Span,
        status: SpanStatus = SpanStatus.SUCCESS,
        output: Optional[Dict[str, Any]] = None,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None,
        cost_usd: Optional[Union[float, Decimal]] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        error_stack: Optional[str] = None
    ) -> Span:
        """
        Manually end a span (for use with callbacks).

        Args:
            span: Span to end
            status: Final status
            output: Output data
            tokens_input: Input tokens (LLM spans)
            tokens_output: Output tokens (LLM spans)
            cost_usd: Cost in USD (LLM spans)
            error_message: Error message (for error status)
            error_type: Error type (for error status)
            error_stack: Error stack trace (for error status)

        Returns:
            Updated Span object
        """
        span.ended_at = datetime.now(timezone.utc)

        if span.started_at:
            # Handle timezone-naive datetimes (SQLite compatibility)
            started_at = span.started_at
            ended_at = span.ended_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            if ended_at.tzinfo is None:
                ended_at = ended_at.replace(tzinfo=timezone.utc)
            delta = ended_at - started_at
            span.duration_ms = int(delta.total_seconds() * 1000)

        span.status = status

        if output is not None:
            span.output = output

        if tokens_input is not None:
            span.tokens_input = tokens_input
        if tokens_output is not None:
            span.tokens_output = tokens_output
        if tokens_input is not None or tokens_output is not None:
            span.tokens_total = (tokens_input or 0) + (tokens_output or 0)

        if cost_usd is not None:
            span.cost_usd = Decimal(str(cost_usd))

        if error_message:
            span.error_message = error_message
            span.error_type = error_type
            span.error_stack = error_stack

        self._db.commit()
        self._db.refresh(span)

        logger.debug(
            f"Ended span {span.id} ({span.span_type.value}: {span.name}) "
            f"status={status.value} duration={span.duration_ms}ms"
        )

        return span

    def record_thought(
        self,
        thought: str,
        parent_span_id: Optional[int] = None
    ) -> Span:
        """
        Record a thought span (agent reasoning).

        Args:
            thought: Thought content
            parent_span_id: Parent span ID (uses current if not provided)

        Returns:
            Created span
        """
        parent = parent_span_id or (self.current_span.id if self.current_span else None)
        depth = (self.current_span.depth + 1) if self.current_span else 0

        span = self.start_span(
            span_type=SpanType.THOUGHT,
            name="Agent Thought",
            parent_span_id=parent,
            depth=depth,
            input_data={"thought": thought}
        )

        # Thoughts are instantaneous
        return self.end_span(span, status=SpanStatus.SUCCESS)

    def record_error(
        self,
        error: Exception,
        parent_span_id: Optional[int] = None,
        include_stack: bool = True
    ) -> Span:
        """
        Record an error span.

        Args:
            error: Exception that occurred
            parent_span_id: Parent span ID
            include_stack: Whether to include stack trace

        Returns:
            Created span
        """
        import traceback

        parent = parent_span_id or (self.current_span.id if self.current_span else None)
        depth = (self.current_span.depth + 1) if self.current_span else 0

        span = self.start_span(
            span_type=SpanType.ERROR,
            name=type(error).__name__,
            parent_span_id=parent,
            depth=depth
        )

        stack_trace = traceback.format_exc() if include_stack else None

        return self.end_span(
            span,
            status=SpanStatus.ERROR,
            error_message=str(error),
            error_type=type(error).__name__,
            error_stack=stack_trace
        )

    def get_spans(self) -> List[Span]:
        """Get all spans for this trace, ordered by span_order"""
        return (
            self._db.query(Span)
            .filter(Span.trace_id == self._trace_id)
            .order_by(Span.span_order)
            .all()
        )

    def get_token_totals(self) -> Dict[str, Any]:
        """
        Get aggregated token counts from all LLM spans in this trace.

        Returns:
            Dictionary with tokens_input, tokens_output, total_tokens, and cost_usd
        """
        spans = self.get_spans()

        # Only count LLM spans for accurate token totals
        llm_spans = [s for s in spans if s.span_type == SpanType.LLM]

        tokens_input = sum(s.tokens_input or 0 for s in llm_spans)
        tokens_output = sum(s.tokens_output or 0 for s in llm_spans)
        total_tokens = tokens_input + tokens_output
        total_cost = sum(s.cost_usd or Decimal(0) for s in llm_spans)

        return {
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "total_tokens": total_tokens,
            "cost_usd": float(total_cost)
        }

    def get_trace_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current trace.

        Returns:
            Dictionary with trace statistics
        """
        spans = self.get_spans()

        total_tokens = sum(s.tokens_total or 0 for s in spans)
        total_cost = sum(s.cost_usd or Decimal(0) for s in spans)
        error_count = sum(1 for s in spans if s.status == SpanStatus.ERROR)

        root = next((s for s in spans if s.parent_span_id is None), None)

        return {
            "trace_id": str(self._trace_id),
            "session_id": self._session_id,
            "span_count": len(spans),
            "root_span_name": root.name if root else None,
            "total_duration_ms": root.duration_ms if root else None,
            "total_tokens": total_tokens,
            "total_cost_usd": float(total_cost),
            "error_count": error_count,
            "status": root.status.value if root else "unknown"
        }


def create_span_recorder(
    db: DBSession,
    session_id: int,
    trace_id: Optional[UUID] = None
) -> SpanRecorder:
    """
    Convenience function to create a span recorder.

    Args:
        db: Database session
        session_id: Session ID
        trace_id: Optional trace ID (generated if not provided)

    Returns:
        SpanRecorder instance
    """
    return SpanRecorder(
        db=db,
        session_id=session_id,
        trace_id=trace_id
    )
