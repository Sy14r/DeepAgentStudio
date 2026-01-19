"""MCP Server package for DeepAgentStudio."""
from .permissions import (
    PERMISSION_PRESETS,
    resolve_permissions,
    has_permission,
)
from .context import (
    MCPContext,
    create_context,
    get_context,
    set_context,
    reset_context,
)
from .errors import (
    MCPError,
    PermissionDenied,
    ResourceNotFound,
    ValidationError,
    RateLimitExceeded,
    InternalError,
)
from .auth import (
    require_permission,
    check_resource_ownership,
    check_self_or_owned,
    require_self_permission,
    get_agent_permissions,
)

__all__ = [
    # Permissions
    "PERMISSION_PRESETS",
    "resolve_permissions",
    "has_permission",
    # Context
    "MCPContext",
    "create_context",
    "get_context",
    "set_context",
    "reset_context",
    # Errors
    "MCPError",
    "PermissionDenied",
    "ResourceNotFound",
    "ValidationError",
    "RateLimitExceeded",
    "InternalError",
    # Auth
    "require_permission",
    "check_resource_ownership",
    "check_self_or_owned",
    "require_self_permission",
    "get_agent_permissions",
]
