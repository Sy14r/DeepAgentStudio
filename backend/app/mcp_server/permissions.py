"""Permission definitions and checking for MCP server."""
from typing import Optional, Set, List

from app.models.agent_permission import PermissionPreset


# Permission definitions for each preset
PERMISSION_PRESETS: dict[str, Set[str]] = {
    PermissionPreset.OBSERVER.value: {
        "agents:list",
        "agents:read",
        "tools:list",
        "tools:read",
        "prompts:list",
        "prompts:read",
        "datasets:list",
        "datasets:read",
        "evaluations:list",
        "evaluations:read",
        "sessions:read:own",
    },

    PermissionPreset.SELF_IMPROVE.value: {
        # Observer permissions
        "agents:list",
        "agents:read",
        "tools:list",
        "tools:read",
        "prompts:list",
        "prompts:read",
        "datasets:list",
        "datasets:read",
        "evaluations:list",
        "evaluations:read",
        "sessions:read:own",
        # Self-modification permissions
        "agents:update:self",
        "prompts:create",
        "prompts:update:own",
        "datasets:update:examples",
    },

    PermissionPreset.TOOL_CREATOR.value: {
        # Self-improve permissions
        "agents:list",
        "agents:read",
        "tools:list",
        "tools:read",
        "prompts:list",
        "prompts:read",
        "datasets:list",
        "datasets:read",
        "evaluations:list",
        "evaluations:read",
        "sessions:read:own",
        "agents:update:self",
        "prompts:create",
        "prompts:update:own",
        "datasets:update:examples",
        # Tool creation permissions
        "tools:create",
        "tools:update:own",
        "tools:generate_schema",
    },

    PermissionPreset.META_AGENT.value: {
        "agents:*",
        "tools:*",
        "prompts:*",
        "datasets:*",
        "evaluations:*",
        "sessions:read:own",
    },

    PermissionPreset.CUSTOM.value: set(),  # Custom uses custom_permissions field
}


def resolve_permissions(preset: str, custom_permissions: Optional[List[str]]) -> Set[str]:
    """
    Resolve a permission preset (or custom list) to a set of permissions.

    Args:
        preset: The permission preset value (string)
        custom_permissions: Custom permissions list (only used if preset is CUSTOM)

    Returns:
        Set of permission strings
    """
    if preset == PermissionPreset.CUSTOM.value:
        return set(custom_permissions or [])
    return PERMISSION_PRESETS.get(preset, set()).copy()


def has_permission(permissions: Set[str], required: str) -> bool:
    """
    Check if a permission set includes a required permission.

    Supports wildcards:
    - "agents:*" matches "agents:list", "agents:create", etc.
    - Exact matches take precedence

    Args:
        permissions: Set of granted permissions
        required: The permission to check for

    Returns:
        True if permission is granted
    """
    # Exact match
    if required in permissions:
        return True

    # Check for wildcard matches
    parts = required.split(":")
    if len(parts) >= 2:
        resource = parts[0]
        wildcard = f"{resource}:*"
        if wildcard in permissions:
            return True

    return False
