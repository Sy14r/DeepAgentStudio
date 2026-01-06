"""
LLM Provider Configuration models for storing encrypted API keys
and provider-specific settings.
"""
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLEnum

from ..database import Base


class LLMProviderType(str, Enum):
    """LLM provider types"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"


class LLMProviderConfig(Base):
    """
    LLM Provider Configuration model.

    Stores encrypted API keys and provider-specific configuration
    for LLM integrations. Each user can have multiple provider configs.

    Security:
    - API keys are encrypted at rest using Fernet encryption
    - Keys are never returned in API responses (use separate decrypt endpoint)
    - Keys are encrypted before storing, decrypted only when needed
    """
    __tablename__ = "llm_provider_configs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Provider information
    provider_type = Column(SQLEnum(LLMProviderType), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # User-defined name (e.g., "My OpenAI Account")
    description = Column(Text, nullable=True)

    # Encrypted API key (stored as base64-encoded encrypted string)
    encrypted_api_key = Column(Text, nullable=False)

    # Provider-specific configuration
    # Structure varies by provider:
    # OpenAI: {"organization_id": "...", "default_model": "gpt-4", ...}
    # Anthropic: {"default_model": "claude-3-5-sonnet-20241022", ...}
    # Azure: {"endpoint": "...", "deployment_name": "...", ...}
    config = Column(JSON, default=dict, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="llm_provider_configs")

    def __repr__(self):
        return f"<LLMProviderConfig(id={self.id}, provider={self.provider_type.value}, name='{self.name}')>"
