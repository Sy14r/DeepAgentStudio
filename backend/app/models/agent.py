from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Agent(Base):
    """Agent model for managing LangChain agents"""

    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)  # Nullable for built-in agents
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # FK to agent_type_configs for execution strategy
    agent_type_id = Column(Integer, ForeignKey("agent_type_configs.id"), nullable=False, index=True)

    tags = Column(JSON, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_builtin = Column(Boolean, default=False, nullable=False, index=True)  # Built-in agents visible to all

    # Reference to current active version
    current_version_id = Column(Integer, ForeignKey("agent_versions.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="agents")
    agent_type_config = relationship("AgentTypeConfig", back_populates="agents")
    versions = relationship(
        "AgentVersion",
        back_populates="agent",
        foreign_keys="AgentVersion.agent_id",
        cascade="all, delete-orphan",
        order_by="AgentVersion.version_number.desc()"
    )
    current_version = relationship(
        "AgentVersion",
        foreign_keys=[current_version_id],
        post_update=True
    )
    mcp_servers = relationship(
        "MCPServerConfig",
        secondary="agent_mcp_servers",
        back_populates="agents"
    )
    evaluation_runs = relationship("EvaluationRun", back_populates="agent")

    def __repr__(self):
        type_name = self.agent_type_config.name if self.agent_type_config else "unknown"
        return f"<Agent(id={self.id}, name='{self.name}', type='{type_name}')>"


class AgentVersion(Base):
    """Agent version model for version control"""

    __tablename__ = "agent_versions"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)

    # Configuration stored as JSONB for flexibility
    # Structure:
    # {
    #   "llm_config": {
    #     "provider": "openai",
    #     "model": "gpt-4",
    #     "temperature": 0.7,
    #     "max_tokens": 2000,
    #     "stop_sequences": []
    #   },
    #   "reflection_config": {
    #     "enabled": true,
    #     "depth": 2,
    #     "iteration_limit": 5
    #   },
    #   "memory_config": {
    #     "type": "buffer",
    #     "context_window": 10,
    #     "retrieval_strategy": "similarity"
    #   },
    #   "tool_ids": [1, 2, 3],
    #   "prompt_id": 1,
    #   "system_prompt": "You are a helpful assistant..."
    # }
    config = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="versions", foreign_keys=[agent_id])
    creator = relationship("User")

    def __repr__(self):
        return f"<AgentVersion(id={self.id}, agent_id={self.agent_id}, version={self.version_number})>"
