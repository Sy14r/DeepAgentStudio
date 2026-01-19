"""Tests for agent permission API endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.agent_permission import AgentPermission, PermissionPreset
from app.mcp_server.permissions import PERMISSION_PRESETS


class TestGetAgentPermissions:
    """Tests for GET /api/v1/agents/{agent_id}/permissions"""

    def test_get_permissions_no_record_returns_default(
        self, client: TestClient, auth_headers: dict, test_agent: dict
    ):
        """When no permission record exists, returns default observer preset."""
        response = client.get(
            f"/api/v1/agents/{test_agent['id']}/permissions",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == test_agent["id"]
        assert data["preset"] == PermissionPreset.OBSERVER.value
        assert data["id"] == 0  # Indicates no record
        assert "agents:list" in data["effective_permissions"]
        assert "agents:read" in data["effective_permissions"]

    def test_get_permissions_with_record(
        self, client: TestClient, auth_headers: dict, test_agent: dict, db: Session
    ):
        """When permission record exists, returns its configuration."""
        # Create permission record
        permission = AgentPermission(
            agent_id=test_agent["id"],
            preset=PermissionPreset.TOOL_CREATOR.value
        )
        db.add(permission)
        db.commit()

        response = client.get(
            f"/api/v1/agents/{test_agent['id']}/permissions",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["preset"] == PermissionPreset.TOOL_CREATOR.value
        assert data["id"] != 0
        # Tool creator should have tool creation permission
        assert "tools:create" in data["effective_permissions"]

    def test_get_permissions_agent_not_found(
        self, client: TestClient, auth_headers: dict
    ):
        """Returns 404 for non-existent agent."""
        response = client.get(
            "/api/v1/agents/99999/permissions",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_get_permissions_unauthorized(
        self, client: TestClient, test_agent: dict
    ):
        """Returns 401 without authentication."""
        response = client.get(
            f"/api/v1/agents/{test_agent['id']}/permissions"
        )
        assert response.status_code == 401


class TestUpdateAgentPermissions:
    """Tests for PUT /api/v1/agents/{agent_id}/permissions"""

    def test_update_permissions_create_new(
        self, client: TestClient, auth_headers: dict, test_agent: dict
    ):
        """Creates permission record when none exists."""
        response = client.put(
            f"/api/v1/agents/{test_agent['id']}/permissions",
            headers=auth_headers,
            json={"preset": PermissionPreset.SELF_IMPROVE.value}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["preset"] == PermissionPreset.SELF_IMPROVE.value
        assert data["id"] != 0
        # Self-improve should have agent update permission
        assert "agents:update:self" in data["effective_permissions"]

    def test_update_permissions_modify_existing(
        self, client: TestClient, auth_headers: dict, test_agent: dict, db: Session
    ):
        """Updates existing permission record."""
        # Create initial permission
        permission = AgentPermission(
            agent_id=test_agent["id"],
            preset=PermissionPreset.OBSERVER.value
        )
        db.add(permission)
        db.commit()
        permission_id = permission.id

        # Update to meta_agent
        response = client.put(
            f"/api/v1/agents/{test_agent['id']}/permissions",
            headers=auth_headers,
            json={"preset": PermissionPreset.META_AGENT.value}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["preset"] == PermissionPreset.META_AGENT.value
        assert data["id"] == permission_id  # Same record updated
        # Meta agent should have wildcard permissions
        assert "agents:*" in data["effective_permissions"]

    def test_update_permissions_with_custom(
        self, client: TestClient, auth_headers: dict, test_agent: dict
    ):
        """Can set custom permissions."""
        response = client.put(
            f"/api/v1/agents/{test_agent['id']}/permissions",
            headers=auth_headers,
            json={
                "preset": PermissionPreset.CUSTOM.value,
                "custom_permissions": ["agents:read", "tools:list", "prompts:create"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["preset"] == PermissionPreset.CUSTOM.value
        assert data["custom_permissions"] == ["agents:read", "tools:list", "prompts:create"]
        # Custom permissions should be in effective
        assert "agents:read" in data["effective_permissions"]
        assert "tools:list" in data["effective_permissions"]
        assert "prompts:create" in data["effective_permissions"]

    def test_update_permissions_invalid_preset(
        self, client: TestClient, auth_headers: dict, test_agent: dict
    ):
        """Returns 400 for invalid preset."""
        response = client.put(
            f"/api/v1/agents/{test_agent['id']}/permissions",
            headers=auth_headers,
            json={"preset": "invalid_preset"}
        )
        assert response.status_code == 400
        assert "Invalid preset" in response.json()["detail"]

    def test_update_permissions_agent_not_found(
        self, client: TestClient, auth_headers: dict
    ):
        """Returns 404 for non-existent agent."""
        response = client.put(
            "/api/v1/agents/99999/permissions",
            headers=auth_headers,
            json={"preset": PermissionPreset.OBSERVER.value}
        )
        assert response.status_code == 404

    def test_update_permissions_unauthorized(
        self, client: TestClient, test_agent: dict
    ):
        """Returns 401 without authentication."""
        response = client.put(
            f"/api/v1/agents/{test_agent['id']}/permissions",
            json={"preset": PermissionPreset.OBSERVER.value}
        )
        assert response.status_code == 401


class TestPermissionPresetContent:
    """Tests verifying permission preset contents are correct."""

    def test_observer_is_read_only(
        self, client: TestClient, auth_headers: dict, test_agent: dict
    ):
        """Observer preset should only have read permissions."""
        response = client.put(
            f"/api/v1/agents/{test_agent['id']}/permissions",
            headers=auth_headers,
            json={"preset": PermissionPreset.OBSERVER.value}
        )
        data = response.json()
        perms = data["effective_permissions"]

        # Should have read/list permissions
        assert "agents:list" in perms
        assert "agents:read" in perms
        assert "tools:list" in perms

        # Should NOT have write permissions
        assert "agents:create" not in perms
        assert "tools:create" not in perms
        assert "agents:delete" not in perms

    def test_meta_agent_has_full_access(
        self, client: TestClient, auth_headers: dict, test_agent: dict
    ):
        """Meta agent preset should have wildcard access."""
        response = client.put(
            f"/api/v1/agents/{test_agent['id']}/permissions",
            headers=auth_headers,
            json={"preset": PermissionPreset.META_AGENT.value}
        )
        data = response.json()
        perms = data["effective_permissions"]

        # Should have wildcard permissions
        assert "agents:*" in perms
        assert "tools:*" in perms
        assert "prompts:*" in perms
