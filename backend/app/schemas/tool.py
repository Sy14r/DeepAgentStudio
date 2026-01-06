from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ToolType(str, Enum):
    """Tool type enumeration"""
    BUILTIN = "builtin"
    CUSTOM = "custom"


class ToolCategory(str, Enum):
    """Tool category enumeration"""
    SEARCH = "search"
    CALCULATOR = "calculator"
    FILESYSTEM = "filesystem"
    API = "api"
    DATABASE = "database"
    RETRIEVAL = "retrieval"
    PYTHON = "python"
    OTHER = "other"


# Tool schemas

class ToolBase(BaseModel):
    """Base tool schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Tool name")
    description: str = Field(..., min_length=1, description="Tool description")
    category: ToolCategory = Field(default=ToolCategory.OTHER, description="Tool category")
    tags: List[str] = Field(default=[], description="Tool tags for categorization")

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Validate tags are non-empty strings"""
        if v is None:
            return []
        return [tag.strip() for tag in v if tag and tag.strip()]


class BuiltinToolCreate(ToolBase):
    """Schema for creating a built-in tool"""
    tool_type: ToolType = Field(default=ToolType.BUILTIN, description="Tool type (builtin)")
    langchain_class: str = Field(..., description="LangChain class name")
    required_config: Dict[str, Any] = Field(default={}, description="Required configuration")

    class Config:
        from_attributes = True


class CustomToolCreate(ToolBase):
    """Schema for creating a custom tool"""
    tool_type: ToolType = Field(default=ToolType.CUSTOM, description="Tool type (custom)")
    function_code: str = Field(..., description="Python function code")
    input_schema: Dict[str, Any] = Field(..., description="Input parameter schema")
    output_schema: Optional[Dict[str, Any]] = Field(default=None, description="Output schema")

    class Config:
        from_attributes = True


class ToolUpdate(BaseModel):
    """Schema for updating a tool"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    category: Optional[ToolCategory] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    # For custom tools only
    function_code: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Validate tags are non-empty strings"""
        if v is None:
            return None
        return [tag.strip() for tag in v if tag and tag.strip()]

    class Config:
        from_attributes = True


class ToolResponse(ToolBase):
    """Schema for tool responses"""
    id: int
    tool_type: ToolType
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    # Fields for built-in tools
    langchain_class: Optional[str] = None
    required_config: Optional[Dict[str, Any]] = None

    # Fields for custom tools
    user_id: Optional[int] = None
    function_code: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ToolListResponse(BaseModel):
    """Schema for paginated tool list"""
    tools: List[ToolResponse]
    total: int
    page: int
    page_size: int

    class Config:
        from_attributes = True


# Agent-Tool Assignment schemas

class AgentToolAssignment(BaseModel):
    """Schema for assigning tools to an agent"""
    tool_ids: List[int] = Field(..., description="List of tool IDs to assign")
    config: Optional[Dict[int, Dict[str, Any]]] = Field(
        default={},
        description="Optional tool-specific configuration overrides (key: tool_id, value: config)"
    )


class AgentToolResponse(BaseModel):
    """Schema for agent-tool assignment response"""
    tool_id: int
    tool_name: str
    tool_category: ToolCategory
    config: Dict[str, Any]
    assigned_at: datetime

    class Config:
        from_attributes = True
