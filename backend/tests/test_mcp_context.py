"""Tests for MCP server context."""
import pytest
from unittest.mock import MagicMock

from app.mcp_server.context import MCPContext, create_context, get_context, set_context, reset_context


class TestMCPContext:
    """Test MCP context management."""

    def test_create_context(self):
        """Test creating a context."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1

        ctx = create_context(user=mock_user, db=mock_db, agent_id=42)

        assert ctx.user_id == 1
        assert ctx.agent_id == 42
        assert ctx.db is mock_db

    def test_context_without_agent(self):
        """Test creating context without agent (direct user call)."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1

        ctx = create_context(user=mock_user, db=mock_db)

        assert ctx.user_id == 1
        assert ctx.agent_id is None

    def test_context_with_permissions(self):
        """Test creating context with permissions."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        perms = {"agents:read", "tools:list"}

        ctx = create_context(user=mock_user, db=mock_db, permissions=perms)

        assert ctx.permissions == perms

    def test_set_and_get_context(self):
        """Test context variable setting and getting."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 5

        ctx = create_context(user=mock_user, db=mock_db, agent_id=10)
        token = set_context(ctx)

        try:
            retrieved = get_context()
            assert retrieved.user_id == 5
            assert retrieved.agent_id == 10
        finally:
            reset_context(token)

    def test_get_context_raises_without_set(self):
        """Test that getting context without setting raises error."""
        # Reset any existing context
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        ctx = create_context(user=mock_user, db=mock_db)
        token = set_context(ctx)
        reset_context(token)

        # Now context should be None, get_context should raise
        with pytest.raises(RuntimeError, match="No MCP context set"):
            get_context()

    def test_reset_context(self):
        """Test resetting context restores previous value."""
        mock_db = MagicMock()
        mock_user1 = MagicMock()
        mock_user1.id = 1
        mock_user2 = MagicMock()
        mock_user2.id = 2

        ctx1 = create_context(user=mock_user1, db=mock_db)
        token1 = set_context(ctx1)

        try:
            ctx2 = create_context(user=mock_user2, db=mock_db)
            token2 = set_context(ctx2)

            assert get_context().user_id == 2

            reset_context(token2)
            assert get_context().user_id == 1
        finally:
            reset_context(token1)
