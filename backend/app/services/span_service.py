"""
Span Service for Enhanced Tracing System.

This service provides CRUD operations and query capabilities for spans:
- List spans with filtering
- Get single span details
- Get hierarchical span tree
- Get aggregated statistics

Implements Phase 1 of ENHANCED_TRACING_SPEC.md.
"""
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal
from uuid import UUID
import logging

from sqlalchemy import func, and_, or_, cast, String
from sqlalchemy.orm import Session as DBSession

from ..models.session import Span, SpanType, SpanStatus, Session
from ..schemas.span import (
    SpanResponse,
    SpanTreeNode,
    SpanTreeResponse,
    SpanStatsResponse,
    SpanListResponse,
    SpanFilterParams
)

logger = logging.getLogger(__name__)


class SpanServiceError(Exception):
    """Exception raised when span service operation fails"""
    pass


class SpanService:
    """
    Service for span CRUD operations and queries.

    Provides methods for listing, filtering, and aggregating span data.
    """

    def __init__(self, db: DBSession):
        """
        Initialize span service.

        Args:
            db: Database session
        """
        self._db = db

    def get_span(self, session_id: int, span_id: int) -> Optional[Span]:
        """
        Get a single span by ID.

        Args:
            session_id: Session ID (for authorization)
            span_id: Span ID

        Returns:
            Span object or None if not found
        """
        return (
            self._db.query(Span)
            .filter(Span.session_id == session_id, Span.id == span_id)
            .first()
        )

    def list_spans(
        self,
        session_id: int,
        filters: Optional[SpanFilterParams] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[Span], int]:
        """
        List spans for a session with optional filtering.

        Args:
            session_id: Session ID
            filters: Optional filter parameters
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Tuple of (list of spans, total count)
        """
        query = self._db.query(Span).filter(Span.session_id == session_id)

        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)

        # Get total count before pagination
        total = query.count()

        # Order and paginate
        query = query.order_by(Span.span_order)
        offset = (page - 1) * page_size
        spans = query.offset(offset).limit(page_size).all()

        return spans, total

    def _apply_filters(self, query, filters: SpanFilterParams):
        """Apply filters to a span query"""
        if filters.span_type:
            query = query.filter(Span.span_type.in_(filters.span_type))

        if filters.status:
            query = query.filter(Span.status.in_(filters.status))

        if filters.min_duration_ms is not None:
            query = query.filter(Span.duration_ms >= filters.min_duration_ms)

        if filters.max_duration_ms is not None:
            query = query.filter(Span.duration_ms <= filters.max_duration_ms)

        if filters.has_error is not None:
            if filters.has_error:
                query = query.filter(Span.status == SpanStatus.ERROR)
            else:
                query = query.filter(Span.status != SpanStatus.ERROR)

        if filters.tags:
            # Filter spans that have ALL specified tags (AND logic)
            for tag in filters.tags:
                query = query.filter(Span.tags.contains([tag]))

        if filters.tool_name:
            query = query.filter(Span.tool_name == filters.tool_name)

        if filters.model_name:
            query = query.filter(Span.model_name == filters.model_name)

        if filters.search:
            # Search in name, input, and output
            search_pattern = f"%{filters.search}%"
            query = query.filter(
                or_(
                    Span.name.ilike(search_pattern),
                    cast(Span.input, String).ilike(search_pattern),
                    cast(Span.output, String).ilike(search_pattern)
                )
            )

        return query

    def get_span_tree(self, session_id: int, trace_id: Optional[UUID] = None) -> SpanTreeResponse:
        """
        Get hierarchical span tree for a session.

        Args:
            session_id: Session ID
            trace_id: Optional trace ID (uses most recent trace if not provided)

        Returns:
            SpanTreeResponse with root span and stats
        """
        # Get all spans for the trace
        query = self._db.query(Span).filter(Span.session_id == session_id)

        if trace_id:
            query = query.filter(Span.trace_id == trace_id)
        else:
            # Get the most recent trace
            latest_trace = (
                self._db.query(Span.trace_id)
                .filter(Span.session_id == session_id)
                .order_by(Span.started_at.desc())
                .first()
            )
            if latest_trace:
                trace_id = latest_trace[0]
                query = query.filter(Span.trace_id == trace_id)

        spans = query.order_by(Span.span_order).all()

        if not spans:
            # Return empty tree with zero stats
            return SpanTreeResponse(
                trace_id=trace_id or UUID('00000000-0000-0000-0000-000000000000'),
                root_span=None,
                stats=SpanStatsResponse(
                    total_spans=0,
                    total_duration_ms=None,
                    total_tokens=0,
                    total_tokens_input=0,
                    total_tokens_output=0,
                    total_cost_usd=Decimal("0"),
                    span_count_by_type={},
                    span_count_by_status={},
                    error_count=0,
                    average_duration_ms=None
                )
            )

        # Build tree structure
        span_dict = {span.id: span for span in spans}
        root_spans: List[Span] = []
        children_map: Dict[int, List[Span]] = {}

        for span in spans:
            if span.parent_span_id is None:
                root_spans.append(span)
            else:
                if span.parent_span_id not in children_map:
                    children_map[span.parent_span_id] = []
                children_map[span.parent_span_id].append(span)

        # Select the primary root: the one with the lowest span_order (first in sequence)
        # Other orphaned spans (no parent) will be attached as children of the primary root
        root_span = None
        orphaned_spans: List[Span] = []
        if root_spans:
            # Sort by span_order to find the true root (first span in execution order)
            root_spans_sorted = sorted(root_spans, key=lambda s: s.span_order)
            root_span = root_spans_sorted[0]
            orphaned_spans = root_spans_sorted[1:]  # Other spans with no parent

            # Add orphaned spans as children of the root
            if orphaned_spans:
                if root_span.id not in children_map:
                    children_map[root_span.id] = []
                children_map[root_span.id].extend(orphaned_spans)

        # Recursive function to build tree node
        def build_tree_node(span: Span) -> SpanTreeNode:
            children = children_map.get(span.id, [])
            child_nodes = [build_tree_node(child) for child in sorted(children, key=lambda s: s.span_order)]

            return SpanTreeNode(
                id=span.id,
                span_type=SpanType(span.span_type.value),
                name=span.name,
                status=SpanStatus(span.status.value),
                started_at=span.started_at,
                ended_at=span.ended_at,
                duration_ms=span.duration_ms,
                depth=span.depth,
                tokens_total=span.tokens_total,
                cost_usd=span.cost_usd,
                tool_name=span.tool_name,
                error_message=span.error_message,
                children=child_nodes
            )

        root_node = build_tree_node(root_span) if root_span else None

        # Calculate stats
        stats = self._calculate_stats(spans)

        return SpanTreeResponse(
            trace_id=trace_id,
            root_span=root_node,
            stats=stats
        )

    def get_span_stats(
        self,
        session_id: int,
        trace_id: Optional[UUID] = None,
        filters: Optional[SpanFilterParams] = None
    ) -> SpanStatsResponse:
        """
        Get aggregated statistics for spans.

        Args:
            session_id: Session ID
            trace_id: Optional trace ID
            filters: Optional filters

        Returns:
            SpanStatsResponse with aggregated metrics
        """
        query = self._db.query(Span).filter(Span.session_id == session_id)

        if trace_id:
            query = query.filter(Span.trace_id == trace_id)

        if filters:
            query = self._apply_filters(query, filters)

        spans = query.all()
        return self._calculate_stats(spans)

    def _calculate_stats(self, spans: List[Span]) -> SpanStatsResponse:
        """Calculate statistics from a list of spans"""
        if not spans:
            return SpanStatsResponse(
                total_spans=0,
                total_duration_ms=None,
                total_tokens=0,
                total_tokens_input=0,
                total_tokens_output=0,
                total_cost_usd=Decimal("0"),
                span_count_by_type={},
                span_count_by_status={},
                error_count=0,
                average_duration_ms=None
            )

        # Calculate totals
        total_tokens_input = sum(s.tokens_input or 0 for s in spans)
        total_tokens_output = sum(s.tokens_output or 0 for s in spans)
        total_tokens = total_tokens_input + total_tokens_output
        total_cost = sum(s.cost_usd or Decimal(0) for s in spans)

        # Find root span for total duration
        root_span = next((s for s in spans if s.parent_span_id is None), None)
        total_duration = root_span.duration_ms if root_span else None

        # Count by type
        span_count_by_type: Dict[str, int] = {}
        for span in spans:
            type_name = span.span_type.value
            span_count_by_type[type_name] = span_count_by_type.get(type_name, 0) + 1

        # Count by status
        span_count_by_status: Dict[str, int] = {}
        for span in spans:
            status_name = span.status.value
            span_count_by_status[status_name] = span_count_by_status.get(status_name, 0) + 1

        # Error count
        error_count = span_count_by_status.get("error", 0)

        # Average duration
        durations = [s.duration_ms for s in spans if s.duration_ms is not None]
        average_duration = sum(durations) / len(durations) if durations else None

        return SpanStatsResponse(
            total_spans=len(spans),
            total_duration_ms=total_duration,
            total_tokens=total_tokens,
            total_tokens_input=total_tokens_input,
            total_tokens_output=total_tokens_output,
            total_cost_usd=total_cost,
            span_count_by_type=span_count_by_type,
            span_count_by_status=span_count_by_status,
            error_count=error_count,
            average_duration_ms=average_duration
        )

    def get_traces_for_session(self, session_id: int) -> List[Dict[str, Any]]:
        """
        Get all trace IDs for a session with basic info.

        Args:
            session_id: Session ID

        Returns:
            List of trace info dicts
        """
        # Get distinct trace IDs with their root spans
        traces = (
            self._db.query(
                Span.trace_id,
                func.min(Span.started_at).label('started_at'),
                func.max(Span.ended_at).label('ended_at'),
                func.count(Span.id).label('span_count')
            )
            .filter(Span.session_id == session_id)
            .group_by(Span.trace_id)
            .order_by(func.min(Span.started_at).desc())
            .all()
        )

        result = []
        for trace in traces:
            # Get root span for this trace
            root_span = (
                self._db.query(Span)
                .filter(
                    Span.session_id == session_id,
                    Span.trace_id == trace.trace_id,
                    Span.parent_span_id.is_(None)
                )
                .first()
            )

            result.append({
                "trace_id": str(trace.trace_id),
                "started_at": trace.started_at.isoformat() if trace.started_at else None,
                "ended_at": trace.ended_at.isoformat() if trace.ended_at else None,
                "span_count": trace.span_count,
                "root_span_name": root_span.name if root_span else None,
                "status": root_span.status.value if root_span else "unknown"
            })

        return result

    def delete_spans_for_session(self, session_id: int) -> int:
        """
        Delete all spans for a session.

        Args:
            session_id: Session ID

        Returns:
            Number of spans deleted
        """
        count = (
            self._db.query(Span)
            .filter(Span.session_id == session_id)
            .delete()
        )
        self._db.commit()
        logger.info(f"Deleted {count} spans for session {session_id}")
        return count


def create_span_service(db: DBSession) -> SpanService:
    """
    Convenience function to create a span service.

    Args:
        db: Database session

    Returns:
        SpanService instance
    """
    return SpanService(db)
