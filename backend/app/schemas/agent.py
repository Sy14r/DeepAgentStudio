from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any


# Configuration schemas for JSONB fields

class LLMConfig(BaseModel):
    """LLM configuration schema"""
    provider: str = Field(..., description="LLM provider (openai, anthropic, ollama, etc.)")
    provider_id: int = Field(..., description="ID of the user's LLM provider configuration")
    model: str = Field(..., description="Model name (gpt-4, claude-3-opus, etc.)")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature for response generation")
    max_tokens: int = Field(default=2000, ge=1, le=100000, description="Maximum tokens for response")
    stop_sequences: List[str] = Field(default=[], description="Stop sequences for generation")

    class Config:
        from_attributes = True


class ReflectionConfig(BaseModel):
    """Reflection configuration schema"""
    enabled: bool = Field(default=False, description="Enable reflection in agent")
    depth: int = Field(default=2, ge=1, le=10, description="Reflection depth")
    iteration_limit: int = Field(default=5, ge=1, le=20, description="Maximum reflection iterations")

    class Config:
        from_attributes = True


class MemoryConfig(BaseModel):
    """Memory configuration schema"""
    type: str = Field(default="buffer", description="Memory type (buffer, summary, vector)")
    context_window: int = Field(default=10, ge=1, le=100, description="Context window size")
    retrieval_strategy: Optional[str] = Field(default="similarity", description="Retrieval strategy for vector memory")

    class Config:
        from_attributes = True


class AgentVersionConfig(BaseModel):
    """Complete agent version configuration"""
    llm_config: LLMConfig
    reflection_config: Optional[ReflectionConfig] = Field(default_factory=lambda: ReflectionConfig())
    memory_config: Optional[MemoryConfig] = Field(default_factory=lambda: MemoryConfig())
    tool_ids: List[int] = Field(default=[], description="List of tool IDs assigned to agent")
    prompt_id: Optional[int] = Field(default=None, description="Prompt template ID")
    system_prompt: Optional[str] = Field(default=None, description="System prompt override")

    class Config:
        from_attributes = True


# AgentVersion schemas

class AgentVersionBase(BaseModel):
    """Base agent version schema"""
    config: AgentVersionConfig


class AgentVersionCreate(AgentVersionBase):
    """Schema for creating a new agent version"""
    pass


class AgentVersionResponse(BaseModel):
    """Schema for agent version responses"""
    id: int
    agent_id: int
    version_number: int
    config: Dict[str, Any]  # JSONB returned as dict
    created_at: datetime
    created_by: int

    class Config:
        from_attributes = True


# Agent schemas

class AgentBase(BaseModel):
    """Base agent schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Agent name")
    description: Optional[str] = Field(default=None, description="Agent description")
    agent_type_id: int = Field(..., description="ID of the agent type configuration")
    tags: List[str] = Field(default=[], description="Agent tags for categorization")

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Validate tags are non-empty strings"""
        if v is None:
            return []
        return [tag.strip() for tag in v if tag and tag.strip()]


class AgentCreate(AgentBase):
    """Schema for creating a new agent"""
    config: AgentVersionConfig

    class Config:
        from_attributes = True


class AgentUpdate(BaseModel):
    """Schema for updating an agent"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    agent_type_id: Optional[int] = Field(None, description="ID of the agent type configuration")
    tags: Optional[List[str]] = None
    config: Optional[AgentVersionConfig] = None  # If provided, creates new version

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Validate tags are non-empty strings"""
        if v is None:
            return None
        return [tag.strip() for tag in v if tag and tag.strip()]

    class Config:
        from_attributes = True


class AgentResponse(BaseModel):
    """Schema for agent responses"""
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    agent_type_id: int
    agent_type_config: Optional[Dict[str, Any]] = None  # AgentTypeConfigCompact as dict
    tags: List[str] = []
    is_active: bool
    current_version_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class AgentDetailResponse(AgentResponse):
    """Schema for detailed agent response with current version"""
    current_version: Optional[AgentVersionResponse] = None

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    """Schema for paginated agent list"""
    agents: List[AgentResponse]
    total: int
    page: int
    page_size: int

    class Config:
        from_attributes = True


class AgentRollbackRequest(BaseModel):
    """Schema for agent rollback request"""
    version_id: int = Field(..., description="Version ID to rollback to")
