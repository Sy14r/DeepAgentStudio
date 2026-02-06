"""MCP tools for agent operations."""
from typing import List, Optional, Dict, Any

from mcp.types import TextContent
from sqlalchemy import or_

from ..server import mcp_tool
from ..context import MCPContext
from ..auth import check_resource_ownership, require_self_permission
from ..errors import ResourceNotFound, ValidationError
from ...models.agent import Agent, AgentVersion
from ...models.agent_type import AgentTypeConfig


@mcp_tool(
    name="agents_list",
    description="List all agents accessible to the user. Returns agent IDs, names, descriptions, and types.",
    permission="agents:list",
    input_schema={
        "type": "object",
        "properties": {
            "include_inactive": {
                "type": "boolean",
                "description": "Include inactive agents in the list",
                "default": False
            },
            "agent_type_id": {
                "type": "integer",
                "description": "Filter by agent type ID"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of agents to return",
                "default": 50,
                "minimum": 1,
                "maximum": 100
            },
            "offset": {
                "type": "integer",
                "description": "Number of agents to skip",
                "default": 0,
                "minimum": 0
            }
        }
    }
)
async def list_agents(
    ctx: MCPContext,
    include_inactive: bool = False,
    agent_type_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0
) -> List[TextContent]:
    """List all agents accessible to the user."""
    query = ctx.db.query(Agent).filter(
        or_(
            Agent.user_id == ctx.user_id,
            Agent.is_builtin == True
        )
    )

    if not include_inactive:
        query = query.filter(Agent.is_active == True)

    if agent_type_id is not None:
        query = query.filter(Agent.agent_type_id == agent_type_id)

    total = query.count()
    agents = query.order_by(Agent.updated_at.desc()).offset(offset).limit(limit).all()

    result = {
        "total": total,
        "offset": offset,
        "limit": limit,
        "agents": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "agent_type_id": a.agent_type_id,
                "is_active": a.is_active,
                "is_builtin": a.is_builtin,
                "tags": a.tags,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None
            }
            for a in agents
        ]
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="agents_read",
    description="Get detailed information about a specific agent including its current configuration.",
    permission="agents:read",
    input_schema={
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "integer",
                "description": "ID of the agent to retrieve"
            }
        },
        "required": ["agent_id"]
    }
)
async def read_agent(ctx: MCPContext, agent_id: int) -> List[TextContent]:
    """Get detailed information about a specific agent."""
    agent = ctx.db.query(Agent).filter(
        Agent.id == agent_id,
        or_(
            Agent.user_id == ctx.user_id,
            Agent.is_builtin == True
        )
    ).first()

    if not agent:
        raise ResourceNotFound(resource_type="agent", resource_id=agent_id)

    # Get current version config
    current_config = None
    if agent.current_version_id:
        version = ctx.db.query(AgentVersion).filter(
            AgentVersion.id == agent.current_version_id
        ).first()
        if version:
            current_config = version.config

    # Get agent type info
    agent_type = None
    if agent.agent_type_id:
        at = ctx.db.query(AgentTypeConfig).filter(
            AgentTypeConfig.id == agent.agent_type_id
        ).first()
        if at:
            agent_type = {
                "id": at.id,
                "name": at.name,
                "description": at.description
            }

    result = {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "agent_type": agent_type,
        "tags": agent.tags,
        "is_active": agent.is_active,
        "is_builtin": agent.is_builtin,
        "current_version_id": agent.current_version_id,
        "config": current_config,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="agents_create",
    description="Create a new agent with the specified configuration.",
    permission="agents:create",
    input_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the agent",
                "minLength": 1,
                "maxLength": 100
            },
            "description": {
                "type": "string",
                "description": "Description of the agent"
            },
            "agent_type_id": {
                "type": "integer",
                "description": "ID of the agent type to use"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for categorizing the agent"
            },
            "config": {
                "type": "object",
                "description": "Agent configuration (LLM settings, etc.)",
                "properties": {
                    "llm": {
                        "type": "object",
                        "properties": {
                            "provider_id": {"type": "integer"},
                            "model": {"type": "string"},
                            "temperature": {"type": "number"}
                        }
                    }
                }
            }
        },
        "required": ["name", "agent_type_id", "config"]
    }
)
async def create_agent(
    ctx: MCPContext,
    name: str,
    agent_type_id: int,
    config: Dict[str, Any],
    description: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> List[TextContent]:
    """Create a new agent."""
    # Validate agent type exists and user has access
    agent_type = ctx.db.query(AgentTypeConfig).filter(
        AgentTypeConfig.id == agent_type_id
    ).first()

    if not agent_type:
        raise ResourceNotFound(resource_type="agent_type", resource_id=agent_type_id)

    if not agent_type.is_builtin and agent_type.user_id != ctx.user_id:
        raise ResourceNotFound(resource_type="agent_type", resource_id=agent_type_id)

    # Create agent
    agent = Agent(
        user_id=ctx.user_id,
        name=name,
        description=description or "",
        agent_type_id=agent_type_id,
        tags=tags or []
    )
    ctx.db.add(agent)
    ctx.db.flush()

    # Create first version
    version = AgentVersion(
        agent_id=agent.id,
        version_number=1,
        config=config,
        created_by=ctx.user_id
    )
    ctx.db.add(version)
    ctx.db.flush()

    # Set current version
    agent.current_version_id = version.id
    ctx.db.commit()

    result = {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "agent_type_id": agent.agent_type_id,
        "current_version_id": agent.current_version_id,
        "created_at": agent.created_at.isoformat() if agent.created_at else None
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="agents_update",
    description="Update an existing agent's configuration. Creates a new version.",
    permission="agents:update",
    input_schema={
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "integer",
                "description": "ID of the agent to update"
            },
            "name": {
                "type": "string",
                "description": "New name for the agent"
            },
            "description": {
                "type": "string",
                "description": "New description"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "New tags"
            },
            "config": {
                "type": "object",
                "description": "New configuration (creates new version)"
            }
        },
        "required": ["agent_id"]
    }
)
async def update_agent(
    ctx: MCPContext,
    agent_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    config: Optional[Dict[str, Any]] = None
) -> List[TextContent]:
    """Update an existing agent."""
    # Check self permission if agent is updating itself
    require_self_permission(ctx, "agents:update", agent_id)

    # Get agent (must be owned by user, not builtin)
    agent = ctx.db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == ctx.user_id,
        Agent.is_builtin == False
    ).first()

    if not agent:
        raise ResourceNotFound(resource_type="agent", resource_id=agent_id)

    # Update basic fields
    if name is not None:
        agent.name = name
    if description is not None:
        agent.description = description
    if tags is not None:
        agent.tags = tags

    # Create new version if config provided
    if config is not None:
        max_version = ctx.db.query(AgentVersion.version_number).filter(
            AgentVersion.agent_id == agent_id
        ).order_by(AgentVersion.version_number.desc()).first()

        next_version = (max_version[0] + 1) if max_version else 1

        version = AgentVersion(
            agent_id=agent.id,
            version_number=next_version,
            config=config,
            created_by=ctx.user_id
        )
        ctx.db.add(version)
        ctx.db.flush()

        agent.current_version_id = version.id

    ctx.db.commit()

    result = {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "tags": agent.tags,
        "current_version_id": agent.current_version_id,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="agents_delete",
    description="Delete an agent (soft delete by default).",
    permission="agents:delete",
    input_schema={
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "integer",
                "description": "ID of the agent to delete"
            },
            "hard_delete": {
                "type": "boolean",
                "description": "Permanently delete the agent",
                "default": False
            }
        },
        "required": ["agent_id"]
    }
)
async def delete_agent(
    ctx: MCPContext,
    agent_id: int,
    hard_delete: bool = False
) -> List[TextContent]:
    """Delete an agent."""
    # Get agent (must be owned by user, not builtin)
    agent = ctx.db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == ctx.user_id,
        Agent.is_builtin == False
    ).first()

    if not agent:
        raise ResourceNotFound(resource_type="agent", resource_id=agent_id)

    if hard_delete:
        ctx.db.delete(agent)
    else:
        agent.is_active = False

    ctx.db.commit()

    return [TextContent(type="text", text=f"Agent {agent_id} deleted successfully")]


