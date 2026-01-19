"""
Session management API endpoints

This module provides comprehensive session management endpoints for:
- Session CRUD operations
- Message history management
- Execution trace tracking
- Session statistics and analytics
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timezone
from urllib.parse import quote

from ...database import get_db
from ...services.media_storage import get_media_storage_service
from ...services.workspace import get_workspace_service
from ...models.user import User
from ...models.agent import Agent
from ...models.session import Session, Message, TraceStep, SessionStatus, MessageRole, Span
from ...schemas.session import (
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    SessionDetailResponse,
    SessionListResponse,
    MessageCreate,
    MessageResponse,
    TraceStepCreate,
    TraceStepResponse,
    SessionStatistics,
    AgentSessionSummary,
)
from ..deps import get_current_user

router = APIRouter()


# ============================================================================
# Statistics and Analytics Endpoints (must be before /{session_id} routes)
# ============================================================================

@router.get("/statistics", response_model=SessionStatistics)
def get_session_statistics(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Get overall session statistics for the current user.

    Returns:
    - Total session count
    - Success/failure counts
    - Average latency
    - Token usage totals
    - Total cost
    - Success rate percentage
    """
    # Get all sessions for user
    total_sessions = db.query(Session).filter(
        Session.user_id == current_user.id
    ).count()

    # Count by status
    completed_sessions = db.query(Session).filter(
        Session.user_id == current_user.id,
        Session.status == SessionStatus.COMPLETED
    ).count()

    failed_sessions = db.query(Session).filter(
        Session.user_id == current_user.id,
        Session.status == SessionStatus.FAILED
    ).count()

    # Calculate average latency (only for completed sessions)
    avg_latency = db.query(func.avg(Session.total_latency_ms)).filter(
        Session.user_id == current_user.id,
        Session.status == SessionStatus.COMPLETED,
        Session.total_latency_ms.isnot(None)
    ).scalar()

    # Sum tokens
    total_tokens_in = db.query(func.sum(Session.token_usage_input)).filter(
        Session.user_id == current_user.id
    ).scalar() or 0

    total_tokens_out = db.query(func.sum(Session.token_usage_output)).filter(
        Session.user_id == current_user.id
    ).scalar() or 0

    total_tokens = total_tokens_in + total_tokens_out

    # Sum cost
    total_cost = db.query(func.sum(Session.total_cost)).filter(
        Session.user_id == current_user.id,
        Session.total_cost.isnot(None)
    ).scalar() or 0.0

    # Calculate success rate
    success_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0.0

    return SessionStatistics(
        total_sessions=total_sessions,
        completed_sessions=completed_sessions,
        failed_sessions=failed_sessions,
        average_latency_ms=float(avg_latency) if avg_latency else None,
        total_tokens_used=total_tokens,
        total_cost=float(total_cost),
        success_rate=success_rate
    )


