from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class User(Base):
    """User model for authentication and ownership"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    agents = relationship("Agent", back_populates="user", cascade="all, delete-orphan")
    agent_types = relationship("AgentTypeConfig", back_populates="user", cascade="all, delete-orphan")
    tools = relationship("Tool", back_populates="user", cascade="all, delete-orphan")
    prompts = relationship("Prompt", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    llm_provider_configs = relationship("LLMProviderConfig", back_populates="user", cascade="all, delete-orphan")
    mcp_server_configs = relationship("MCPServerConfig", back_populates="user", cascade="all, delete-orphan")
    # Evaluation relationships
    evaluation_datasets = relationship("EvaluationDataset", back_populates="user", cascade="all, delete-orphan")
    evaluators = relationship("Evaluator", back_populates="user", cascade="all, delete-orphan")
    evaluation_runs = relationship("EvaluationRun", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
