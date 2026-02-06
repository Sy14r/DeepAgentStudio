"""Tests for MCP permission system."""
import pytest

from app.mcp_server.permissions import (
    PERMISSION_PRESETS,
    resolve_permissions,
    has_permission,
)
from app.models.agent_permission import PermissionPreset


class TestPermissionPresets:
    """Test permission preset definitions."""

    def test_observer_permissions(self):
        """Test observer preset has read-only permissions."""
        perms = PERMISSION_PRESETS[PermissionPreset.OBSERVER.value]

        assert "agents:list" in perms
        assert "agents:read" in perms
        assert "tools:list" in perms
        assert "agents:create" not in perms
        assert "agents:update:self" not in perms

    def test_self_improve_permissions(self):
        """Test self_improve preset includes observer + self-modification."""
        perms = PERMISSION_PRESETS[PermissionPreset.SELF_IMPROVE.value]

        # Has observer permissions
        assert "agents:list" in perms
        assert "agents:read" in perms

        # Plus self-modification
        assert "agents:update:self" in perms
        assert "prompts:create" in perms
        assert "datasets:update:examples" in perms

        # But not full create
        assert "agents:create" not in perms

    def test_tool_creator_permissions(self):
        """Test tool_creator preset includes self_improve + tool creation."""
        perms = PERMISSION_PRESETS[PermissionPreset.TOOL_CREATOR.value]

        # Has self_improve permissions
        assert "agents:update:self" in perms

        # Plus tool creation
        assert "tools:create" in perms
        assert "tools:update:own" in perms

        # But not agent creation
        assert "agents:create" not in perms

    def test_meta_agent_permissions(self):
        """Test meta_agent preset has full access."""
        perms = PERMISSION_PRESETS[PermissionPreset.META_AGENT.value]

        assert "agents:*" in perms
        assert "tools:*" in perms
        assert "prompts:*" in perms
        assert "datasets:*" in perms
        assert "evaluations:*" in perms


class TestResolvePermissions:
    """Test permission resolution."""

    def test_resolve_preset(self):
        """Test resolving a preset to permission list."""
        perms = resolve_permissions(PermissionPreset.OBSERVER.value, None)

        assert isinstance(perms, set)
        assert "agents:list" in perms

    def test_resolve_custom(self):
        """Test resolving custom permissions."""
        custom = ["agents:read", "tools:create"]
        perms = resolve_permissions(PermissionPreset.CUSTOM.value, custom)

        assert perms == {"agents:read", "tools:create"}


class TestHasPermission:
    """Test permission checking."""

    def test_exact_match(self):
        """Test exact permission match."""
        perms = {"agents:list", "agents:read"}

        assert has_permission(perms, "agents:list") is True
        assert has_permission(perms, "agents:create") is False

    def test_wildcard_match(self):
        """Test wildcard permission matching."""
        perms = {"agents:*"}

        assert has_permission(perms, "agents:list") is True
        assert has_permission(perms, "agents:create") is True
        assert has_permission(perms, "agents:update:self") is True
        assert has_permission(perms, "tools:create") is False

    def test_self_permission(self):
        """Test :self permission matching."""
        perms = {"agents:update:self"}

        # :self matches :self
        assert has_permission(perms, "agents:update:self") is True
        # :self does NOT match general :*
        assert has_permission(perms, "agents:update:other") is False

    def test_own_permission(self):
        """Test :own permission matching."""
        perms = {"tools:update:own"}

        assert has_permission(perms, "tools:update:own") is True
        assert has_permission(perms, "tools:update:other") is False
