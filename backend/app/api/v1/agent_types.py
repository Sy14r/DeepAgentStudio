"""
Agent Type Configuration API endpoints

Provides CRUD operations for managing agent type configurations with:
- Builtin types (read-only, visible to all)
- Custom user-defined types (full CRUD for owner)
- Recommended tools association
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from ...database import get_db
from ...models.user import User
from ...models.agent_type import AgentTypeConfig, ExecutionStrategy, StrategyType
from ...models.tool import Tool, ToolType
from ...schemas.agent_type import (
    AgentTypeConfigCreate,
    AgentTypeConfigUpdate,
    AgentTypeConfigResponse,
    AgentTypeConfigListResponse,
    RecommendedToolInfo,
    ExecutionStrategy as ExecutionStrategySchema,
    StrategyType as StrategyTypeSchema,
    StrategyValidateRequest,
    StrategyValidateResponse,
    StrategyTestRequest,
    StrategyTestResponse,
    StrategyTemplatesResponse,
    StrategyTemplateResponse,
    StrategyTemplateInfo,
)
from ...services.strategy_executor import (
    CustomStrategyExecutor,
    get_strategy_template,
    list_strategy_templates,
)
from ..deps import get_current_user

router = APIRouter()


def _build_response(agent_type: AgentTypeConfig) -> AgentTypeConfigResponse:
    """Helper to build response with recommended tools"""
    recommended_tools = [
        RecommendedToolInfo(
            id=t.id,
            name=t.name,
            category=t.category.value
        )
        for t in agent_type.recommended_tools
    ]
    return AgentTypeConfigResponse(
        id=agent_type.id,
        user_id=agent_type.user_id,
        name=agent_type.name,
        description=agent_type.description,
        icon=agent_type.icon,
        execution_strategy=agent_type.execution_strategy,
        system_prompt_template=agent_type.system_prompt_template,
        default_llm_config=agent_type.default_llm_config or {},
        default_memory_config=agent_type.default_memory_config or {},
        max_iterations=agent_type.max_iterations,
        strategy_type=agent_type.strategy_type,
        custom_strategy_code=agent_type.custom_strategy_code,
        code_template_version=agent_type.code_template_version,
        is_builtin=agent_type.is_builtin,
        is_active=agent_type.is_active,
        recommended_tools=recommended_tools,
        created_at=agent_type.created_at,
        updated_at=agent_type.updated_at,
    )


@router.get("", response_model=AgentTypeConfigListResponse)
def list_agent_types(
    execution_strategy: Optional[ExecutionStrategySchema] = Query(None, description="Filter by execution strategy"),
    is_active: bool = Query(True, description="Filter by active status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all agent types (builtin + user's custom).

    Returns builtin types visible to all users, plus custom types owned by the current user.
    """
    query = db.query(AgentTypeConfig).options(
        joinedload(AgentTypeConfig.recommended_tools)
    )

    # Filter by execution strategy
    if execution_strategy:
        query = query.filter(AgentTypeConfig.execution_strategy == execution_strategy.value)

    # Filter by active status
    query = query.filter(AgentTypeConfig.is_active == is_active)

    # Show builtin types and user's custom types
    query = query.filter(
        (AgentTypeConfig.is_builtin == True) | (AgentTypeConfig.user_id == current_user.id)
    )

    total = query.count()
    agent_types = query.order_by(
        AgentTypeConfig.is_builtin.desc(),
        AgentTypeConfig.name
    ).offset(skip).limit(limit).all()

    return AgentTypeConfigListResponse(
        agent_types=[_build_response(at) for at in agent_types],
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit
    )


