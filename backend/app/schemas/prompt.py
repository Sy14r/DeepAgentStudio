"""
Pydantic schemas for Prompt models
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# Enums (matching model enums)

class MessageType(str, Enum):
    """Message type for prompts"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class PromptUseCase(str, Enum):
    """Prompt use case categories"""
    RESEARCH = "research"
    CODING = "coding"
    ANALYSIS = "analysis"
    WRITING = "writing"
    CONVERSATION = "conversation"
    PLANNING = "planning"
    OTHER = "other"


# Base schemas

class PromptBase(BaseModel):
    """Base prompt schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Prompt name")
    description: Optional[str] = Field(None, description="Prompt description")
    use_case: PromptUseCase = Field(default=PromptUseCase.OTHER, description="Prompt use case category")
    tags: List[str] = Field(default=[], description="Tags for categorization")

    @field_validator('tags', mode='before')
    @classmethod
    def clean_tags(cls, v):
        """Clean and validate tags"""
        if v is None:
            return []
        return [tag.strip() for tag in v if tag and tag.strip()]


class PromptVersionConfig(BaseModel):
    """Schema for prompt version configuration"""
    template: str = Field(..., min_length=1, description="The prompt template with {variable} placeholders")
    message_type: MessageType = Field(default=MessageType.USER, description="Message type (system/user/assistant)")
    is_active: bool = Field(default=True, description="Whether this version is active for A/B testing")

    @field_validator('template')
    @classmethod
    def validate_template(cls, v):
        """Validate template is not empty"""
        if not v or not v.strip():
            raise ValueError("Template cannot be empty")
        return v.strip()


# Request schemas

class PromptCreate(PromptBase):
    """Schema for creating a new prompt"""
    version: PromptVersionConfig = Field(..., description="Initial version configuration")


class PromptUpdate(BaseModel):
    """Schema for updating prompt metadata"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    use_case: Optional[PromptUseCase] = None
    tags: Optional[List[str]] = None

    @field_validator('tags', mode='before')
    @classmethod
    def clean_tags(cls, v):
        """Clean and validate tags"""
        if v is None:
            return None
        return [tag.strip() for tag in v if tag and tag.strip()]


class PromptVersionCreate(BaseModel):
    """Schema for creating a new prompt version"""
    template: str = Field(..., min_length=1)
    message_type: MessageType = Field(default=MessageType.USER)
    is_active: bool = Field(default=True)

    @field_validator('template')
    @classmethod
    def validate_template(cls, v):
        """Validate template is not empty"""
        if not v or not v.strip():
            raise ValueError("Template cannot be empty")
        return v.strip()


class PromptVersionUpdate(BaseModel):
    """Schema for updating a prompt version"""
    is_active: Optional[bool] = None


# Response schemas

class PromptVersionResponse(BaseModel):
    """Schema for prompt version response"""
    id: int
    prompt_id: int
    version_number: int
    template: str
    variables: List[str]
    message_type: MessageType
    is_active: bool
    usage_count: int
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class PromptResponse(PromptBase):
    """Schema for basic prompt response"""
    id: int
    user_id: int
    is_active: bool
    current_version_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PromptDetailResponse(PromptResponse):
    """Schema for detailed prompt response with current version"""
    current_version: Optional[PromptVersionResponse] = None


class PromptListResponse(BaseModel):
    """Schema for paginated prompt list"""
    prompts: List[PromptResponse]
    total: int
    page: int
    page_size: int

    class Config:
        from_attributes = True


class PromptRollbackRequest(BaseModel):
    """Schema for rolling back to a specific version"""
    version_id: int = Field(..., description="The version ID to rollback to")


class PromptPreviewRequest(BaseModel):
    """Schema for previewing a prompt with sample data"""
    template: str = Field(..., description="The prompt template")
    variables: Dict[str, Any] = Field(default={}, description="Sample variable values")


class PromptPreviewResponse(BaseModel):
    """Schema for prompt preview response"""
    rendered: str = Field(..., description="The rendered prompt with variables substituted")
    variables_found: List[str] = Field(..., description="Variables found in the template")
    variables_missing: List[str] = Field(default=[], description="Required variables not provided")
