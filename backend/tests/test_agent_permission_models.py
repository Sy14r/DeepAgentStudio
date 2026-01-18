"""Tests for AgentPermission model."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.agent_permission import AgentPermission, PermissionPreset
from app.models.agent import Agent
from app.models.agent_type import AgentTypeConfig, StrategyType


class TestAgentPermissionModel:
    """Test cases for AgentPermission model."""

    def test_create_permission_with_preset(self, db, test_user):
        """Test creating a permission with a preset."""
        # Create an agent type first
        agent_type = AgentTypeConfig(
            name="Test Type",
            description="Test",
            strategy=StrategyType.REACT,
            config={},
        )
        db.add(agent_type)
        db.commit()

        # Create an agent
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            description="Test",
            agent_type_id=agent_type.id,
            is_active=True
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)

        # Create permission
        permission = AgentPermission(
            agent_id=agent.id,
            preset=PermissionPreset.SELF_IMPROVE
        )
        db.add(permission)
        db.commit()
        db.refresh(permission)

        assert permission.id is not None
        assert permission.preset == PermissionPreset.SELF_IMPROVE
        assert permission.custom_permissions is None
        assert permission.created_at is not None

    def test_create_permission_with_custom(self, db, test_user):
        """Test creating a permission with custom permissions."""
        agent_type = AgentTypeConfig(
            name="Test Type 2",
            description="Test",
            strategy=StrategyType.REACT,
            config={},
        )
        db.add(agent_type)
        db.commit()

        agent = Agent(
            user_id=test_user.id,
            name="Custom Agent",
            description="Test",
            agent_type_id=agent_type.id,
            is_active=True
        )
        db.add(agent)
        db.commit()

        permission = AgentPermission(
            agent_id=agent.id,
            preset=PermissionPreset.CUSTOM,
            custom_permissions=["agents:read", "tools:create"]
        )
        db.add(permission)
        db.commit()
        db.refresh(permission)

        assert permission.preset == PermissionPreset.CUSTOM
        assert permission.custom_permissions == ["agents:read", "tools:create"]

    def test_unique_agent_constraint(self, db, test_user):
        """Test that each agent can only have one permission record."""
        agent_type = AgentTypeConfig(
            name="Test Type 3",
            description="Test",
            strategy=StrategyType.REACT,
            config={},
        )
        db.add(agent_type)
        db.commit()

        agent = Agent(
            user_id=test_user.id,
            name="Unique Agent",
            description="Test",
            agent_type_id=agent_type.id,
            is_active=True
        )
        db.add(agent)
        db.commit()

        perm1 = AgentPermission(agent_id=agent.id, preset=PermissionPreset.OBSERVER)
        db.add(perm1)
        db.commit()

        perm2 = AgentPermission(agent_id=agent.id, preset=PermissionPreset.META_AGENT)
        db.add(perm2)

        with pytest.raises(IntegrityError):
            db.commit()

    def test_cascade_delete_on_agent_delete(self, db, test_user):
        """Test that permission is deleted when agent is deleted."""
        agent_type = AgentTypeConfig(
            name="Test Type 4",
            description="Test",
            strategy=StrategyType.REACT,
            config={},
        )
        db.add(agent_type)
        db.commit()

        agent = Agent(
            user_id=test_user.id,
            name="Cascade Agent",
            description="Test",
            agent_type_id=agent_type.id,
            is_active=True
        )
        db.add(agent)
        db.commit()

        permission = AgentPermission(agent_id=agent.id, preset=PermissionPreset.TOOL_CREATOR)
        db.add(permission)
        db.commit()
        permission_id = permission.id

        # Delete agent
        db.delete(agent)
        db.commit()

        # Permission should be gone
        result = db.query(AgentPermission).filter(AgentPermission.id == permission_id).first()
        assert result is None

    def test_default_preset_is_observer(self, db, test_user):
        """Test that default preset is observer."""
        agent_type = AgentTypeConfig(
            name="Test Type 5",
            description="Test",
            strategy=StrategyType.REACT,
            config={},
        )
        db.add(agent_type)
        db.commit()

        agent = Agent(
            user_id=test_user.id,
            name="Default Agent",
            description="Test",
            agent_type_id=agent_type.id,
            is_active=True
        )
        db.add(agent)
        db.commit()

        permission = AgentPermission(agent_id=agent.id)
        db.add(permission)
        db.commit()
        db.refresh(permission)

        assert permission.preset == PermissionPreset.OBSERVER


class TestPermissionPresetEnum:
    """Test cases for PermissionPreset enum."""

    def test_all_presets_exist(self):
        """Test that all expected presets are defined."""
        assert PermissionPreset.OBSERVER == "observer"
        assert PermissionPreset.SELF_IMPROVE == "self_improve"
        assert PermissionPreset.TOOL_CREATOR == "tool_creator"
        assert PermissionPreset.META_AGENT == "meta_agent"
        assert PermissionPreset.CUSTOM == "custom"
