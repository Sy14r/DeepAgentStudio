"""
Workspace models for Advanced Agent Toolkit.

This module implements workspace management for autonomous agents:
- SessionWorkspace: Isolated file storage for each session
- SessionTask: Task list for tracking progress on complex tasks
- SessionScratchpad: Working notes and intermediate thoughts
- SearchProviderConfig: Web search API configuration
"""
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, BigInteger
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLEnum

from ..database import Base


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class SearchProviderType(str, Enum):
    """Search provider type enumeration"""
    SERPER = "serper"
    TAVILY = "tavily"
    SERPAPI = "serpapi"


class SessionWorkspace(Base):
    """
    SessionWorkspace model - Manages isolated file storage for each session.

    Each session gets a dedicated workspace directory where the agent can
    read, write, and edit files. The workspace is sandboxed for security.
    """
    __tablename__ = "session_workspaces"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Workspace metadata
    workspace_path = Column(String(255), nullable=False)  # Relative path from base
    total_size_bytes = Column(BigInteger, default=0, nullable=False)
    file_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    # Use passive_deletes=True to let the database handle cascade delete via ondelete="CASCADE"
    session = relationship("Session", backref=backref("workspace", uselist=False, passive_deletes=True))

    def __repr__(self):
        return f"<SessionWorkspace(id={self.id}, session_id={self.session_id}, path='{self.workspace_path}')>"


class SessionTask(Base):
    """
    SessionTask model - Task list for tracking progress on complex tasks.

    Agents can create, update, and complete tasks to track their progress
    on multi-step work. Tasks persist across context window resets.
    """
    __tablename__ = "session_tasks"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Task data
    task_number = Column(Integer, nullable=False)  # Per-session sequential ID
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        SQLEnum(TaskStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TaskStatus.PENDING,
        index=True
    )
    notes = Column(Text, nullable=True)  # Accumulated notes/updates

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    # Use passive_deletes=True to let the database handle cascade delete via ondelete="CASCADE"
    session = relationship("Session", backref=backref("tasks", passive_deletes=True))

    def __repr__(self):
        return f"<SessionTask(id={self.id}, session_id={self.session_id}, task_number={self.task_number}, status={self.status.value})>"


class SessionScratchpad(Base):
    """
    SessionScratchpad model - Working notes and intermediate thoughts.

    Agents can use the scratchpad to preserve context across turns,
    store intermediate results, and maintain continuity on long tasks.
    Supports multiple named sections.
    """
    __tablename__ = "session_scratchpads"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Scratchpad data
    section = Column(String(100), nullable=False, default="default")  # Named section
    content = Column(Text, nullable=False, default="")

    # Timestamps
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    # Use passive_deletes=True to let the database handle cascade delete via ondelete="CASCADE"
    session = relationship("Session", backref=backref("scratchpads", passive_deletes=True))

    def __repr__(self):
        return f"<SessionScratchpad(id={self.id}, session_id={self.session_id}, section='{self.section}')>"


class SearchProviderConfig(Base):
    """
    SearchProviderConfig model - Web search API configuration.

    Users can configure their preferred search API provider for
    the web_search tool. API keys are encrypted at rest.
    """
    __tablename__ = "search_provider_configs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Provider configuration
    provider_type = Column(SQLEnum(SearchProviderType), nullable=False, index=True)
    api_key_encrypted = Column(String(500), nullable=False)  # Fernet encrypted

    # Settings
    is_active = Column(Boolean, default=True, nullable=False)
    default_num_results = Column(Integer, default=5, nullable=False)

    # Usage tracking
    total_searches = Column(Integer, default=0, nullable=False)
    last_search_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    user = relationship("User", backref="search_provider_config", uselist=False)

    def __repr__(self):
        return f"<SearchProviderConfig(id={self.id}, user_id={self.user_id}, provider='{self.provider_type.value}')>"
