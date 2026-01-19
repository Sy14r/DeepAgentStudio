"""MCP Server setup and configuration."""
import logging
from typing import Optional, List, Dict, Any
from functools import wraps

from mcp.server import Server
from mcp.types import Tool, TextContent

from .context import MCPContext, create_context, set_context, reset_context, get_context
from .auth import require_permission, get_agent_permissions
from .errors import MCPError, PermissionDenied
from ..models.mcp_audit_log import MCPAuditLog

logger = logging.getLogger(__name__)

# Create the MCP server instance
server = Server("deepagent-studio")


def get_server() -> Server:
    """Get the MCP server instance."""
    return server


def mcp_tool(
    name: str,
    description: str,
    permission: str,
    input_schema: Dict[str, Any]
):
    """
    Decorator for registering MCP tools with permission checking and audit logging.

    Args:
        name: Tool name (e.g., "agents_list")
        description: Human-readable description of the tool
        permission: Required permission (e.g., "agents:list")
        input_schema: JSON Schema for tool input

    Usage:
        @mcp_tool(
            name="agents_list",
            description="List all agents accessible to the user",
            permission="agents:list",
            input_schema={"type": "object", "properties": {...}}
        )
        async def list_agents(ctx: MCPContext, **kwargs) -> List[TextContent]:
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(**kwargs):
            ctx = get_context()
            success = False
            error_code = None

            try:
                # Check permission
                require_permission(ctx, permission)

                # Execute the tool
                result = await func(ctx, **kwargs)
                success = True
                return result

            except PermissionDenied as e:
                error_code = e.code
                raise
            except MCPError as e:
                error_code = e.code
                raise
            except Exception as e:
                error_code = "internal_error"
                logger.exception(f"Error in MCP tool {name}: {e}")
                raise
            finally:
                # Log the invocation
                try:
                    _log_invocation(
                        ctx=ctx,
                        tool_name=name,
                        action=permission.split(":")[1] if ":" in permission else permission,
                        resource_type=permission.split(":")[0] if ":" in permission else None,
                        success=success,
                        error_code=error_code,
                        request_summary=_summarize_request(kwargs)
                    )
                except Exception as log_error:
                    logger.error(f"Failed to log MCP invocation: {log_error}")

        # Store metadata for registration
        wrapper._mcp_tool_metadata = {
            "name": name,
            "description": description,
            "permission": permission,
            "input_schema": input_schema,
            "handler": wrapper
        }

        return wrapper

    return decorator


def _log_invocation(
    ctx: MCPContext,
    tool_name: str,
    action: str,
    resource_type: Optional[str],
    success: bool,
    error_code: Optional[str],
    request_summary: Optional[Dict[str, Any]]
) -> None:
    """Log an MCP tool invocation to the audit log."""
    log_entry = MCPAuditLog(
        user_id=ctx.user_id,
        agent_id=ctx.agent_id,
        session_id=ctx.session_id,
        tool_name=tool_name,
        action=action,
        resource_type=resource_type,
        success=success,
        error_code=error_code,
        request_summary=request_summary
    )
    ctx.db.add(log_entry)
    ctx.db.commit()


def _summarize_request(kwargs: Dict[str, Any], max_length: int = 500) -> Dict[str, Any]:
    """
    Create a summary of the request for audit logging.

    Truncates large values and removes sensitive data.
    """
    summary = {}
    sensitive_keys = {"password", "secret", "token", "key", "api_key"}

    for key, value in kwargs.items():
        if key.lower() in sensitive_keys:
            summary[key] = "[REDACTED]"
        elif isinstance(value, str) and len(value) > max_length:
            summary[key] = value[:max_length] + "..."
        elif isinstance(value, (dict, list)):
            str_value = str(value)
            if len(str_value) > max_length:
                summary[key] = str_value[:max_length] + "..."
            else:
                summary[key] = value
        else:
            summary[key] = value

    return summary


# Registry of all MCP tools
_registered_tools: Dict[str, Dict[str, Any]] = {}


def register_tool(tool_func) -> None:
    """Register a decorated MCP tool."""
    if hasattr(tool_func, "_mcp_tool_metadata"):
        metadata = tool_func._mcp_tool_metadata
        _registered_tools[metadata["name"]] = metadata
        logger.info(f"Registered MCP tool: {metadata['name']}")
    else:
        raise ValueError(f"Function {tool_func.__name__} is not decorated with @mcp_tool")


def get_registered_tools() -> Dict[str, Dict[str, Any]]:
    """Get all registered MCP tools."""
    return _registered_tools.copy()


def get_tools_for_permissions(permissions: set) -> List[Tool]:
    """
    Get MCP Tool objects for tools the user has permission to use.

    Args:
        permissions: Set of permission strings

    Returns:
        List of MCP Tool objects
    """
    from .permissions import has_permission

    tools = []
    for name, metadata in _registered_tools.items():
        required_perm = metadata["permission"]
        if has_permission(permissions, required_perm):
            tools.append(Tool(
                name=name,
                description=metadata["description"],
                inputSchema=metadata["input_schema"]
            ))

    return tools
