from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum
from ..database import Base


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


# Association table for agent-tool many-to-many relationship
agent_tools = Table(
    'agent_tools',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('agent_id', Integer, ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
    Column('tool_id', Integer, ForeignKey('tools.id', ondelete='CASCADE'), nullable=False),
    Column('config', JSON, default=dict, nullable=False),  # Tool-specific config override
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False)
)


class Tool(Base):
    """Tool model for built-in and custom tools"""

    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(SQLEnum(ToolCategory), nullable=False, default=ToolCategory.OTHER)
    tags = Column(JSON, default=list, nullable=False)
    tool_type = Column(SQLEnum(ToolType), nullable=False, default=ToolType.BUILTIN)
    is_active = Column(Boolean, default=True, nullable=False)

    # For built-in tools
    langchain_class = Column(String(255), nullable=True)  # e.g., "DuckDuckGoSearchRun"
    required_config = Column(JSON, default=dict, nullable=True)  # Required API keys, params, etc.

    # For custom tools
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    function_code = Column(Text, nullable=True)  # Python function code
    input_schema = Column(JSON, nullable=True)  # Input parameter schema
    output_schema = Column(JSON, nullable=True)  # Output schema

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="tools")
    # Many-to-many with agents through agent_tools table
    # agents = relationship("Agent", secondary=agent_tools, back_populates="tools")

    def __repr__(self):
        return f"<Tool(id={self.id}, name='{self.name}', type='{self.tool_type.value}', category='{self.category.value}')>"