@router.post("", response_model=AgentTypeConfigResponse, status_code=status.HTTP_201_CREATED)
def create_agent_type(
    data: AgentTypeConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new custom agent type.

    Custom agent types allow users to define their own configurations for agent behavior.
    """
    # Check for duplicate name (within user's types + builtins)
    existing = db.query(AgentTypeConfig).filter(
        AgentTypeConfig.name == data.name,
        (AgentTypeConfig.is_builtin == True) | (AgentTypeConfig.user_id == current_user.id)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent type '{data.name}' already exists"
        )

    # Validate and fetch recommended tools
    recommended_tools = []
    for tool_id in data.recommended_tool_ids:
        tool = db.query(Tool).filter(Tool.id == tool_id).first()
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool {tool_id} not found"
            )
        # Check access - builtin tools are public, custom tools must be owned
        if tool.tool_type == ToolType.CUSTOM and tool.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No access to tool {tool_id}"
            )
        recommended_tools.append(tool)

    # Validate custom strategy code if provided
    if data.strategy_type == StrategyTypeSchema.custom_code:
        if not data.custom_strategy_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="custom_strategy_code is required when strategy_type is 'custom_code'"
            )
        executor = CustomStrategyExecutor()
        validation = executor.validate_code(data.custom_strategy_code)
        if not validation.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid strategy code: {validation.error}"
            )

    # Create agent type
    agent_type = AgentTypeConfig(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        icon=data.icon,
        execution_strategy=data.execution_strategy,
        system_prompt_template=data.system_prompt_template,
        default_llm_config=data.default_llm_config,
        default_memory_config=data.default_memory_config,
        max_iterations=data.max_iterations,
        strategy_type=data.strategy_type,
        custom_strategy_code=data.custom_strategy_code,
        code_template_version=data.code_template_version,
        is_builtin=False,
        is_active=True
    )
    agent_type.recommended_tools = recommended_tools

    db.add(agent_type)
    db.commit()
    db.refresh(agent_type)

    return _build_response(agent_type)


@router.get("/{agent_type_id}", response_model=AgentTypeConfigResponse)
def get_agent_type(
    agent_type_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get agent type by ID.

    Users can access builtin types and their own custom types.
    """
    agent_type = db.query(AgentTypeConfig).options(
        joinedload(AgentTypeConfig.recommended_tools)
    ).filter(AgentTypeConfig.id == agent_type_id).first()

    if not agent_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent type not found"
        )

    # Check access - builtin types are public, custom types must be owned
    if not agent_type.is_builtin and agent_type.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this agent type"
        )

    return _build_response(agent_type)


@router.put("/{agent_type_id}", response_model=AgentTypeConfigResponse)
def update_agent_type(
    agent_type_id: int,
    data: AgentTypeConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an agent type.

    Builtin agent types cannot be modified. Only the owner can modify custom types.
    """
    agent_type = db.query(AgentTypeConfig).options(
        joinedload(AgentTypeConfig.recommended_tools)
    ).filter(AgentTypeConfig.id == agent_type_id).first()

    if not agent_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent type not found"
        )

    # Builtin protection
    if agent_type.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Builtin agent types cannot be modified. Clone it to create a custom version."
        )

    # Ownership check
    if agent_type.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this agent type"
        )

    # Check for duplicate name if name is being changed
    if data.name is not None and data.name != agent_type.name:
        existing = db.query(AgentTypeConfig).filter(
            AgentTypeConfig.name == data.name,
            AgentTypeConfig.id != agent_type_id,
            (AgentTypeConfig.is_builtin == True) | (AgentTypeConfig.user_id == current_user.id)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent type '{data.name}' already exists"
            )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    # Handle recommended_tool_ids separately
    if "recommended_tool_ids" in update_data:
        tool_ids = update_data.pop("recommended_tool_ids")
        tools = []
        for tool_id in tool_ids:
            tool = db.query(Tool).filter(Tool.id == tool_id).first()
            if tool:
                # Check access
                if tool.tool_type == ToolType.CUSTOM and tool.user_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"No access to tool {tool_id}"
                    )
                tools.append(tool)
        agent_type.recommended_tools = tools

    for field, value in update_data.items():
        setattr(agent_type, field, value)

    db.commit()
    db.refresh(agent_type)

    return _build_response(agent_type)


@router.delete("/{agent_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent_type(
    agent_type_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an agent type.

    Builtin agent types cannot be deleted.
    Cannot delete if agents are using this type.
    """
    agent_type = db.query(AgentTypeConfig).filter(
        AgentTypeConfig.id == agent_type_id
    ).first()

    if not agent_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent type not found"
        )

    # Builtin protection
    if agent_type.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Builtin agent types cannot be deleted"
        )

    # Ownership check
    if agent_type.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this agent type"
        )

    # Check if any agents are using this type
    if agent_type.agents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete: {len(agent_type.agents)} agent(s) are using this type. Reassign them first."
        )

    db.delete(agent_type)
    db.commit()

    return None


