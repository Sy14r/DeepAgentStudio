"""Request context for MCP server operations."""
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional, Any, Set

from sqlalchemy.orm import Session


@dataclass
class MCPContext:
    """
    Context for MCP tool operations.

    Provides access to user identity, agent identity (if called by agent),
    database session, and resolved permissions.
    """
    user_id: int
    agent_id: Optional[int]
    db: Session
    session_id: Optional[int] = None
    permissions: Optional[Set[str]] = None


# Context variable for async-safe storage
_mcp_context: ContextVar[Optional[MCPContext]] = ContextVar("mcp_context", default=None)


def create_context(
    user: Any,  # User model instance
    db: Session,
    agent_id: Optional[int] = None,
    session_id: Optional[int] = None,
    permissions: Optional[Set[str]] = None
) -> MCPContext:
    """
    Create a new MCP context.

    Args:
        user: The authenticated user
        db: Database session
        agent_id: Optional agent ID if called by an agent
        session_id: Optional session ID for tracing
        permissions: Optional set of resolved permissions

    Returns:
        MCPContext instance
    """
    return MCPContext(
        user_id=user.id,
        agent_id=agent_id,
        db=db,
        session_id=session_id,
        permissions=permissions
    )


def set_context(ctx: MCPContext) -> Any:
    """Set the current MCP context. Returns token for reset."""
    return _mcp_context.set(ctx)


def get_context() -> MCPContext:
    """
    Get the current MCP context.

    Raises:
        RuntimeError: If no context is set
    """
    ctx = _mcp_context.get()
    if ctx is None:
        raise RuntimeError("No MCP context set")
    return ctx


def reset_context(token: Any) -> None:
    """Reset context to previous value using token from set_context."""
    _mcp_context.reset(token)