@mcp_tool(
    name="agents_clone",
    description="Clone an existing agent to create an editable copy.",
    permission="agents:create",
    input_schema={
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "integer",
                "description": "ID of the agent to clone"
            },
            "new_name": {
                "type": "string",
                "description": "Name for the cloned agent (optional)"
            }
        },
        "required": ["agent_id"]
    }
)
async def clone_agent(
    ctx: MCPContext,
    agent_id: int,
    new_name: Optional[str] = None
) -> List[TextContent]:
    """Clone an existing agent."""
    # Get source agent (can be owned or builtin)
    source = ctx.db.query(Agent).filter(
        Agent.id == agent_id,
        or_(
            Agent.user_id == ctx.user_id,
            Agent.is_builtin == True
        )
    ).first()

    if not source:
        raise ResourceNotFound(resource_type="agent", resource_id=agent_id)

    # Generate clone name
    clone_name = new_name or f"{source.name} (Copy)"

    # Create cloned agent
    cloned = Agent(
        user_id=ctx.user_id,
        name=clone_name,
        description=source.description,
        agent_type_id=source.agent_type_id,
        tags=source.tags.copy() if source.tags else [],
        is_active=True,
        is_builtin=False
    )
    ctx.db.add(cloned)
    ctx.db.flush()

    # Clone current version
    if source.current_version_id:
        original_version = ctx.db.query(AgentVersion).filter(
            AgentVersion.id == source.current_version_id
        ).first()

        if original_version:
            cloned_version = AgentVersion(
                agent_id=cloned.id,
                version_number=1,
                config=original_version.config.copy() if original_version.config else {},
                created_by=ctx.user_id
            )
            ctx.db.add(cloned_version)
            ctx.db.flush()
            cloned.current_version_id = cloned_version.id

    ctx.db.commit()

    result = {
        "id": cloned.id,
        "name": cloned.name,
        "description": cloned.description,
        "source_agent_id": agent_id,
        "created_at": cloned.created_at.isoformat() if cloned.created_at else None
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="agents_assign_tools",
    description="Assign tools to an agent. Replaces existing tool assignments.",
    permission="agents:update:tools",
    input_schema={
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "integer",
                "description": "ID of the agent"
            },
            "tool_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "List of tool IDs to assign to the agent"
            }
        },
        "required": ["agent_id", "tool_ids"]
    }
)
async def assign_tools(
    ctx: MCPContext,
    agent_id: int,
    tool_ids: List[int]
) -> List[TextContent]:
    """Assign tools to an agent."""
    from ...models.tool import Tool
    from ...models.agent import AgentTool

    # Check permission for self-update
    require_self_permission(ctx, "agents:update:tools", agent_id)

    # Get agent (must be owned by user)
    agent = ctx.db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == ctx.user_id,
        Agent.is_builtin == False
    ).first()

    if not agent:
        raise ResourceNotFound(resource_type="agent", resource_id=agent_id)

    # Validate all tools exist and are accessible
    tools = ctx.db.query(Tool).filter(
        Tool.id.in_(tool_ids),
        or_(
            Tool.user_id == ctx.user_id,
            Tool.is_builtin == True
        )
    ).all()

    valid_ids = {t.id for t in tools}
    invalid_ids = set(tool_ids) - valid_ids
    if invalid_ids:
        raise ValidationError(
            message=f"Invalid tool IDs: {list(invalid_ids)}",
            details={"invalid_ids": list(invalid_ids)}
        )

    # Remove existing assignments
    ctx.db.query(AgentTool).filter(AgentTool.agent_id == agent_id).delete()

    # Create new assignments
    for tool_id in tool_ids:
        agent_tool = AgentTool(agent_id=agent_id, tool_id=tool_id)
        ctx.db.add(agent_tool)

    ctx.db.commit()

    result = {
        "agent_id": agent_id,
        "assigned_tools": tool_ids,
        "tool_count": len(tool_ids)
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="agents_assign_mcp_servers",
    description="Assign MCP servers to an agent. Replaces existing server assignments.",
    permission="agents:update:mcp_servers",
    input_schema={
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "integer",
                "description": "ID of the agent"
            },
            "mcp_server_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "List of MCP server IDs to assign"
            }
        },
        "required": ["agent_id", "mcp_server_ids"]
    }
)
async def assign_mcp_servers(
    ctx: MCPContext,
    agent_id: int,
    mcp_server_ids: List[int]
) -> List[TextContent]:
    """Assign MCP servers to an agent."""
    from ...models.mcp_server import MCPServer
    from ...models.agent import AgentMCPServer

    # Check permission for self-update
    require_self_permission(ctx, "agents:update:mcp_servers", agent_id)

    # Get agent (must be owned by user)
    agent = ctx.db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == ctx.user_id,
        Agent.is_builtin == False
    ).first()

    if not agent:
        raise ResourceNotFound(resource_type="agent", resource_id=agent_id)

    # Validate all MCP servers exist and are accessible
    servers = ctx.db.query(MCPServer).filter(
        MCPServer.id.in_(mcp_server_ids),
        or_(
            MCPServer.user_id == ctx.user_id,
            MCPServer.is_builtin == True
        )
    ).all()

    valid_ids = {s.id for s in servers}
    invalid_ids = set(mcp_server_ids) - valid_ids
    if invalid_ids:
        raise ValidationError(
            message=f"Invalid MCP server IDs: {list(invalid_ids)}",
            details={"invalid_ids": list(invalid_ids)}
        )

    # Remove existing assignments
    ctx.db.query(AgentMCPServer).filter(AgentMCPServer.agent_id == agent_id).delete()

    # Create new assignments
    for server_id in mcp_server_ids:
        agent_server = AgentMCPServer(agent_id=agent_id, mcp_server_id=server_id)
        ctx.db.add(agent_server)

    ctx.db.commit()

    result = {
        "agent_id": agent_id,
        "assigned_mcp_servers": mcp_server_ids,
        "server_count": len(mcp_server_ids)
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="agents_get_tools",
    description="Get the list of tools assigned to an agent.",
    permission="agents:read",
    input_schema={
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "integer",
                "description": "ID of the agent"
            }
        },
        "required": ["agent_id"]
    }
)
async def get_agent_tools(
    ctx: MCPContext,
    agent_id: int
) -> List[TextContent]:
    """Get tools assigned to an agent."""
    from ...models.tool import Tool
    from ...models.agent import AgentTool

    # Get agent (can be owned or builtin)
    agent = ctx.db.query(Agent).filter(
        Agent.id == agent_id,
        or_(
            Agent.user_id == ctx.user_id,
            Agent.is_builtin == True
        )
    ).first()

    if not agent:
        raise ResourceNotFound(resource_type="agent", resource_id=agent_id)

    # Get assigned tools via join
    tools = ctx.db.query(Tool).join(
        AgentTool, Tool.id == AgentTool.tool_id
    ).filter(
        AgentTool.agent_id == agent_id
    ).all()

    result = {
        "agent_id": agent_id,
        "tools": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "is_builtin": t.is_builtin
            }
            for t in tools
        ],
        "tool_count": len(tools)
    }

    return [TextContent(type="text", text=str(result))]


# List of all tools in this module for registration
TOOLS = [
    list_agents,
    read_agent,
    create_agent,
    update_agent,
    delete_agent,
    clone_agent,
    assign_tools,
    assign_mcp_servers,
    get_agent_tools
]