@router.post("/backfill-costs")
def backfill_session_costs(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Backfill session costs from span data.

    This endpoint updates the total_cost field for all sessions
    that have spans but no cost recorded. It calculates the total
    cost from all spans associated with each session.

    Returns:
    - Number of sessions updated
    - Total sessions checked
    """
    from decimal import Decimal

    # Get all sessions for user that have null total_cost
    sessions_to_update = db.query(Session).filter(
        Session.user_id == current_user.id,
        Session.total_cost.is_(None)
    ).all()

    updated_count = 0
    for session in sessions_to_update:
        # Calculate total cost from spans
        total_cost = db.query(func.sum(Span.cost_usd)).filter(
            Span.session_id == session.id,
            Span.cost_usd.isnot(None)
        ).scalar()

        if total_cost and total_cost > Decimal(0):
            session.total_cost = float(total_cost)
            updated_count += 1

    db.commit()

    return {
        "message": f"Backfilled costs for {updated_count} sessions",
        "sessions_checked": len(sessions_to_update),
        "sessions_updated": updated_count
    }


# ============================================================================
# Session CRUD Endpoints
# ============================================================================

@router.post("", response_model=SessionDetailResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Create a new session for agent execution.

    Creates a session record with:
    - Associated agent (and optionally specific version)
    - Initial status (PENDING)
    - User-defined title and metadata
    """
    # Verify agent exists and belongs to user
    agent = db.query(Agent).filter(
        Agent.id == session_data.agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Determine agent version (use specified or current)
    agent_version_id = session_data.agent_version_id
    if agent_version_id is None and agent.current_version_id:
        agent_version_id = agent.current_version_id

    # Create session
    session = Session(
        user_id=current_user.id,
        agent_id=agent.id,
        agent_version_id=agent_version_id,
        title=session_data.title,
        status=SessionStatus.PENDING,
        meta=session_data.meta
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    # Return detailed response with empty messages and traces
    return SessionDetailResponse(
        **SessionResponse.model_validate(session).model_dump(),
        messages=[],
        trace_steps=[]
    )


@router.get("", response_model=SessionListResponse)
def list_sessions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    status_filter: Optional[SessionStatus] = Query(None, description="Filter by session status"),
    agent_id: Optional[int] = Query(None, description="Filter by agent ID"),
    exclude_evaluation: bool = Query(False, description="Exclude evaluation sessions"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    List all sessions for the current user with pagination and filters.

    Supports filtering by:
    - Session status (pending, running, completed, failed)
    - Agent ID
    - Exclude evaluation sessions (sessions with is_evaluation=true in metadata)
    """
    query = db.query(Session).filter(Session.user_id == current_user.id)

    if status_filter:
        query = query.filter(Session.status == status_filter)

    if agent_id:
        # Verify agent belongs to user
        agent = db.query(Agent).filter(
            Agent.id == agent_id,
            Agent.user_id == current_user.id
        ).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        query = query.filter(Session.agent_id == agent_id)

    if exclude_evaluation:
        # Exclude sessions that have is_evaluation=true in their metadata
        # Also exclude evaluator sessions (LLM Judge, Semantic Similarity) which have type='evaluator_session'
        # Use PostgreSQL JSON extraction
        from sqlalchemy import or_, and_, text
        query = query.filter(
            and_(
                # Exclude is_evaluation=true
                or_(
                    Session.meta.is_(None),
                    Session.meta.op('->>')('is_evaluation').is_(None),
                    Session.meta.op('->>')('is_evaluation') != 'true'
                ),
                # Exclude type=evaluator_session
                or_(
                    Session.meta.is_(None),
                    Session.meta.op('->>')('type').is_(None),
                    Session.meta.op('->>')('type') != 'evaluator_session'
                )
            )
        )

    total = query.count()
    sessions = query.order_by(Session.started_at.desc()).offset(skip).limit(limit).all()

    return SessionListResponse(
        sessions=[SessionResponse.model_validate(s) for s in sessions],
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Get detailed session information including messages and traces.

    Returns complete session data:
    - Session metadata and metrics
    - Conversation messages (ordered by sequence)
    - Execution trace steps (ordered by step number)
    """
    session = db.query(Session).filter(
        Session.id == session_id,
        Session.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Build detailed response with messages and traces
    return SessionDetailResponse(
        **SessionResponse.model_validate(session).model_dump(),
        messages=[MessageResponse.model_validate(m) for m in session.messages],
        trace_steps=[TraceStepResponse.model_validate(t) for t in session.trace_steps]
    )


@router.put("/{session_id}", response_model=SessionDetailResponse)
def update_session(
    session_id: int,
    session_data: SessionUpdate,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Update session metadata and metrics.

    Can update:
    - Title
    - Status
    - Completion timestamp
    - Performance metrics (latency, tokens, cost)
    - Error information
    - Custom metadata

    Note: Cannot change agent association. Messages and traces
    are updated via separate endpoints.
    """
    session = db.query(Session).filter(
        Session.id == session_id,
        Session.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Update fields
    update_data = session_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(session, field, value)

    db.commit()
    db.refresh(session)

    # Return detailed response
    return SessionDetailResponse(
        **SessionResponse.model_validate(session).model_dump(),
        messages=[MessageResponse.model_validate(m) for m in session.messages],
        trace_steps=[TraceStepResponse.model_validate(t) for t in session.trace_steps]
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Delete a session (hard delete).

    Cascades to:
    - All messages in the session
    - All trace steps in the session
    """
    session = db.query(Session).filter(
        Session.id == session_id,
        Session.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    db.delete(session)
    db.commit()
    return None


# ============================================================================
# Message Management Endpoints
# ============================================================================

@router.get("/{session_id}/messages", response_model=List[MessageResponse])
def list_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Get all messages for a session, ordered by sequence number.
    """
    # Verify session ownership
    session = db.query(Session).filter(
        Session.id == session_id,
        Session.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    messages = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.sequence_number).all()

    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/{session_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(
    session_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Add a new message to a session.

    Automatically assigns sequence number based on existing messages.
    """
    # Verify session ownership
    session = db.query(Session).filter(
        Session.id == session_id,
        Session.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get next sequence number
    max_seq = db.query(func.max(Message.sequence_number)).filter(
        Message.session_id == session_id
    ).scalar()

    next_seq = (max_seq + 1) if max_seq is not None else 0

    # Create message
    message = Message(
        session_id=session_id,
        sequence_number=next_seq,
        role=message_data.role,
        content=message_data.content,
        tool_calls=message_data.tool_calls,
        tool_call_id=message_data.tool_call_id,
        meta=message_data.meta
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return MessageResponse.model_validate(message)


# ============================================================================
# Trace Step Management Endpoints
# ============================================================================

@router.get("/{session_id}/traces", response_model=List[TraceStepResponse])
def list_session_traces(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Get all trace steps for a session, ordered by step number.
    """
    # Verify session ownership
    session = db.query(Session).filter(
        Session.id == session_id,
        Session.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    traces = db.query(TraceStep).filter(
        TraceStep.session_id == session_id
    ).order_by(TraceStep.step_number).all()

    return [TraceStepResponse.model_validate(t) for t in traces]


@router.post("/{session_id}/traces", response_model=TraceStepResponse, status_code=status.HTTP_201_CREATED)
def create_trace_step(
    session_id: int,
    trace_data: TraceStepCreate,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Add a new trace step to a session.

    Automatically assigns step number based on existing steps.
    """
    # Verify session ownership
    session = db.query(Session).filter(
        Session.id == session_id,
        Session.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get next step number
    max_step = db.query(func.max(TraceStep.step_number)).filter(
        TraceStep.session_id == session_id
    ).scalar()

    next_step = (max_step + 1) if max_step is not None else 0

    # Create trace step
    trace = TraceStep(
        session_id=session_id,
        step_number=next_step,
        step_type=trace_data.step_type,
        content=trace_data.content,
        tool_name=trace_data.tool_name,
        tool_input=trace_data.tool_input,
        tool_output=trace_data.tool_output,
        latency_ms=trace_data.latency_ms,
        meta=trace_data.meta
    )

    db.add(trace)
    db.commit()
    db.refresh(trace)

    return TraceStepResponse.model_validate(trace)


# ============================================================================
# Agent-specific Analytics Endpoints
# ============================================================================

@router.get("/agents/{agent_id}/summary", response_model=AgentSessionSummary)
def get_agent_session_summary(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Get session summary for a specific agent.

    Returns per-agent statistics:
    - Session count
    - Success/failure counts
    - Average latency
    - Total tokens used
    - Total cost
    """
    # Verify agent ownership
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Get session count
    session_count = db.query(Session).filter(
        Session.agent_id == agent_id
    ).count()

    # Count by status
    success_count = db.query(Session).filter(
        Session.agent_id == agent_id,
        Session.status == SessionStatus.COMPLETED
    ).count()

    failure_count = db.query(Session).filter(
        Session.agent_id == agent_id,
        Session.status == SessionStatus.FAILED
    ).count()

    # Average latency
    avg_latency = db.query(func.avg(Session.total_latency_ms)).filter(
        Session.agent_id == agent_id,
        Session.status == SessionStatus.COMPLETED,
        Session.total_latency_ms.isnot(None)
    ).scalar()

    # Total tokens
    total_tokens_in = db.query(func.sum(Session.token_usage_input)).filter(
        Session.agent_id == agent_id
    ).scalar() or 0

    total_tokens_out = db.query(func.sum(Session.token_usage_output)).filter(
        Session.agent_id == agent_id
    ).scalar() or 0

    total_tokens = total_tokens_in + total_tokens_out

    # Total cost
    total_cost = db.query(func.sum(Session.total_cost)).filter(
        Session.agent_id == agent_id,
        Session.total_cost.isnot(None)
    ).scalar() or 0.0

    return AgentSessionSummary(
        agent_id=agent.id,
        agent_name=agent.name,
        session_count=session_count,
        success_count=success_count,
        failure_count=failure_count,
        average_latency_ms=float(avg_latency) if avg_latency else None,
        total_tokens=total_tokens,
        total_cost=float(total_cost)
    )


# ============================================================================
# Media File Serving Endpoint
# ============================================================================

@router.get("/{session_id}/media/{file_path:path}")
def get_session_media(
    session_id: int,
    file_path: str,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Serve a media file from a session's workspace.

    This endpoint serves generated media files (images, audio, video, files)
    from agent tool outputs like DALL-E image generation.

    Args:
        session_id: Session ID owning the media file
        file_path: Relative path within the session workspace (e.g., "_media/image.png")

    Returns:
        Raw file content with appropriate Content-Type header
    """
    # Verify session ownership
    session = db.query(Session).filter(
        Session.id == session_id,
        Session.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get media storage service
    media_storage = get_media_storage_service(db)

    # Retrieve the file
    content, mime_type = media_storage.get_media_file(session_id, file_path)

    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found"
        )

    # Return file with appropriate headers
    # Use RFC 5987 encoding for filename to handle special characters safely
    filename = file_path.split('/')[-1]
    encoded_filename = quote(filename, safe='')
    return Response(
        content=content,
        media_type=mime_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
            "Cache-Control": "max-age=3600"  # Cache for 1 hour
        }
    )


# ============================================================================
# Task Management Endpoints
# ============================================================================

@router.get("/{session_id}/tasks")
def get_session_tasks(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Get all tasks for a session's workspace.

    Returns the task list managed by the agent during execution,
    including task status, descriptions, and notes.

    Returns:
    - tasks: List of tasks with id, title, description, status, notes, timestamps
    """
    # Verify session ownership
    session = db.query(Session).filter(
        Session.id == session_id,
        Session.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get workspace service and fetch tasks
    workspace_service = get_workspace_service(db)
    result = workspace_service.get_tasks(session_id)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error or "Failed to get tasks"
        )

    return result.data
