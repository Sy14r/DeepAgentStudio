"""MCP tools for session and introspection operations."""
from typing import List, Optional, Dict, Any

from mcp.types import TextContent
from sqlalchemy import or_

from ..server import mcp_tool
from ..context import MCPContext, get_context
from ..auth import get_agent_permissions
from ..errors import ResourceNotFound
from ...models.session import Session, Message, TraceStep
from ...models.agent import Agent, AgentVersion
from ...models.agent_permission import AgentPermission, PermissionPreset


@mcp_tool(
    name="introspect_whoami",
    description="Get information about the current agent including its effective permissions. Always allowed.",
    permission="agents:read",  # Will be handled specially - always allowed for self
    input_schema={
        "type": "object",
        "properties": {}
    }
)
async def whoami(ctx: MCPContext) -> List[TextContent]:
    """Get current agent info and effective permissions."""
    result = {
        "user_id": ctx.user_id,
        "agent_id": ctx.agent_id,
        "session_id": ctx.session_id,
        "is_direct_user_call": ctx.agent_id is None
    }

    if ctx.agent_id:
        # Get agent details
        agent = ctx.db.query(Agent).filter(Agent.id == ctx.agent_id).first()
        if agent:
            result["agent"] = {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "is_builtin": agent.is_builtin
            }

        # Get permissions
        agent_perm = ctx.db.query(AgentPermission).filter(
            AgentPermission.agent_id == ctx.agent_id
        ).first()

        if agent_perm:
            result["permission_preset"] = agent_perm.preset
            result["custom_permissions"] = agent_perm.custom_permissions
        else:
            result["permission_preset"] = PermissionPreset.OBSERVER.value
            result["custom_permissions"] = None

        # Get effective permissions
        permissions = get_agent_permissions(ctx)
        result["effective_permissions"] = sorted(list(permissions))
    else:
        result["effective_permissions"] = ["*"]  # Full access for direct user calls

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="sessions_get_current",
    description="Get details about the current session including message history.",
    permission="sessions:read:own",
    input_schema={
        "type": "object",
        "properties": {
            "include_messages": {
                "type": "boolean",
                "description": "Include message history",
                "default": True
            },
            "message_limit": {
                "type": "integer",
                "description": "Maximum number of messages to return",
                "default": 50
            }
        }
    }
)
async def get_current_session(
    ctx: MCPContext,
    include_messages: bool = True,
    message_limit: int = 50
) -> List[TextContent]:
    """Get current session details."""
    if not ctx.session_id:
        return [TextContent(type="text", text="{'error': 'No session context'}")]

    session = ctx.db.query(Session).filter(
        Session.id == ctx.session_id,
        Session.user_id == ctx.user_id
    ).first()

    if not session:
        raise ResourceNotFound(resource_type="session", resource_id=ctx.session_id)

    result = {
        "id": session.id,
        "agent_id": session.agent_id,
        "status": session.status.value if session.status else None,
        "title": session.title,
        "total_tokens_input": session.total_tokens_input,
        "total_tokens_output": session.total_tokens_output,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None
    }

    if include_messages:
        messages = ctx.db.query(Message).filter(
            Message.session_id == ctx.session_id
        ).order_by(Message.created_at.desc()).limit(message_limit).all()

        result["messages"] = [
            {
                "id": m.id,
                "role": m.role.value if m.role else None,
                "content": m.content[:500] + "..." if len(m.content) > 500 else m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in reversed(messages)  # Reverse to get chronological order
        ]
        result["message_count"] = len(messages)

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="sessions_list",
    description="List sessions for the current user, optionally filtered by agent.",
    permission="sessions:list",
    input_schema={
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "integer",
                "description": "Filter by agent ID"
            },
            "status": {
                "type": "string",
                "enum": ["active", "completed", "failed", "cancelled"],
                "description": "Filter by session status"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of sessions to return",
                "default": 20
            },
            "offset": {
                "type": "integer",
                "description": "Number of sessions to skip",
                "default": 0
            }
        }
    }
)
async def list_sessions(
    ctx: MCPContext,
    agent_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
) -> List[TextContent]:
    """List sessions for the current user."""
    from ...models.session import SessionStatus

    query = ctx.db.query(Session).filter(Session.user_id == ctx.user_id)

    if agent_id:
        query = query.filter(Session.agent_id == agent_id)

    if status:
        try:
            session_status = SessionStatus(status)
            query = query.filter(Session.status == session_status)
        except ValueError:
            pass

    total = query.count()
    sessions = query.order_by(Session.updated_at.desc()).offset(offset).limit(limit).all()

    result = {
        "total": total,
        "offset": offset,
        "limit": limit,
        "sessions": [
            {
                "id": s.id,
                "agent_id": s.agent_id,
                "status": s.status.value if s.status else None,
                "title": s.title,
                "total_tokens_input": s.total_tokens_input,
                "total_tokens_output": s.total_tokens_output,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None
            }
            for s in sessions
        ]
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="sessions_get_traces",
    description="Get execution traces for a session.",
    permission="sessions:read:own",
    input_schema={
        "type": "object",
        "properties": {
            "session_id": {
                "type": "integer",
                "description": "Session ID (defaults to current session)"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of trace steps to return",
                "default": 100
            }
        }
    }
)
async def get_session_traces(
    ctx: MCPContext,
    session_id: Optional[int] = None,
    limit: int = 100
) -> List[TextContent]:
    """Get execution traces for a session."""
    target_session_id = session_id or ctx.session_id

    if not target_session_id:
        return [TextContent(type="text", text="{'error': 'No session specified'}")]

    # Verify session ownership
    session = ctx.db.query(Session).filter(
        Session.id == target_session_id,
        Session.user_id == ctx.user_id
    ).first()

    if not session:
        raise ResourceNotFound(resource_type="session", resource_id=target_session_id)

    traces = ctx.db.query(TraceStep).filter(
        TraceStep.session_id == target_session_id
    ).order_by(TraceStep.created_at).limit(limit).all()

    result = {
        "session_id": target_session_id,
        "trace_count": len(traces),
        "traces": [
            {
                "id": t.id,
                "step_type": t.step_type.value if t.step_type else None,
                "name": t.name,
                "input_data": t.input_data,
                "output_data": t.output_data,
                "duration_ms": t.duration_ms,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in traces
        ]
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="agents_list_versions",
    description="List version history for an agent.",
    permission="agents:read",
    input_schema={
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "integer",
                "description": "Agent ID (defaults to current agent for agent calls)"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of versions to return",
                "default": 20
            }
        }
    }
)
async def list_agent_versions(
    ctx: MCPContext,
    agent_id: Optional[int] = None,
    limit: int = 20
) -> List[TextContent]:
    """List version history for an agent."""
    target_agent_id = agent_id or ctx.agent_id

    if not target_agent_id:
        return [TextContent(type="text", text="{'error': 'No agent specified'}")]

    # Verify agent access
    agent = ctx.db.query(Agent).filter(
        Agent.id == target_agent_id,
        or_(
            Agent.user_id == ctx.user_id,
            Agent.is_builtin == True
        )
    ).first()

    if not agent:
        raise ResourceNotFound(resource_type="agent", resource_id=target_agent_id)

    versions = ctx.db.query(AgentVersion).filter(
        AgentVersion.agent_id == target_agent_id
    ).order_by(AgentVersion.version_number.desc()).limit(limit).all()

    result = {
        "agent_id": target_agent_id,
        "agent_name": agent.name,
        "current_version_id": agent.current_version_id,
        "version_count": len(versions),
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "is_current": v.id == agent.current_version_id,
                "config": v.config,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "created_by": v.created_by
            }
            for v in versions
        ]
    }

    return [TextContent(type="text", text=str(result))]


# List of all tools in this module for registration
TOOLS = [
    whoami,
    get_current_session,
    list_sessions,
    get_session_traces,
    list_agent_versions
]
