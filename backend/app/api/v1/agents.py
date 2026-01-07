"""
Agent management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import insert, delete as sql_delete
from typing import List, Optional
from pydantic import BaseModel
import logging

from ...database import get_db
from ...models.user import User
from ...models.agent import Agent, AgentVersion
from ...models.agent_type import AgentTypeConfig
from ...models.tool import Tool, ToolType, agent_tools
from ...models.mcp_server import MCPServerConfig, agent_mcp_servers
from ...schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentDetailResponse,
    AgentListResponse,
    AgentVersionResponse,
    AgentRollbackRequest,
)
from ...schemas.tool import (
    ToolResponse,
    AgentToolAssignment,
    AgentToolResponse,
)
from ...schemas.mcp_server import (
    AgentMCPServerAssignment,
    MCPServerConfigResponse,
)
from ...schemas.session import (
    InvokeRequest,
    InvokeResponse,
    TokenUsage,
)
from ...services.agent_executor import (
    AgentExecutorService,
    AgentNotFoundError,
    AgentConfigurationError,
    AgentExecutionTimeoutError,
)
from ..deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_agent_type_config_compact(agent_type_config: AgentTypeConfig) -> dict:
    """Helper to build compact agent type config response as dict"""
    return {
        "id": agent_type_config.id,
        "name": agent_type_config.name,
        "description": agent_type_config.description,
        "icon": agent_type_config.icon,
        "execution_strategy": agent_type_config.execution_strategy.value,
        "strategy_type": agent_type_config.strategy_type.value,
        "is_builtin": agent_type_config.is_builtin
    }


def _build_agent_detail_response(agent: Agent, db: Session) -> AgentDetailResponse:
    """Helper function to build AgentDetailResponse with current version"""
    current_version = None
    if agent.current_version_id:
        version = db.query(AgentVersion).filter(
            AgentVersion.id == agent.current_version_id
        ).first()
        if version:
            current_version = AgentVersionResponse.model_validate(version)

    # Build agent type config compact
    agent_type_config = None
    if agent.agent_type_config:
        agent_type_config = _build_agent_type_config_compact(agent.agent_type_config)

    return AgentDetailResponse(
        id=agent.id,
        user_id=agent.user_id,
        name=agent.name,
        description=agent.description,
        agent_type_id=agent.agent_type_id,
        agent_type_config=agent_type_config,
        tags=agent.tags,
        is_active=agent.is_active,
        is_builtin=agent.is_builtin,
        current_version_id=agent.current_version_id,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        current_version=current_version
    )


@router.post("", response_model=AgentDetailResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    agent_data: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new agent with initial version.

    Creates both an Agent record and its first AgentVersion.
    """
    # Validate agent_type_id exists and user has access
    agent_type_config = db.query(AgentTypeConfig).filter(
        AgentTypeConfig.id == agent_data.agent_type_id
    ).first()

    if not agent_type_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent type with ID {agent_data.agent_type_id} not found"
        )

    # Check access: builtin types are public, custom types must be owned by user
    if not agent_type_config.is_builtin and agent_type_config.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this agent type"
        )

    # Create agent
    agent = Agent(
        user_id=current_user.id,
        name=agent_data.name,
        description=agent_data.description,
        agent_type_id=agent_data.agent_type_id,
        tags=agent_data.tags
    )
    db.add(agent)
    db.flush()  # Flush to get agent.id

    # Create first version
    version = AgentVersion(
        agent_id=agent.id,
        version_number=1,
        config=agent_data.config.model_dump(),
        created_by=current_user.id
    )
    db.add(version)
    db.flush()

    # Set current version
    agent.current_version_id = version.id
    db.commit()
    db.refresh(agent)
    db.refresh(version)

    # Build response
    return _build_agent_detail_response(agent, db)


def _build_agent_response(agent: Agent) -> AgentResponse:
    """Build AgentResponse with agent_type_config"""
    agent_type_config = None
    if agent.agent_type_config:
        agent_type_config = _build_agent_type_config_compact(agent.agent_type_config)

    return AgentResponse(
        id=agent.id,
        user_id=agent.user_id,
        name=agent.name,
        description=agent.description,
        agent_type_id=agent.agent_type_id,
        agent_type_config=agent_type_config,
        tags=agent.tags,
        is_active=agent.is_active,
        is_builtin=agent.is_builtin,
        current_version_id=agent.current_version_id,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    )


