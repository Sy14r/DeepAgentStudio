"""MCP audit log model for tracking tool invocations."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class MCPAuditLog(Base):
    """
    Audit log for MCP tool invocations.

    Tracks all MCP tool calls for security auditing and debugging.
    """
    __tablename__ = "mcp_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)

    tool_name = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(Integer, nullable=True)

    success = Column(Boolean, nullable=False)
    error_code = Column(String(50), nullable=True)
    request_summary = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships (optional, for querying)
    user = relationship("User")
    agent = relationship("Agent")

    def __repr__(self):
        return f"<MCPAuditLog(tool={self.tool_name}, success={self.success})>"
