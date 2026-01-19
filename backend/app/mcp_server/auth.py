"""Authentication and authorization for MCP server."""
from typing import Type, TypeVar, Any, Optional, Set

from sqlalchemy.orm import Session

from .context import MCPContext, get_context
from .permissions import resolve_permissions, has_permission
from .errors import PermissionDenied, ResourceNotFound
from ..models.agent_permission import AgentPermission, PermissionPreset
from ..database import Base

T = TypeVar("T", bound=Base)


def get_agent_permissions(ctx: MCPContext) -> Set[str]:
    """
    Get the resolved permissions for the current context.

    If permissions are cached in context, returns those.
    Otherwise loads from database and caches.

    Args:
        ctx: The MCP context

    Returns:
        Set of permission strings
    """
    # Check if already cached
    if ctx.permissions is not None:
        return ctx.permissions

    # Direct user calls get full access
    if ctx.agent_id is None:
        return {"*"}  # Wildcard for full access

    # Load agent's permissions from database
    agent_perm = ctx.db.query(AgentPermission).filter(
        AgentPermission.agent_id == ctx.agent_id
    ).first()

    if agent_perm:
        preset = agent_perm.preset
        custom = agent_perm.custom_permissions
    else:
        # Default to observer if no explicit permissions
        preset = PermissionPreset.OBSERVER.value
        custom = None

    permissions = resolve_permissions(preset, custom)
    return permissions


def require_permission(ctx: MCPContext, permission: str) -> None:
    """
    Check that the current context has the required permission.

    If called directly by user (no agent_id), all permissions are granted.
    If called by an agent, checks agent's permission preset.

    Args:
        ctx: The MCP context
        permission: Required permission string (e.g., "agents:create")

    Raises:
        PermissionDenied: If permission is not granted
    """
    # Direct user calls bypass agent permission checks
    if ctx.agent_id is None:
        return

    permissions = get_agent_permissions(ctx)

    if not has_permission(permissions, permission):
        raise PermissionDenied(action=permission)


def check_resource_ownership(
    ctx: MCPContext,
    model: Type[T],
    resource_id: int,
    user_field: str = "user_id",
    allow_builtin: bool = False
) -> T:
    """
    Verify resource exists and belongs to the current user.

    Args:
        ctx: The MCP context
        model: SQLAlchemy model class
        resource_id: ID of the resource
        user_field: Name of the user_id field on the model
        allow_builtin: If True, also allows access to builtin resources

    Returns:
        The resource instance

    Raises:
        ResourceNotFound: If resource doesn't exist or doesn't belong to user
    """
    query = ctx.db.query(model).filter(model.id == resource_id)

    # Check ownership or builtin status
    if allow_builtin and hasattr(model, 'is_builtin'):
        from sqlalchemy import or_
        query = query.filter(
            or_(
                getattr(model, user_field) == ctx.user_id,
                model.is_builtin == True
            )
        )
    else:
        query = query.filter(getattr(model, user_field) == ctx.user_id)

    resource = query.first()

    if not resource:
        raise ResourceNotFound(
            resource_type=model.__tablename__,
            resource_id=resource_id
        )

    return resource


def check_self_or_owned(
    ctx: MCPContext,
    resource_agent_id: int
) -> bool:
    """
    Check if the resource belongs to the calling agent (self) or is owned.

    Used for :self permission checks.

    Args:
        ctx: The MCP context
        resource_agent_id: Agent ID of the resource being accessed

    Returns:
        True if this is a "self" access (agent modifying itself)
    """
    return ctx.agent_id is not None and ctx.agent_id == resource_agent_id


def require_self_permission(ctx: MCPContext, base_permission: str, target_agent_id: int) -> None:
    """
    Check permission with :self variant if applicable.

    If agent is modifying itself, checks for base_permission:self.
    Otherwise checks for the full base_permission.

    Args:
        ctx: The MCP context
        base_permission: Base permission (e.g., "agents:update")
        target_agent_id: Agent ID being modified

    Raises:
        PermissionDenied: If permission is not granted
    """
    if ctx.agent_id is None:
        return  # Direct user call

    if check_self_or_owned(ctx, target_agent_id):
        # Agent modifying itself - check for :self permission
        require_permission(ctx, f"{base_permission}:self")
    else:
        # Agent modifying another agent - need full permission
        require_permission(ctx, base_permission)
