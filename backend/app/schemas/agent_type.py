"""
Pydantic schemas for Agent Type Configuration.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Re-export enum for schema use
class ExecutionStrategy(str, Enum):
    """Execution strategy enum - maps to agent executor methods

    Note: Enum names are lowercase to match PostgreSQL enum labels.
    """
    react = "react"
    plan_and_execute = "plan_and_execute"
    conversational = "conversational"
    codeact = "codeact"


class StrategyType(str, Enum):
    """Strategy type enum - distinguishes builtin strategies from custom code

    Note: Enum names are lowercase to match PostgreSQL enum labels.
    """
    builtin = "builtin"
    custom_code = "custom_code"


# ============================================================================
# Sub-schemas for JSON fields
# ============================================================================

class DefaultLLMConfig(BaseModel):
    """Default LLM configuration for agent type"""
    provider: Optional[str] = Field(default=None, description="Default LLM provider")
    model: Optional[str] = Field(default=None, description="Default model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=100000)

    model_config = ConfigDict(from_attributes=True)


class DefaultMemoryConfig(BaseModel):
    """Default memory configuration for agent type"""
    type: str = Field(default="buffer", description="Memory type (buffer, summary, vector)")
    context_window: int = Field(default=10, ge=1, le=100)
    retrieval_strategy: Optional[str] = Field(default="similarity")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Helper schemas for relationships
# ============================================================================

class RecommendedToolInfo(BaseModel):
    """Minimal tool info for agent type response"""
    id: int
    name: str
    category: str

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Request Schemas
# ============================================================================

class AgentTypeConfigBase(BaseModel):
    """Base schema for agent type configuration"""
    name: str = Field(..., min_length=1, max_length=255, description="Agent type name")
    description: Optional[str] = Field(default=None, description="Agent type description")
    icon: Optional[str] = Field(default=None, max_length=50, description="Lucide icon name")
    execution_strategy: ExecutionStrategy = Field(default=ExecutionStrategy.react)
    system_prompt_template: Optional[str] = Field(default=None, description="Default system prompt template")
    default_llm_config: Dict[str, Any] = Field(default_factory=dict)
    default_memory_config: Dict[str, Any] = Field(default_factory=dict)
    max_iterations: int = Field(default=10, ge=1, le=50)

    # Custom strategy fields
    strategy_type: StrategyType = Field(
        default=StrategyType.builtin,
        description="Type of execution strategy: builtin or custom_code"
    )
    custom_strategy_code: Optional[str] = Field(
        default=None,
        description="Python code for custom execution strategy"
    )
    code_template_version: int = Field(
        default=1,
        ge=1,
        description="Version of the code template format"
    )


class AgentTypeConfigCreate(AgentTypeConfigBase):
    """Schema for creating a new agent type"""
    recommended_tool_ids: List[int] = Field(default=[], description="IDs of recommended tools")

    model_config = ConfigDict(from_attributes=True)


class AgentTypeConfigUpdate(BaseModel):
    """Schema for updating an agent type (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    execution_strategy: Optional[ExecutionStrategy] = None
    system_prompt_template: Optional[str] = None
    default_llm_config: Optional[Dict[str, Any]] = None
    default_memory_config: Optional[Dict[str, Any]] = None
    max_iterations: Optional[int] = Field(None, ge=1, le=50)
    recommended_tool_ids: Optional[List[int]] = None
    is_active: Optional[bool] = None

    # Custom strategy fields
    strategy_type: Optional[StrategyType] = None
    custom_strategy_code: Optional[str] = None
    code_template_version: Optional[int] = Field(None, ge=1)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas
# ============================================================================

class AgentTypeConfigResponse(AgentTypeConfigBase):
    """Schema for agent type configuration response"""
    id: int
    user_id: Optional[int]
    is_builtin: bool
    is_active: bool
    recommended_tools: List[RecommendedToolInfo] = []
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class AgentTypeConfigListResponse(BaseModel):
    """Schema for paginated agent type list"""
    agent_types: List[AgentTypeConfigResponse]
    total: int = Field(..., description="Total number of agent types")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Compact response for embedding in other responses
# ============================================================================

class AgentTypeConfigCompact(BaseModel):
    """Compact agent type info for embedding in agent responses"""
    id: int
    name: str
    execution_strategy: ExecutionStrategy
    strategy_type: StrategyType
    icon: Optional[str]
    is_builtin: bool

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Strategy Validation Schemas
# ============================================================================

class StrategyValidateRequest(BaseModel):
    """Request schema for validating custom strategy code"""
    code: str = Field(..., min_length=1, description="Python code to validate")

    model_config = ConfigDict(from_attributes=True)


class StrategyValidateResponse(BaseModel):
    """Response schema for strategy validation"""
    is_valid: bool
    error: Optional[str] = None
    warnings: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class StrategyTestRequest(BaseModel):
    """Request schema for testing custom strategy code"""
    code: str = Field(..., min_length=1, description="Python code to test")
    input_message: str = Field(default="Hello, world!", description="Test input message")
    config: Dict[str, Any] = Field(default_factory=dict, description="Test config")

    model_config = ConfigDict(from_attributes=True)


class StrategyTestResponse(BaseModel):
    """Response schema for strategy test execution"""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    execution_time_ms: int = 0
    steps: List[Dict[str, Any]] = []
    tokens_input: int = 0
    tokens_output: int = 0

    model_config = ConfigDict(from_attributes=True)


class StrategyTemplateInfo(BaseModel):
    """Information about a strategy template"""
    name: str
    description: str

    model_config = ConfigDict(from_attributes=True)


class StrategyTemplatesResponse(BaseModel):
    """Response schema for listing strategy templates"""
    templates: List[StrategyTemplateInfo]

    model_config = ConfigDict(from_attributes=True)


class StrategyTemplateResponse(BaseModel):
    """Response schema for getting a strategy template"""
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)