@router.post("/{agent_type_id}/clone", response_model=AgentTypeConfigResponse, status_code=status.HTTP_201_CREATED)
def clone_agent_type(
    agent_type_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clone an agent type to create a custom editable copy.

    This is useful for creating customized versions of builtin types.
    """
    source = db.query(AgentTypeConfig).options(
        joinedload(AgentTypeConfig.recommended_tools)
    ).filter(AgentTypeConfig.id == agent_type_id).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent type not found"
        )

    # Check access
    if not source.is_builtin and source.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this agent type"
        )

    # Generate unique name
    base_name = f"{source.name} (Copy)"
    name = base_name
    counter = 1
    while db.query(AgentTypeConfig).filter(
        AgentTypeConfig.name == name,
        (AgentTypeConfig.is_builtin == True) | (AgentTypeConfig.user_id == current_user.id)
    ).first():
        counter += 1
        name = f"{base_name} {counter}"

    # Create clone
    clone = AgentTypeConfig(
        user_id=current_user.id,
        name=name,
        description=source.description,
        icon=source.icon,
        execution_strategy=source.execution_strategy,
        system_prompt_template=source.system_prompt_template,
        default_llm_config=source.default_llm_config.copy() if source.default_llm_config else {},
        default_memory_config=source.default_memory_config.copy() if source.default_memory_config else {},
        max_iterations=source.max_iterations,
        strategy_type=source.strategy_type,
        custom_strategy_code=source.custom_strategy_code,
        code_template_version=source.code_template_version,
        is_builtin=False,
        is_active=True
    )

    # Copy recommended tools (only accessible ones)
    accessible_tools = []
    for tool in source.recommended_tools:
        if tool.tool_type == ToolType.BUILTIN or tool.user_id == current_user.id:
            accessible_tools.append(tool)
    clone.recommended_tools = accessible_tools

    db.add(clone)
    db.commit()
    db.refresh(clone)

    return _build_response(clone)


# ============================================================================
# Strategy Code Validation and Testing Endpoints
# ============================================================================

@router.post("/strategies/validate", response_model=StrategyValidateResponse)
def validate_strategy_code(
    data: StrategyValidateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Validate custom strategy code.

    Checks:
    - Valid Python syntax
    - execute() function exists with correct signature
    - No dangerous patterns (exec, eval, open, etc.)
    - Only allowed imports
    """
    executor = CustomStrategyExecutor()
    result = executor.validate_code(data.code)

    return StrategyValidateResponse(
        is_valid=result.is_valid,
        error=result.error,
        warnings=result.warnings or []
    )


@router.get("/strategies/templates", response_model=StrategyTemplatesResponse)
def get_strategy_templates(
    current_user: User = Depends(get_current_user),
):
    """
    List available strategy code templates.

    Templates provide starting points for common patterns:
    - simple_chat: Basic conversational agent
    - react_custom: Custom ReAct-style with tools
    - chain_of_thought: Chain-of-thought prompting
    - tool_selector: LLM-guided tool selection
    """
    templates = list_strategy_templates()
    return StrategyTemplatesResponse(
        templates=[StrategyTemplateInfo(**t) for t in templates]
    )


@router.get("/strategies/templates/{template_name}", response_model=StrategyTemplateResponse)
def get_strategy_template_by_name(
    template_name: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific strategy template by name.
    """
    code = get_strategy_template(template_name)
    if code is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found"
        )

    return StrategyTemplateResponse(name=template_name, code=code)