@router.get("", response_model=AgentListResponse)
def list_agents(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    active_only: bool = Query(True, description="Only return active agents"),
    agent_type_id: Optional[int] = Query(None, description="Filter by agent type ID"),
    include_builtin: bool = Query(True, description="Include built-in agents"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all agents for the current user with pagination.

    Includes both user's custom agents and built-in agents (visible to all).
    """
    from sqlalchemy import or_

    query = db.query(Agent).options(
        joinedload(Agent.agent_type_config)
    )

    # Show user's agents OR built-in agents
    if include_builtin:
        query = query.filter(
            or_(
                Agent.user_id == current_user.id,
                Agent.is_builtin == True
            )
        )
    else:
        query = query.filter(Agent.user_id == current_user.id)

    if active_only:
        query = query.filter(Agent.is_active == True)

    if agent_type_id is not None:
        query = query.filter(Agent.agent_type_id == agent_type_id)

    total = query.count()
    # Order built-in agents first, then by updated_at
    agents = query.order_by(Agent.is_builtin.desc(), Agent.updated_at.desc()).offset(skip).limit(limit).all()

    return AgentListResponse(
        agents=[_build_agent_response(agent) for agent in agents],
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/{agent_id}", response_model=AgentDetailResponse)
def get_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get agent details including current version.

    Users can view their own agents and built-in agents.
    """
    from sqlalchemy import or_

    agent = db.query(Agent).options(
        joinedload(Agent.agent_type_config)
    ).filter(
        Agent.id == agent_id,
        or_(
            Agent.user_id == current_user.id,
            Agent.is_builtin == True
        )
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    return _build_agent_detail_response(agent, db)


@router.put("/{agent_id}", response_model=AgentDetailResponse)
def update_agent(
    agent_id: int,
    agent_data: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update agent details.

    If config is provided, creates a new version.
    Built-in agents cannot be modified.
    """
    # First find the agent
    agent = db.query(Agent).filter(Agent.id == agent_id).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Prevent modifying built-in agents
    if agent.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Built-in agents cannot be modified. Clone to create your own copy."
        )

    # Check ownership
    if agent.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Update basic fields
    if agent_data.name is not None:
        agent.name = agent_data.name
    if agent_data.description is not None:
        agent.description = agent_data.description
    if agent_data.agent_type_id is not None:
        # Validate new agent_type_id
        new_agent_type = db.query(AgentTypeConfig).filter(
            AgentTypeConfig.id == agent_data.agent_type_id
        ).first()
        if not new_agent_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent type with ID {agent_data.agent_type_id} not found"
            )
        # Check access
        if not new_agent_type.is_builtin and new_agent_type.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this agent type"
            )
        agent.agent_type_id = agent_data.agent_type_id
    if agent_data.tags is not None:
        agent.tags = agent_data.tags

    # Create new version if config provided
    if agent_data.config is not None:
        # Get current max version number
        max_version = db.query(AgentVersion.version_number).filter(
            AgentVersion.agent_id == agent_id
        ).order_by(AgentVersion.version_number.desc()).first()

        next_version_number = (max_version[0] + 1) if max_version else 1

        # Create new version
        new_version = AgentVersion(
            agent_id=agent.id,
            version_number=next_version_number,
            config=agent_data.config.model_dump(),
            created_by=current_user.id
        )
        db.add(new_version)
        db.flush()

        # Update current version
        agent.current_version_id = new_version.id

    db.commit()
    db.refresh(agent)

    return _build_agent_detail_response(agent, db)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: int,
    hard_delete: bool = Query(False, description="Permanently delete agent"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an agent (soft delete by default).

    Set hard_delete=true to permanently delete.
    Built-in agents cannot be deleted.
    """
    # First find the agent
    agent = db.query(Agent).filter(Agent.id == agent_id).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Prevent deleting built-in agents
    if agent.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Built-in agents cannot be deleted"
        )

    # Check ownership
    if agent.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    if hard_delete:
        db.delete(agent)
    else:
        agent.is_active = False

    db.commit()
    return None


@router.post("/{agent_id}/clone", response_model=AgentDetailResponse, status_code=status.HTTP_201_CREATED)
def clone_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clone an agent to create an editable copy.

    Works for both user-owned agents and built-in agents.
    The clone will be owned by the current user and fully editable.
    """
    from sqlalchemy import or_

    # Find the agent (allow cloning both user-owned and built-in agents)
    agent = db.query(Agent).options(
        joinedload(Agent.agent_type_config)
    ).filter(
        Agent.id == agent_id,
        or_(
            Agent.user_id == current_user.id,
            Agent.is_builtin == True
        )
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Create clone with new name
    clone_name = f"{agent.name} (Copy)"
    # Check if name already exists and add number if needed
    existing_count = db.query(Agent).filter(
        Agent.user_id == current_user.id,
        Agent.name.like(f"{agent.name} (Copy)%")
    ).count()
    if existing_count > 0:
        clone_name = f"{agent.name} (Copy {existing_count + 1})"

    # Create the cloned agent
    cloned_agent = Agent(
        user_id=current_user.id,
        name=clone_name,
        description=agent.description,
        agent_type_id=agent.agent_type_id,
        tags=agent.tags.copy() if agent.tags else [],
        is_active=True,
        is_builtin=False  # Clone is never built-in
    )
    db.add(cloned_agent)
    db.flush()

    # Clone the current version if it exists
    if agent.current_version_id:
        original_version = db.query(AgentVersion).filter(
            AgentVersion.id == agent.current_version_id
        ).first()

        if original_version:
            cloned_version = AgentVersion(
                agent_id=cloned_agent.id,
                version_number=1,
                config=original_version.config.copy() if original_version.config else {},
                created_by=current_user.id
            )
            db.add(cloned_version)
            db.flush()
            cloned_agent.current_version_id = cloned_version.id

    db.commit()
    db.refresh(cloned_agent)

    return _build_agent_detail_response(cloned_agent, db)


@router.get("/{agent_id}/versions", response_model=List[AgentVersionResponse])
def list_agent_versions(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get version history for an agent.
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

    versions = db.query(AgentVersion).filter(
        AgentVersion.agent_id == agent_id
    ).order_by(AgentVersion.version_number.desc()).all()

    return [AgentVersionResponse.model_validate(version) for version in versions]


@router.post("/{agent_id}/rollback", response_model=AgentDetailResponse)
def rollback_agent(
    agent_id: int,
    rollback_data: AgentRollbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rollback agent to a previous version.

    Updates the current_version_id to point to the specified version.
    """
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Verify version exists and belongs to this agent
    version = db.query(AgentVersion).filter(
        AgentVersion.id == rollback_data.version_id,
        AgentVersion.agent_id == agent_id
    ).first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found for this agent"
        )

    # Update current version
    agent.current_version_id = version.id
    db.commit()
    db.refresh(agent)

    return _build_agent_detail_response(agent, db)


# Agent-Tool Association Endpoints

@router.post("/{agent_id}/tools", response_model=List[AgentToolResponse])
def assign_tools_to_agent(
    agent_id: int,
    assignment: AgentToolAssignment,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Assign tools to an agent.

    Replaces existing tool assignments with new ones.
    """
    # Check if agent exists and user owns it
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Verify all tools exist and user has access
    for tool_id in assignment.tool_ids:
        tool = db.query(Tool).filter(Tool.id == tool_id).first()
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool with ID {tool_id} not found"
            )

        # Check access
        if tool.tool_type == ToolType.CUSTOM and tool.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have access to tool '{tool.name}'"
            )

    # Remove existing assignments
    db.execute(
        sql_delete(agent_tools).where(agent_tools.c.agent_id == agent_id)
    )

    # Add new assignments
    responses = []
    for tool_id in assignment.tool_ids:
        # Get tool-specific config if provided
        config = assignment.config.get(tool_id, {}) if assignment.config else {}

        # Insert new assignment
        stmt = insert(agent_tools).values(
            agent_id=agent_id,
            tool_id=tool_id,
            config=config
        )
        result = db.execute(stmt)
        db.flush()

        # Get tool for response
        tool = db.query(Tool).filter(Tool.id == tool_id).first()

        # Get the assignment to get created_at
        assignment_row = db.execute(
            agent_tools.select().where(
                (agent_tools.c.agent_id == agent_id) & (agent_tools.c.tool_id == tool_id)
            )
        ).first()

        responses.append(AgentToolResponse(
            tool_id=tool.id,
            tool_name=tool.name,
            tool_category=tool.category,
            config=config,
            assigned_at=assignment_row.created_at
        ))

    db.commit()

    return responses


@router.get("/{agent_id}/tools", response_model=List[AgentToolResponse])
def get_agent_tools(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all tools assigned to an agent.
    """
    # Check if agent exists and user owns it
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Get agent-tool assignments
    assignments = db.execute(
        agent_tools.select().where(agent_tools.c.agent_id == agent_id)
    ).all()

    # Build response
    responses = []
    for assignment in assignments:
        tool = db.query(Tool).filter(Tool.id == assignment.tool_id).first()
        if tool:
            responses.append(AgentToolResponse(
                tool_id=tool.id,
                tool_name=tool.name,
                tool_category=tool.category,
                config=assignment.config,
                assigned_at=assignment.created_at
            ))

    return responses


@router.delete("/{agent_id}/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_tool_from_agent(
    agent_id: int,
    tool_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a tool from an agent.
    """
    # Check if agent exists and user owns it
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Remove the assignment
    result = db.execute(
        sql_delete(agent_tools).where(
            (agent_tools.c.agent_id == agent_id) & (agent_tools.c.tool_id == tool_id)
        )
    )

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool assignment not found"
        )

    db.commit()

    return None


# ============================================================================
# Agent Execution Endpoint
# ============================================================================

@router.post("/{agent_id}/invoke", response_model=InvokeResponse)
def invoke_agent(
    agent_id: int,
    request: InvokeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Invoke an agent with a message.

    Executes the agent with the provided input message and returns
    the agent's response along with execution metadata.

    - **message**: The user message to send to the agent
    - **session_id**: Optional session ID to continue a conversation
    - **config_override**: Optional configuration overrides for this invocation
    - **timeout_seconds**: Optional timeout in seconds (1-3600)

    Returns:
        InvokeResponse with the agent's output or error details
    """
    try:
        # Create executor service
        executor = AgentExecutorService(db=db, user_id=current_user.id)

        # Invoke the agent
        result = executor.invoke(
            agent_id=agent_id,
            input_message=request.message,
            session_id=request.session_id,
            config_override=request.config_override,
            timeout_seconds=request.timeout_seconds
        )

        # Build response
        return InvokeResponse(
            success=result.success,
            output=result.output,
            error=result.error,
            error_type=result.error_type,
            session_id=result.session_id,
            token_usage=TokenUsage(
                input_tokens=result.tokens_input,
                output_tokens=result.tokens_output,
                total_tokens=result.tokens_input + result.tokens_output
            ),
            latency_ms=result.total_latency_ms,
            steps=result.steps
        )

    except AgentNotFoundError as e:
        logger.warning(f"Agent not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except AgentConfigurationError as e:
        logger.error(f"Agent configuration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except AgentExecutionTimeoutError as e:
        logger.warning(f"Agent execution timeout: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e)
        )

    except Exception as e:
        logger.exception(f"Agent execution failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}"
        )


# ============================================================================
# Agent-MCP Server Association Endpoints
# ============================================================================

@router.post("/{agent_id}/mcp-servers", response_model=List[MCPServerConfigResponse])
def assign_mcp_servers_to_agent(
    agent_id: int,
    assignment: AgentMCPServerAssignment,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Assign MCP servers to an agent.

    Replaces existing MCP server assignments with new ones.
    """
    # Check if agent exists and user owns it
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Verify all MCP servers exist and user has access
    servers = []
    for server_id in assignment.mcp_server_ids:
        server = db.query(MCPServerConfig).filter(
            MCPServerConfig.id == server_id,
            MCPServerConfig.user_id == current_user.id
        ).first()
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP server with ID {server_id} not found"
            )
        servers.append(server)

    # Remove existing assignments
    db.execute(
        sql_delete(agent_mcp_servers).where(agent_mcp_servers.c.agent_id == agent_id)
    )

    # Add new assignments
    for server in servers:
        stmt = insert(agent_mcp_servers).values(
            agent_id=agent_id,
            mcp_server_id=server.id
        )
        db.execute(stmt)

    db.commit()

    # Return the assigned servers
    return [_server_to_response(s) for s in servers]


@router.get("/{agent_id}/mcp-servers", response_model=List[MCPServerConfigResponse])
def get_agent_mcp_servers(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all MCP servers assigned to an agent.
    """
    # Check if agent exists and user owns it
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Get assigned MCP servers through the relationship
    return [_server_to_response(s) for s in agent.mcp_servers]


@router.delete("/{agent_id}/mcp-servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_mcp_server_from_agent(
    agent_id: int,
    server_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove an MCP server from an agent.
    """
    # Check if agent exists and user owns it
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Remove the assignment
    result = db.execute(
        sql_delete(agent_mcp_servers).where(
            (agent_mcp_servers.c.agent_id == agent_id) &
            (agent_mcp_servers.c.mcp_server_id == server_id)
        )
    )

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server assignment not found"
        )

    db.commit()

    return None


def _server_to_response(server: MCPServerConfig) -> MCPServerConfigResponse:
    """Convert MCPServerConfig model to response schema"""
    cached_tools_count = 0
    if server.cached_tools:
        cached_tools_count = len(server.cached_tools)

    return MCPServerConfigResponse(
        id=server.id,
        user_id=server.user_id,
        name=server.name,
        description=server.description,
        transport_type=server.transport_type,
        stdio_config=server.stdio_config,
        http_config=server.http_config,
        config=server.config,
        has_env_vars=bool(server.encrypted_env_vars),
        cached_tools_count=cached_tools_count,
        tools_last_discovered_at=server.tools_last_discovered_at,
        is_active=server.is_active,
        last_connected_at=server.last_connected_at,
        last_error=server.last_error,
        created_at=server.created_at,
        updated_at=server.updated_at,
    )


# ============= POWER AGENT ENDPOINTS =============

class PowerAgentCreateRequest(BaseModel):
    """Request to create a Power Agent"""
    provider_id: Optional[int] = None
    custom_name: Optional[str] = None


class PowerAgentResponse(BaseModel):
    """Response for Power Agent creation"""
    success: bool
    message: str
    agent_id: Optional[int] = None
    tool_count: Optional[int] = None


class DemoScenario(BaseModel):
    """Demo scenario schema"""
    name: str
    description: str
    example_prompt: str
    tags: List[str]


class PowerAgentConfigResponse(BaseModel):
    """Response with Power Agent configuration"""
    name: str
    description: str
    system_prompt: str
    demo_scenarios: List[DemoScenario]


@router.post("/power-agent/create", response_model=PowerAgentResponse)
def create_power_agent(
    request: PowerAgentCreateRequest = PowerAgentCreateRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Power Agent for the current user.

    The Power Agent comes pre-configured with all available tools:
    - Web Search & Fetch for research
    - File management (read, write, edit, list, search)
    - Task Manager for project planning
    - Scratchpad for working memory
    - Python Code Execution
    - HTTP Request for APIs

    If a Power Agent already exists for the user, returns the existing agent ID.
    """
    from ...utils.power_agent import create_power_agent_for_user

    result = create_power_agent_for_user(
        db=db,
        user_id=current_user.id,
        provider_id=request.provider_id,
        custom_name=request.custom_name
    )

    if result["success"]:
        return PowerAgentResponse(
            success=True,
            message="Power Agent created successfully",
            agent_id=result["agent_id"],
            tool_count=result["tool_count"]
        )
    else:
        # Check if it's because agent already exists
        if "already exists" in result.get("error", ""):
            return PowerAgentResponse(
                success=True,
                message="Power Agent already exists",
                agent_id=result.get("agent_id"),
                tool_count=None
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to create Power Agent")
        )


@router.get("/power-agent/config", response_model=PowerAgentConfigResponse)
def get_power_agent_config(
    current_user: User = Depends(get_current_user)
):
    """
    Get the Power Agent configuration and demo scenarios.

    Returns the system prompt and demo scenarios that can be used
    as starting points for using the Power Agent.
    """
    from ...utils.power_agent import get_power_agent_config, DEMO_SCENARIOS

    config = get_power_agent_config()

    return PowerAgentConfigResponse(
        name=config["config"]["name"],
        description=config["config"]["description"],
        system_prompt=config["system_prompt"],
        demo_scenarios=[DemoScenario(**s) for s in DEMO_SCENARIOS]
    )
