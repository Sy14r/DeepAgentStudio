"""Tests for MCPAuditLog model."""
import pytest
from datetime import datetime

from app.models.mcp_audit_log import MCPAuditLog
from app.models.agent import Agent
from app.models.agent_type import AgentTypeConfig, StrategyType


class TestMCPAuditLogModel:
    """Test cases for MCPAuditLog model."""

    def test_create_audit_log(self, db, test_user):
        """Test creating an audit log entry."""
        log = MCPAuditLog(
            user_id=test_user.id,
            tool_name="deepagent_agents_list",
            action="agents:list",
            success=True,
            request_summary={"limit": 50}
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        assert log.id is not None
        assert log.tool_name == "deepagent_agents_list"
        assert log.success is True
        assert log.created_at is not None

    def test_create_audit_log_with_agent(self, db, test_user):
        """Test creating an audit log with agent context."""
        agent_type = AgentTypeConfig(
            name="Audit Test Type",
            description="Test",
            strategy=StrategyType.REACT,
            config={},
        )
        db.add(agent_type)
        db.commit()

        agent = Agent(
            user_id=test_user.id,
            name="Audit Agent",
            description="Test",
            agent_type_id=agent_type.id,
            is_active=True
        )
        db.add(agent)
        db.commit()

        log = MCPAuditLog(
            user_id=test_user.id,
            agent_id=agent.id,
            tool_name="deepagent_agents_update",
            action="agents:update:self",
            resource_type="agent",
            resource_id=agent.id,
            success=True
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        assert log.agent_id == agent.id
        assert log.resource_type == "agent"

    def test_create_audit_log_failure(self, db, test_user):
        """Test creating an audit log for a failed operation."""
        log = MCPAuditLog(
            user_id=test_user.id,
            tool_name="deepagent_agents_create",
            action="agents:create",
            success=False,
            error_code="permission_denied"
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        assert log.success is False
        assert log.error_code == "permission_denied"
