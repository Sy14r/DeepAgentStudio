"""
Pydantic schemas for LLM Provider Configuration.

Security Note: API keys are NEVER included in response schemas.
To update an API key, use a separate endpoint that doesn't return the key.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


# Re-export enum for schema use
class LLMProviderType(str, Enum):
    """LLM provider types"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"
    OPENAI_COMPATIBLE = "openai_compatible"


# ============================================================================
# Request Schemas
# ============================================================================

class LLMProviderConfigBase(BaseModel):
    """Base schema for LLM provider configuration"""
    provider_type: LLMProviderType = Field(..., description="LLM provider type")
    name: str = Field(..., max_length=255, description="User-defined name for this configuration")
    description: Optional[str] = Field(None, description="Optional description")
    config: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific configuration")


class LLMProviderConfigCreate(LLMProviderConfigBase):
    """
    Schema for creating a new LLM provider configuration.

    The API key is provided in plaintext and will be encrypted before storage.
    """
    api_key: Optional[str] = Field(None, description="API key (will be encrypted). Optional for local/custom endpoints.")


class LLMProviderConfigUpdate(BaseModel):
    """
    Schema for updating LLM provider configuration.

    All fields are optional. To update the API key, use the separate
    update_api_key endpoint for security.
    """
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class LLMProviderConfigUpdateAPIKey(BaseModel):
    """Schema for updating only the API key"""
    api_key: str = Field(..., description="New API key (will be encrypted)")


# ============================================================================
# Response Schemas
# ============================================================================

class LLMProviderConfigResponse(LLMProviderConfigBase):
    """
    Schema for LLM provider configuration response.

    SECURITY: API key is NEVER included in responses.
    The encrypted_api_key field is also excluded for security.
    """
    id: int
    user_id: int
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    has_api_key: bool = Field(..., description="Indicates if an API key is configured")

    model_config = ConfigDict(from_attributes=True)


class LLMProviderConfigListResponse(BaseModel):
    """Schema for paginated provider configuration list"""
    providers: list[LLMProviderConfigResponse]
    total: int = Field(..., description="Total number of provider configs")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")


# ============================================================================
# Provider-Specific Configuration Helpers
# ============================================================================

class OpenAIConfig(BaseModel):
    """OpenAI-specific configuration"""
    base_url: Optional[str] = Field(None, description="Custom API base URL for OpenAI-compatible endpoints (e.g. vLLM, LM Studio)")
    organization_id: Optional[str] = Field(None, description="OpenAI organization ID")
    default_model: str = Field(default="gpt-4", description="Default model to use")
    max_tokens: Optional[int] = Field(None, ge=1, le=128000, description="Max tokens")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperature")


class AnthropicConfig(BaseModel):
    """Anthropic-specific configuration"""
    default_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Default model to use"
    )
    max_tokens: Optional[int] = Field(None, ge=1, le=200000, description="Max tokens")
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0, description="Temperature")


class GoogleConfig(BaseModel):
    """Google Gemini-specific configuration"""
    default_model: str = Field(default="gemini-pro", description="Default model to use")
    max_tokens: Optional[int] = Field(None, ge=1, description="Max tokens")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperature")


class AzureOpenAIConfig(BaseModel):
    """Azure OpenAI-specific configuration"""
    endpoint: str = Field(..., description="Azure OpenAI endpoint URL")
    deployment_name: str = Field(..., description="Deployment name")
    api_version: str = Field(default="2023-05-15", description="API version")


class OllamaConfig(BaseModel):
    """Ollama-specific configuration"""
    base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")
    default_model: str = Field(default="llama2", description="Default model to use")


class OpenAICompatibleConfig(BaseModel):
    """Configuration for OpenAI API-compatible servers (vLLM, LM Studio, llama.cpp, etc.)"""
    base_url: str = Field(..., description="Base URL of the OpenAI-compatible server (required)")
    default_model: Optional[str] = Field(None, description="Default model to use")
    max_tokens: Optional[int] = Field(None, ge=1, le=128000, description="Max tokens")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperature")


# ============================================================================
# Test/Validation Schemas
# ============================================================================

class LLMProviderTestRequest(BaseModel):
    """Schema for testing a provider configuration"""
    test_message: str = Field(
        default="Hello, this is a test message.",
        description="Message to send for testing"
    )


class LLMProviderTestResponse(BaseModel):
    """Schema for provider test response"""
    success: bool = Field(..., description="Whether the test succeeded")
    response: Optional[str] = Field(None, description="Response from the LLM")
    error: Optional[str] = Field(None, description="Error message if test failed")
    latency_ms: Optional[int] = Field(None, description="Response latency in milliseconds")
    tokens_used: Optional[int] = Field(None, description="Tokens used in the test")


# ============================================================================
# Model Discovery Schemas
# ============================================================================

class DiscoverModelsRequest(BaseModel):
    """Schema for discovering models from an OpenAI-compatible server"""
    base_url: str = Field(..., description="Base URL of the server")
    api_key: Optional[str] = Field(None, description="Optional API key")


class DiscoverModelsResponse(BaseModel):
    """Schema for model discovery response"""
    success: bool = Field(..., description="Whether discovery succeeded")
    models: list[str] = Field(default_factory=list, description="List of model IDs")
    error: Optional[str] = Field(None, description="Error message if failed")
