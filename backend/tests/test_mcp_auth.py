"""Tests for MCP auth and permission checking."""
import pytest
from unittest.mock import MagicMock

from app.mcp_server.auth import (
    require_permission,
    check_resource_ownership,
    check_self_or_owned,
    require_self_permission,
    get_agent_permissions
)
from app.mcp_server.context import MCPContext
from app.mcp_server.errors import PermissionDenied, ResourceNotFound
from app.models.agent_permission import PermissionPreset


class TestGetAgentPermissions:
    """Test permission retrieval."""

    def test_direct_user_gets_full_access(self):
        """Test that direct user calls get wildcard access."""
        mock_db = MagicMock()
        ctx = MCPContext(user_id=1, agent_id=None, db=mock_db)

        perms = get_agent_permissions(ctx)

        assert "*" in perms

    def test_cached_permissions_returned(self):
        """Test that cached permissions are returned."""
        mock_db = MagicMock()
        cached = {"agents:read", "tools:list"}
        ctx = MCPContext(user_id=1, agent_id=1, db=mock_db, permissions=cached)

        perms = get_agent_permissions(ctx)

        assert perms == cached
        # DB should not be queried
        mock_db.query.assert_not_called()


class TestRequirePermission:
    """Test permission requirement checking."""

    def test_allow_direct_user_call(self):
        """Test that direct user calls (no agent_id) are allowed."""
        mock_db = MagicMock()
        ctx = MCPContext(user_id=1, agent_id=None, db=mock_db)

        # Should not raise - direct user calls bypass agent permissions
        require_permission(ctx, "agents:create")

    def test_allow_with_cached_permission(self):
        """Test allowing action when permission exists in cache."""
        mock_db = MagicMock()
        cached = {"tools:create", "tools:list"}
        ctx = MCPContext(user_id=1, agent_id=42, db=mock_db, permissions=cached)

        # Should not raise
        require_permission(ctx, "tools:create")

    def test_deny_without_permission(self):
        """Test denying action when permission missing."""
        mock_db = MagicMock()
        cached = {"agents:read", "tools:list"}
        ctx = MCPContext(user_id=1, agent_id=42, db=mock_db, permissions=cached)

        with pytest.raises(PermissionDenied) as exc_info:
            require_permission(ctx, "agents:create")

        assert exc_info.value.details["action"] == "agents:create"

    def test_allow_with_wildcard(self):
        """Test allowing action when wildcard permission exists."""
        mock_db = MagicMock()
        cached = {"agents:*", "tools:list"}
        ctx = MCPContext(user_id=1, agent_id=42, db=mock_db, permissions=cached)

        # Should not raise - agents:* matches agents:create
        require_permission(ctx, "agents:create")


class TestCheckResourceOwnership:
    """Test resource ownership verification."""

    def test_allow_owned_resource(self):
        """Test allowing access to owned resource."""
        from sqlalchemy import Column, Integer, String
        from app.database import Base

        # Use a real model for testing
        from app.models.agent import Agent

        mock_db = MagicMock()

        # Create a mock agent instance
        mock_agent = MagicMock()
        mock_agent.name = "My Agent"
        mock_agent.id = 1
        mock_agent.user_id = 1

        # Set up the mock chain properly
        mock_query = MagicMock()
        mock_filter1 = MagicMock()
        mock_filter2 = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter1
        mock_filter1.filter.return_value = mock_filter2
        mock_filter2.first.return_value = mock_agent

        ctx = MCPContext(user_id=1, agent_id=None, db=mock_db)

        result = check_resource_ownership(ctx, Agent, 1)
        assert result.name == "My Agent"

    def test_deny_not_found(self):
        """Test denying access when resource not found."""
        from app.models.agent import Agent

        mock_db = MagicMock()

        # Set up mock chain to return None
        mock_query = MagicMock()
        mock_filter1 = MagicMock()
        mock_filter2 = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter1
        mock_filter1.filter.return_value = mock_filter2
        mock_filter2.first.return_value = None

        ctx = MCPContext(user_id=1, agent_id=None, db=mock_db)

        with pytest.raises(ResourceNotFound) as exc_info:
            check_resource_ownership(ctx, Agent, 99999)

        assert exc_info.value.details["resource_id"] == 99999


class TestCheckSelfOrOwned:
    """Test self access checking."""

    def test_self_access(self):
        """Test that agent accessing itself returns True."""
        mock_db = MagicMock()
        ctx = MCPContext(user_id=1, agent_id=42, db=mock_db)

        result = check_self_or_owned(ctx, 42)
        assert result is True

    def test_other_agent_access(self):
        """Test that agent accessing another agent returns False."""
        mock_db = MagicMock()
        ctx = MCPContext(user_id=1, agent_id=42, db=mock_db)

        result = check_self_or_owned(ctx, 99)
        assert result is False

    def test_no_agent_context(self):
        """Test that direct user calls return False."""
        mock_db = MagicMock()
        ctx = MCPContext(user_id=1, agent_id=None, db=mock_db)

        result = check_self_or_owned(ctx, 42)
        assert result is False


class TestRequireSelfPermission:
    """Test self permission checking."""

    def test_direct_user_always_allowed(self):
        """Test that direct user calls are always allowed."""
        mock_db = MagicMock()
        ctx = MCPContext(user_id=1, agent_id=None, db=mock_db)

        # Should not raise
        require_self_permission(ctx, "agents:update", 42)

    def test_self_modification_uses_self_permission(self):
        """Test that self modification checks :self permission."""
        mock_db = MagicMock()
        cached = {"agents:update:self"}
        ctx = MCPContext(user_id=1, agent_id=42, db=mock_db, permissions=cached)

        # Should not raise - has agents:update:self
        require_self_permission(ctx, "agents:update", 42)

    def test_other_modification_needs_full_permission(self):
        """Test that modifying other agent needs full permission."""
        mock_db = MagicMock()
        cached = {"agents:update:self"}  # Only has self permission
        ctx = MCPContext(user_id=1, agent_id=42, db=mock_db, permissions=cached)

        with pytest.raises(PermissionDenied):
            require_self_permission(ctx, "agents:update", 99)  # Different agent
