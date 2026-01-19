"""MCP tools for tool operations."""
from typing import List, Optional, Dict, Any

from mcp.types import TextContent
from sqlalchemy import or_

from ..server import mcp_tool
from ..context import MCPContext
from ..auth import check_resource_ownership
from ..errors import ResourceNotFound, ValidationError
from ...models.tool import Tool, ToolType, ToolCategory


@mcp_tool(
    name="tools_list",
    description="List all tools accessible to the user. Includes both built-in and custom tools.",
    permission="tools:list",
    input_schema={
        "type": "object",
        "properties": {
            "tool_type": {
                "type": "string",
                "enum": ["builtin", "custom"],
                "description": "Filter by tool type"
            },
            "category": {
                "type": "string",
                "description": "Filter by tool category"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of tools to return",
                "default": 50,
                "minimum": 1,
                "maximum": 100
            },
            "offset": {
                "type": "integer",
                "description": "Number of tools to skip",
                "default": 0,
                "minimum": 0
            }
        }
    }
)
async def list_tools(
    ctx: MCPContext,
    tool_type: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[TextContent]:
    """List all tools accessible to the user."""
    query = ctx.db.query(Tool).filter(
        or_(
            Tool.user_id == ctx.user_id,
            Tool.tool_type == ToolType.BUILTIN
        )
    )

    if tool_type == "builtin":
        query = query.filter(Tool.tool_type == ToolType.BUILTIN)
    elif tool_type == "custom":
        query = query.filter(Tool.tool_type == ToolType.CUSTOM)

    if category:
        query = query.filter(Tool.category == category)

    total = query.count()
    tools = query.order_by(Tool.name).offset(offset).limit(limit).all()

    result = {
        "total": total,
        "offset": offset,
        "limit": limit,
        "tools": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "tool_type": t.tool_type.value if t.tool_type else None,
                "category": t.category.value if t.category else None,
                "is_active": t.is_active
            }
            for t in tools
        ]
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="tools_read",
    description="Get detailed information about a specific tool including its configuration.",
    permission="tools:read",
    input_schema={
        "type": "object",
        "properties": {
            "tool_id": {
                "type": "integer",
                "description": "ID of the tool to retrieve"
            }
        },
        "required": ["tool_id"]
    }
)
async def read_tool(ctx: MCPContext, tool_id: int) -> List[TextContent]:
    """Get detailed information about a specific tool."""
    tool = ctx.db.query(Tool).filter(
        Tool.id == tool_id,
        or_(
            Tool.user_id == ctx.user_id,
            Tool.tool_type == ToolType.BUILTIN
        )
    ).first()

    if not tool:
        raise ResourceNotFound(resource_type="tool", resource_id=tool_id)

    result = {
        "id": tool.id,
        "name": tool.name,
        "description": tool.description,
        "tool_type": tool.tool_type.value if tool.tool_type else None,
        "category": tool.category.value if tool.category else None,
        "implementation": tool.implementation,
        "config_schema": tool.config_schema,
        "default_config": tool.default_config,
        "is_active": tool.is_active,
        "created_at": tool.created_at.isoformat() if tool.created_at else None,
        "updated_at": tool.updated_at.isoformat() if tool.updated_at else None
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="tools_create",
    description="Create a new custom tool with the specified configuration.",
    permission="tools:create",
    input_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the tool",
                "minLength": 1,
                "maxLength": 100
            },
            "description": {
                "type": "string",
                "description": "Description of what the tool does"
            },
            "category": {
                "type": "string",
                "enum": ["web", "file", "code", "data", "communication", "utility", "custom"],
                "description": "Category of the tool"
            },
            "implementation": {
                "type": "string",
                "description": "Python code implementing the tool"
            },
            "config_schema": {
                "type": "object",
                "description": "JSON Schema for tool configuration"
            },
            "default_config": {
                "type": "object",
                "description": "Default configuration values"
            }
        },
        "required": ["name", "description", "implementation"]
    }
)
async def create_tool(
    ctx: MCPContext,
    name: str,
    description: str,
    implementation: str,
    category: Optional[str] = None,
    config_schema: Optional[Dict[str, Any]] = None,
    default_config: Optional[Dict[str, Any]] = None
) -> List[TextContent]:
    """Create a new custom tool."""
    # Check if tool name already exists for user
    existing = ctx.db.query(Tool).filter(
        Tool.user_id == ctx.user_id,
        Tool.name == name
    ).first()

    if existing:
        raise ValidationError(field="name", reason=f"Tool with name '{name}' already exists")

    # Map category string to enum
    tool_category = None
    if category:
        try:
            tool_category = ToolCategory(category)
        except ValueError:
            tool_category = ToolCategory.CUSTOM

    tool = Tool(
        user_id=ctx.user_id,
        name=name,
        description=description,
        tool_type=ToolType.CUSTOM,
        category=tool_category or ToolCategory.CUSTOM,
        implementation=implementation,
        config_schema=config_schema,
        default_config=default_config,
        is_active=True
    )
    ctx.db.add(tool)
    ctx.db.commit()

    result = {
        "id": tool.id,
        "name": tool.name,
        "description": tool.description,
        "category": tool.category.value if tool.category else None,
        "created_at": tool.created_at.isoformat() if tool.created_at else None
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="tools_update",
    description="Update an existing custom tool.",
    permission="tools:update",
    input_schema={
        "type": "object",
        "properties": {
            "tool_id": {
                "type": "integer",
                "description": "ID of the tool to update"
            },
            "name": {
                "type": "string",
                "description": "New name for the tool"
            },
            "description": {
                "type": "string",
                "description": "New description"
            },
            "implementation": {
                "type": "string",
                "description": "New implementation code"
            },
            "config_schema": {
                "type": "object",
                "description": "New configuration schema"
            },
            "default_config": {
                "type": "object",
                "description": "New default configuration"
            },
            "is_active": {
                "type": "boolean",
                "description": "Whether the tool is active"
            }
        },
        "required": ["tool_id"]
    }
)
async def update_tool(
    ctx: MCPContext,
    tool_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    implementation: Optional[str] = None,
    config_schema: Optional[Dict[str, Any]] = None,
    default_config: Optional[Dict[str, Any]] = None,
    is_active: Optional[bool] = None
) -> List[TextContent]:
    """Update an existing custom tool."""
    # Get tool (must be custom and owned by user)
    tool = ctx.db.query(Tool).filter(
        Tool.id == tool_id,
        Tool.user_id == ctx.user_id,
        Tool.tool_type == ToolType.CUSTOM
    ).first()

    if not tool:
        raise ResourceNotFound(resource_type="tool", resource_id=tool_id)

    if name is not None:
        tool.name = name
    if description is not None:
        tool.description = description
    if implementation is not None:
        tool.implementation = implementation
    if config_schema is not None:
        tool.config_schema = config_schema
    if default_config is not None:
        tool.default_config = default_config
    if is_active is not None:
        tool.is_active = is_active

    ctx.db.commit()

    result = {
        "id": tool.id,
        "name": tool.name,
        "description": tool.description,
        "is_active": tool.is_active,
        "updated_at": tool.updated_at.isoformat() if tool.updated_at else None
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="tools_delete",
    description="Delete a custom tool.",
    permission="tools:delete",
    input_schema={
        "type": "object",
        "properties": {
            "tool_id": {
                "type": "integer",
                "description": "ID of the tool to delete"
            }
        },
        "required": ["tool_id"]
    }
)
async def delete_tool(ctx: MCPContext, tool_id: int) -> List[TextContent]:
    """Delete a custom tool."""
    # Get tool (must be custom and owned by user)
    tool = ctx.db.query(Tool).filter(
        Tool.id == tool_id,
        Tool.user_id == ctx.user_id,
        Tool.tool_type == ToolType.CUSTOM
    ).first()

    if not tool:
        raise ResourceNotFound(resource_type="tool", resource_id=tool_id)

    ctx.db.delete(tool)
    ctx.db.commit()

    return [TextContent(type="text", text=f"Tool {tool_id} deleted successfully")]


# List of all tools in this module for registration
TOOLS = [
    list_tools,
    read_tool,
    create_tool,
    update_tool,
    delete_tool
]
