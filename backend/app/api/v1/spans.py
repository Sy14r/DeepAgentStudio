"""
Span management API endpoints for Enhanced Tracing System.

This module provides endpoints for:
- Listing spans with filtering
- Getting span details
- Getting hierarchical span tree
- Getting span statistics

Implements Phase 1 of ENHANCED_TRACING_SPEC.md.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session as DBSession
from typing import List, Optional
from uuid import UUID

from ...database import get_db
from ...models.user import User
from ...models.session import Session, Span, SpanType, SpanStatus
from ...schemas.span import (
    SpanResponse,
    SpanTreeResponse,
    SpanStatsResponse,
    SpanListResponse,
    SpanFilterParams,
)
from ...services.span_service import SpanService, create_span_service
from ..deps import get_current_user

router = APIRouter()


def get_session_or_404(
    session_id: int,
    current_user: User,
    db: DBSession
) -> Session:
    """Helper to get session and verify ownership"""
    session = db.query(Session).filter(
        Session.id == session_id,
        Session.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return session


# ============================================================================
# Span List and Detail Endpoints
# ============================================================================

@router.get("/{session_id}/spans", response_model=SpanListResponse)
def list_spans(
    session_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    span_type: Optional[List[SpanType]] = Query(None, description="Filter by span type(s)"),
    status_filter: Optional[List[SpanStatus]] = Query(None, alias="status", description="Filter by status(es)"),
    min_duration_ms: Optional[int] = Query(None, ge=0, description="Minimum duration in ms"),
    max_duration_ms: Optional[int] = Query(None, ge=0, description="Maximum duration in ms"),
    has_error: Optional[bool] = Query(None, description="Filter by error presence"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags (AND logic)"),
    search: Optional[str] = Query(None, description="Search in name, input, output"),
    tool_name: Optional[str] = Query(None, description="Filter by tool name"),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    trace_id: Optional[UUID] = Query(None, description="Filter by trace ID"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    List spans for a session with optional filtering.

    Supports filtering by:
    - Span type (agent, llm, tool, etc.)
    - Status (running, success, error)
    - Duration range
    - Error presence
    - Tags
    - Search text
    - Tool name
    - Model name
    - Trace ID
    """
    # Verify session ownership
    get_session_or_404(session_id, current_user, db)

    # Build filter params
    filters = None
    if any([span_type, status_filter, min_duration_ms, max_duration_ms,
            has_error is not None, tags, search, tool_name, model_name]):
        filters = SpanFilterParams(
            span_type=span_type,
            status=status_filter,
            min_duration_ms=min_duration_ms,
            max_duration_ms=max_duration_ms,
            has_error=has_error,
            tags=tags,
            search=search,
            tool_name=tool_name,
            model_name=model_name
        )

    # If trace_id is specified, filter at query level
    service = create_span_service(db)

    # Get spans (with optional trace filter)
    query = db.query(Span).filter(Span.session_id == session_id)
    if trace_id:
        query = query.filter(Span.trace_id == trace_id)

    # Apply filters through service
    if filters:
        query = service._apply_filters(query, filters)

    # Get total count
    total = query.count()

    # Order and paginate
    query = query.order_by(Span.span_order)
    offset = (page - 1) * page_size
    spans = query.offset(offset).limit(page_size).all()

    return SpanListResponse(
        spans=[SpanResponse.model_validate(s) for s in spans],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{session_id}/spans/tree", response_model=SpanTreeResponse)
def get_span_tree(
    session_id: int,
    trace_id: Optional[UUID] = Query(None, description="Specific trace ID (uses most recent if not provided)"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Get hierarchical span tree for a session.

    Returns spans organized as a tree with parent-child relationships,
    along with aggregated statistics.

    If trace_id is not provided, returns the most recent trace.
    """
    # Verify session ownership
    get_session_or_404(session_id, current_user, db)

    service = create_span_service(db)
    return service.get_span_tree(session_id, trace_id)


@router.get("/{session_id}/spans/stats", response_model=SpanStatsResponse)
def get_span_stats(
    session_id: int,
    trace_id: Optional[UUID] = Query(None, description="Filter by trace ID"),
    span_type: Optional[List[SpanType]] = Query(None, description="Filter by span type(s)"),
    status_filter: Optional[List[SpanStatus]] = Query(None, alias="status", description="Filter by status(es)"),
    min_duration_ms: Optional[int] = Query(None, ge=0, description="Minimum duration in ms"),
    max_duration_ms: Optional[int] = Query(None, ge=0, description="Maximum duration in ms"),
    has_error: Optional[bool] = Query(None, description="Filter by error presence"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Get aggregated statistics for spans.

    Returns:
    - Total span count
    - Total duration
    - Token usage totals
    - Cost totals
    - Breakdown by type and status
    - Error count
    """
    # Verify session ownership
    get_session_or_404(session_id, current_user, db)

    # Build filter params
    filters = None
    if any([span_type, status_filter, min_duration_ms, max_duration_ms, has_error is not None]):
        filters = SpanFilterParams(
            span_type=span_type,
            status=status_filter,
            min_duration_ms=min_duration_ms,
            max_duration_ms=max_duration_ms,
            has_error=has_error
        )

    service = create_span_service(db)
    return service.get_span_stats(session_id, trace_id, filters)


@router.get("/{session_id}/spans/traces")
def list_traces(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    List all traces for a session.

    A trace represents a single agent invocation. Returns basic info
    about each trace including start time, span count, and root span name.
    """
    # Verify session ownership
    get_session_or_404(session_id, current_user, db)

    service = create_span_service(db)
    return service.get_traces_for_session(session_id)


@router.get("/{session_id}/spans/{span_id}", response_model=SpanResponse)
def get_span(
    session_id: int,
    span_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Get detailed information for a single span.

    Returns full span data including:
    - Timing (start, end, duration)
    - Input/output data
    - Token usage and cost (for LLM spans)
    - Tool information (for tool spans)
    - Error details (for error spans)
    - Metadata and tags
    """
    # Verify session ownership
    get_session_or_404(session_id, current_user, db)

    service = create_span_service(db)
    span = service.get_span(session_id, span_id)

    if not span:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Span not found"
        )

    return SpanResponse.model_validate(span)
