"""Agent permission model for MCP access control."""
from enum import Enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class PermissionPreset(str, Enum):
    """Permission preset levels for agents."""
    OBSERVER = "observer"
    SELF_IMPROVE = "self_improve"
    TOOL_CREATOR = "tool_creator"
    META_AGENT = "meta_agent"
    CUSTOM = "custom"


class AgentPermission(Base):
    """
    Stores MCP permissions for agents.

    Each agent can have one permission record defining what MCP tools
    it can access. Permissions are either a preset (observer, self_improve,
    tool_creator, meta_agent) or custom (explicit permission list).
    """
    __tablename__ = "agent_permissions"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    preset = Column(
        SQLEnum(PermissionPreset),
        nullable=False,
        default=PermissionPreset.OBSERVER
    )
    custom_permissions = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    agent = relationship("Agent", back_populates="mcp_permission")

    def __repr__(self):
        return f"<AgentPermission(agent_id={self.agent_id}, preset={self.preset})>"
