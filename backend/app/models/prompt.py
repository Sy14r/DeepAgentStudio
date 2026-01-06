from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum
from ..database import Base


class MessageType(str, Enum):
    """Message type enumeration for prompts"""
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


class Prompt(Base):
    """Prompt template model with versioning support"""

    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    use_case = Column(SQLEnum(PromptUseCase), nullable=False, default=PromptUseCase.OTHER)
    tags = Column(JSON, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    current_version_id = Column(Integer, ForeignKey("prompt_versions.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="prompts")
    versions = relationship("PromptVersion", back_populates="prompt", foreign_keys="PromptVersion.prompt_id", cascade="all, delete-orphan")
    current_version = relationship("PromptVersion", foreign_keys=[current_version_id], post_update=True)

    def __repr__(self):
        return f"<Prompt(id={self.id}, name='{self.name}', use_case='{self.use_case.value}', versions={len(self.versions) if self.versions else 0})>"


class PromptVersion(Base):
    """Prompt version model for version control"""

    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    template = Column(Text, nullable=False)  # The actual prompt template
    variables = Column(JSON, default=list, nullable=False)  # Extracted variable names
    message_type = Column(SQLEnum(MessageType), nullable=False, default=MessageType.USER)
    is_active = Column(Boolean, default=True, nullable=False)  # For A/B testing
    usage_count = Column(Integer, default=0, nullable=False)  # Usage statistics

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    prompt = relationship("Prompt", back_populates="versions", foreign_keys=[prompt_id])
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<PromptVersion(id={self.id}, prompt_id={self.prompt_id}, version={self.version_number}, type='{self.message_type.value}', active={self.is_active})>"
