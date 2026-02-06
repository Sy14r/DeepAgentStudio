from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum
from ..database import Base


class ExecutionStrategy(str, Enum):
    """Execution strategy enum - maps to agent executor methods

    Note: The enum NAMES (lowercase) must match the PostgreSQL enum labels
    because SQLAlchemy maps to Python enum by name, not value.
    """
    react = "react"
    plan_and_execute = "plan_and_execute"
    conversational = "conversational"
    codeact = "codeact"


class StrategyType(str, Enum):
    """Strategy type enum - distinguishes builtin strategies from custom code

    Note: The enum NAMES (lowercase) must match the PostgreSQL enum labels.
    """
    builtin = "builtin"
    custom_code = "custom_code"


# Association table for agent_type - recommended_tools many-to-many
agent_type_recommended_tools = Table(
    'agent_type_recommended_tools',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('agent_type_id', Integer, ForeignKey('agent_type_configs.id', ondelete='CASCADE'), nullable=False),
    Column('tool_id', Integer, ForeignKey('tools.id', ondelete='CASCADE'), nullable=False),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False)
)


class AgentTypeConfig(Base):
    """Agent type configuration model for builtin and custom agent types"""

    __tablename__ = "agent_type_configs"

    id = Column(Integer, primary_key=True, index=True)

    # User ownership - nullable for builtin types (like Tools pattern)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Basic info
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # Lucide icon name (e.g., "brain", "workflow")

    # Execution configuration
    execution_strategy = Column(SQLEnum(ExecutionStrategy), nullable=False, default=ExecutionStrategy.react)

    # Custom strategy configuration
    strategy_type = Column(SQLEnum(StrategyType), nullable=False, default=StrategyType.builtin)
    custom_strategy_code = Column(Text, nullable=True)  # Python code for custom strategies
    code_template_version = Column(Integer, default=1, nullable=False)  # Version for template migrations

    # Default prompting
    system_prompt_template = Column(Text, nullable=True)  # Default system prompt with {variables}

    # Default LLM settings as JSON
    # Structure: {"provider": "openai", "model": "gpt-4", "temperature": 0.7, "max_tokens": 4096}
    default_llm_config = Column(JSON, default=dict, nullable=False)

    # Default memory settings as JSON
    # Structure: {"type": "buffer", "context_window": 10, "retrieval_strategy": "similarity"}
    default_memory_config = Column(JSON, default=dict, nullable=False)

    # Iteration limits
    max_iterations = Column(Integer, default=10, nullable=False)

    # Builtin flag and active status
    is_builtin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="agent_types")
    recommended_tools = relationship(
        "Tool",
        secondary=agent_type_recommended_tools,
        backref="recommended_by_types"
    )
    agents = relationship("Agent", back_populates="agent_type_config")

    def __repr__(self):
        return f"<AgentTypeConfig(id={self.id}, name='{self.name}', strategy='{self.execution_strategy.value}', strategy_type='{self.strategy_type.value}', builtin={self.is_builtin})>"
