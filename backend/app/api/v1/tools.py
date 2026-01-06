"""
Tool management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Any, Dict
from pydantic import BaseModel

from ...database import get_db
from ...models.user import User
from ...models.tool import Tool, ToolType, ToolCategory
from ...schemas.tool import (
    BuiltinToolCreate,
    CustomToolCreate,
    ToolUpdate,
    ToolResponse,
    ToolListResponse,
)
from ...utils.schema_generator import (
    generate_input_schema_with_descriptions,
    validate_function_code,
    extract_function_name,
)
from ..deps import get_current_user


class SchemaGenerateRequest(BaseModel):
    """Request body for schema generation."""
    function_code: str


class SchemaGenerateResponse(BaseModel):
    """Response body for schema generation."""
    success: bool
    schema: Optional[Dict[str, Any]] = None
    function_name: Optional[str] = None
    error: Optional[str] = None

router = APIRouter()


@router.post("/generate-schema", response_model=SchemaGenerateResponse)
def generate_schema(
    request: SchemaGenerateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate input schema from Python function code.

    Parses the function signature and docstring to create a JSON schema
    compatible with LangChain tools.
    """
    # Validate the code
    is_valid, error = validate_function_code(request.function_code)
    if not is_valid:
        return SchemaGenerateResponse(
            success=False,
            error=error
        )

    # Generate schema
    schema = generate_input_schema_with_descriptions(request.function_code)
    if not schema:
        return SchemaGenerateResponse(
            success=False,
            error="Failed to generate schema from function code"
        )

    # Extract function name
    func_name = extract_function_name(request.function_code)

    return SchemaGenerateResponse(
        success=True,
        schema=schema,
        function_name=func_name
    )


@router.get("", response_model=ToolListResponse)
def list_tools(
    category: Optional[ToolCategory] = Query(None, description="Filter by category"),
    tool_type: Optional[ToolType] = Query(None, description="Filter by tool type"),
    is_active: bool = Query(True, description="Filter by active status"),
    skip: int = Query(0, ge=0, description="Number of tools to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of tools to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all tools with optional filters.

    Returns both built-in tools and user's custom tools.
    """
    query = db.query(Tool)

    # Filter by category
    if category:
        query = query.filter(Tool.category == category)

    # Filter by tool type
    if tool_type:
        query = query.filter(Tool.tool_type == tool_type)

    # Filter by active status
    query = query.filter(Tool.is_active == is_active)

    # Show built-in tools and user's custom tools
    query = query.filter(
        (Tool.tool_type == ToolType.BUILTIN) | (Tool.user_id == current_user.id)
    )

    # Get total count
    total = query.count()

    # Apply pagination
    tools = query.order_by(Tool.created_at.desc()).offset(skip).limit(limit).all()

    # Convert to response models
    tool_responses = [ToolResponse.model_validate(tool) for tool in tools]

    return ToolListResponse(
        tools=tool_responses,
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )


@router.post("/builtin", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
def create_builtin_tool(
    tool_data: BuiltinToolCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new built-in tool.

    Note: In production, this should be restricted to admin users only.
    """
    # Check if tool name already exists
    existing = db.query(Tool).filter(Tool.name == tool_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool with name '{tool_data.name}' already exists"
        )

    # Create built-in tool
    tool = Tool(
        name=tool_data.name,
        description=tool_data.description,
        category=tool_data.category,
        tags=tool_data.tags,
        tool_type=ToolType.BUILTIN,
        langchain_class=tool_data.langchain_class,
        required_config=tool_data.required_config,
        user_id=None,  # Built-in tools have no owner
        is_active=True
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)

    return ToolResponse.model_validate(tool)


@router.post("/custom", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
def create_custom_tool(
    tool_data: CustomToolCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new custom tool.

    Custom tools are owned by the user who creates them.
    """
    # Check if tool name already exists
    existing = db.query(Tool).filter(Tool.name == tool_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool with name '{tool_data.name}' already exists"
        )

    # Create custom tool
    tool = Tool(
        name=tool_data.name,
        description=tool_data.description,
        category=tool_data.category,
        tags=tool_data.tags,
        tool_type=ToolType.CUSTOM,
        user_id=current_user.id,
        function_code=tool_data.function_code,
        input_schema=tool_data.input_schema,
        output_schema=tool_data.output_schema,
        is_active=True
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)

    return ToolResponse.model_validate(tool)


@router.get("/{tool_id}", response_model=ToolResponse)
def get_tool(
    tool_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get tool details by ID.

    Users can only access built-in tools or their own custom tools.
    """
    tool = db.query(Tool).filter(Tool.id == tool_id).first()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found"
        )

    # Check access: built-in tools are public, custom tools are private
    if tool.tool_type == ToolType.CUSTOM and tool.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this tool"
        )

    return ToolResponse.model_validate(tool)


@router.put("/{tool_id}", response_model=ToolResponse)
def update_tool(
    tool_id: int,
    tool_data: ToolUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update tool details.

    Users can update both built-in tools and their own custom tools.
    """
    tool = db.query(Tool).filter(Tool.id == tool_id).first()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found"
        )

    # Check ownership for custom tools only
    if tool.tool_type == ToolType.CUSTOM and tool.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own tools"
        )

    # Update fields if provided
    update_data = tool_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tool, field, value)

    db.commit()
    db.refresh(tool)

    return ToolResponse.model_validate(tool)


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tool(
    tool_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a tool.

    Users can only delete their own custom tools.
    Built-in tools cannot be deleted via API.
    """
    tool = db.query(Tool).filter(Tool.id == tool_id).first()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found"
        )

    # Only custom tools can be deleted
    if tool.tool_type == ToolType.BUILTIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Built-in tools cannot be deleted"
        )

    # Check ownership
    if tool.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own tools"
        )

    db.delete(tool)
    db.commit()

    return None
