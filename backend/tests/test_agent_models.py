"""
Tests for Agent and AgentVersion models
"""
import pytest
from sqlalchemy.exc import IntegrityError
from app.models.agent import Agent, AgentVersion, AgentType
from app.models.user import User
from app.security import hash_password


class TestAgentModel:
    """Test cases for Agent model"""

    def test_create_agent_with_all_fields(self, db, test_user):
        """Test creating an agent with all fields"""
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            description="A test agent for testing",
            agent_type=AgentType.REACT,
            tags=["test", "automation"],
            is_active=True
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)

        assert agent.id is not None
        assert agent.user_id == test_user.id
        assert agent.name == "Test Agent"
        assert agent.description == "A test agent for testing"
        assert agent.agent_type == AgentType.REACT
        assert agent.tags == ["test", "automation"]
        assert agent.is_active is True
        assert agent.current_version_id is None
        assert agent.created_at is not None
        assert agent.updated_at is not None

    def test_create_agent_minimal_fields(self, db, test_user):
        """Test creating an agent with minimal required fields"""
        agent = Agent(
            user_id=test_user.id,
            name="Minimal Agent",
            agent_type=AgentType.CONVERSATIONAL
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)

        assert agent.id is not None
        assert agent.name == "Minimal Agent"
        assert agent.description is None
        assert agent.agent_type == AgentType.CONVERSATIONAL
        assert agent.tags == []
        assert agent.is_active is True

    def test_agent_defaults(self, db, test_user):
        """Test agent default values"""
        agent = Agent(
            user_id=test_user.id,
            name="Default Agent"
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)

        assert agent.agent_type == AgentType.REACT  # Default type
        assert agent.tags == []
        assert agent.is_active is True
        assert agent.current_version_id is None

    def test_agent_without_user_id_fails(self, db):
        """Test that creating an agent without user_id fails"""
        agent = Agent(name="No User Agent")
        db.add(agent)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_agent_without_name_fails(self, db, test_user):
        """Test that creating an agent without name fails"""
        agent = Agent(user_id=test_user.id)
        db.add(agent)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_agent_types(self, db, test_user):
        """Test different agent types"""
        agent_types = [
            AgentType.REACT,
            AgentType.PLAN_AND_EXECUTE,
            AgentType.CONVERSATIONAL,
            AgentType.CUSTOM
        ]

        for agent_type in agent_types:
            agent = Agent(
                user_id=test_user.id,
                name=f"Agent {agent_type.value}",
                agent_type=agent_type
            )
            db.add(agent)
            db.commit()
            db.refresh(agent)
            assert agent.agent_type == agent_type

    def test_query_agent_by_name(self, db, test_user):
        """Test querying agent by name"""
        agent = Agent(
            user_id=test_user.id,
            name="Searchable Agent"
        )
        db.add(agent)
        db.commit()

        found = db.query(Agent).filter(Agent.name == "Searchable Agent").first()
        assert found is not None
        assert found.name == "Searchable Agent"

    def test_query_agent_by_user_id(self, db, test_user):
        """Test querying agents by user_id"""
        agent1 = Agent(user_id=test_user.id, name="Agent 1")
        agent2 = Agent(user_id=test_user.id, name="Agent 2")
        db.add_all([agent1, agent2])
        db.commit()

        agents = db.query(Agent).filter(Agent.user_id == test_user.id).all()
        assert len(agents) == 2

    def test_update_agent(self, db, test_user):
        """Test updating agent attributes"""
        agent = Agent(user_id=test_user.id, name="Original Name")
        db.add(agent)
        db.commit()

        agent.name = "Updated Name"
        agent.description = "New description"
        agent.tags = ["updated"]
        db.commit()
        db.refresh(agent)

        assert agent.name == "Updated Name"
        assert agent.description == "New description"
        assert agent.tags == ["updated"]

    def test_delete_agent(self, db, test_user):
        """Test deleting an agent"""
        agent = Agent(user_id=test_user.id, name="Delete Me")
        db.add(agent)
        db.commit()
        agent_id = agent.id

        db.delete(agent)
        db.commit()

        deleted = db.query(Agent).filter(Agent.id == agent_id).first()
        assert deleted is None

    def test_soft_delete_agent(self, db, test_user):
        """Test soft deleting an agent (is_active=False)"""
        agent = Agent(user_id=test_user.id, name="Soft Delete Me")
        db.add(agent)
        db.commit()

        agent.is_active = False
        db.commit()
        db.refresh(agent)

        assert agent.is_active is False
        assert db.query(Agent).filter(Agent.id == agent.id).first() is not None

    def test_agent_cascade_delete_with_user(self, db):
        """Test that deleting a user cascades to delete agents"""
        user = User(
            username="deleteuser",
            email="delete@example.com",
            hashed_password=hash_password("password123")
        )
        db.add(user)
        db.commit()

        agent = Agent(user_id=user.id, name="Will be deleted")
        db.add(agent)
        db.commit()
        agent_id = agent.id

        db.delete(user)
        db.commit()

        deleted_agent = db.query(Agent).filter(Agent.id == agent_id).first()
        assert deleted_agent is None

    def test_multiple_agents_for_user(self, db, test_user):
        """Test creating multiple agents for same user"""
        agents = [
            Agent(user_id=test_user.id, name=f"Agent {i}")
            for i in range(5)
        ]
        db.add_all(agents)
        db.commit()

        user_agents = db.query(Agent).filter(Agent.user_id == test_user.id).all()
        assert len(user_agents) == 5

    def test_agent_repr(self, db, test_user):
        """Test agent string representation"""
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        repr_str = repr(agent)
        assert "Agent" in repr_str
        assert str(agent.id) in repr_str
        assert "Test Agent" in repr_str
        assert "ReAct" in repr_str


class TestAgentVersionModel:
    """Test cases for AgentVersion model"""

    def test_create_agent_version(self, db, test_user):
        """Test creating an agent version"""
        agent = Agent(user_id=test_user.id, name="Versioned Agent")
        db.add(agent)
        db.commit()

        config = {
            "llm_config": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000
            }
        }

        version = AgentVersion(
            agent_id=agent.id,
            version_number=1,
            config=config,
            created_by=test_user.id
        )
        db.add(version)
        db.commit()
        db.refresh(version)

        assert version.id is not None
        assert version.agent_id == agent.id
        assert version.version_number == 1
        assert version.config == config
        assert version.created_by == test_user.id
        assert version.created_at is not None

    def test_agent_version_complex_config(self, db, test_user):
        """Test agent version with complex configuration"""
        agent = Agent(user_id=test_user.id, name="Complex Agent")
        db.add(agent)
        db.commit()

        config = {
            "llm_config": {
                "provider": "anthropic",
                "model": "claude-3-opus",
                "temperature": 0.8,
                "max_tokens": 4000,
                "stop_sequences": ["END", "STOP"]
            },
            "reflection_config": {
                "enabled": True,
                "depth": 3,
                "iteration_limit": 10
            },
            "memory_config": {
                "type": "vector",
                "context_window": 20,
                "retrieval_strategy": "mmr"
            },
            "tool_ids": [1, 2, 3, 4],
            "prompt_id": 5,
            "system_prompt": "You are a helpful assistant."
        }

        version = AgentVersion(
            agent_id=agent.id,
            version_number=1,
            config=config,
            created_by=test_user.id
        )
        db.add(version)
        db.commit()
        db.refresh(version)

        assert version.config["llm_config"]["provider"] == "anthropic"
        assert version.config["reflection_config"]["enabled"] is True
        assert version.config["memory_config"]["type"] == "vector"
        assert len(version.config["tool_ids"]) == 4

    def test_multiple_versions_for_agent(self, db, test_user):
        """Test creating multiple versions for same agent"""
        agent = Agent(user_id=test_user.id, name="Multi-Version Agent")
        db.add(agent)
        db.commit()

        configs = [
            {"llm_config": {"provider": "openai", "model": f"gpt-{i}"}}
            for i in range(1, 4)
        ]

        for i, config in enumerate(configs, start=1):
            version = AgentVersion(
                agent_id=agent.id,
                version_number=i,
                config=config,
                created_by=test_user.id
            )
            db.add(version)
        db.commit()

        versions = db.query(AgentVersion).filter(
            AgentVersion.agent_id == agent.id
        ).all()
        assert len(versions) == 3

    def test_agent_version_without_agent_id_fails(self, db, test_user):
        """Test that creating version without agent_id fails"""
        version = AgentVersion(
            version_number=1,
            config={},
            created_by=test_user.id
        )
        db.add(version)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_agent_version_without_config_uses_default(self, db, test_user):
        """Test that creating version without config uses empty dict default"""
        agent = Agent(user_id=test_user.id, name="Agent")
        db.add(agent)
        db.commit()

        version = AgentVersion(
            agent_id=agent.id,
            version_number=1,
            created_by=test_user.id
        )
        db.add(version)
        db.commit()
        db.refresh(version)

        assert version.config == {}

    def test_agent_version_cascade_delete(self, db, test_user):
        """Test that deleting agent cascades to delete versions"""
        agent = Agent(user_id=test_user.id, name="Delete Me")
        db.add(agent)
        db.commit()

        version = AgentVersion(
            agent_id=agent.id,
            version_number=1,
            config={"test": "data"},
            created_by=test_user.id
        )
        db.add(version)
        db.commit()
        version_id = version.id

        db.delete(agent)
        db.commit()

        deleted_version = db.query(AgentVersion).filter(
            AgentVersion.id == version_id
        ).first()
        assert deleted_version is None

    def test_agent_version_ordering(self, db, test_user):
        """Test querying versions in descending order"""
        agent = Agent(user_id=test_user.id, name="Ordered Agent")
        db.add(agent)
        db.commit()

        for i in range(5, 0, -1):
            version = AgentVersion(
                agent_id=agent.id,
                version_number=i,
                config={"version": i},
                created_by=test_user.id
            )
            db.add(version)
        db.commit()

        versions = db.query(AgentVersion).filter(
            AgentVersion.agent_id == agent.id
        ).order_by(AgentVersion.version_number.desc()).all()

        assert versions[0].version_number == 5
        assert versions[-1].version_number == 1

    def test_agent_current_version_relationship(self, db, test_user):
        """Test agent current_version relationship"""
        agent = Agent(user_id=test_user.id, name="Current Version Agent")
        db.add(agent)
        db.commit()

        version = AgentVersion(
            agent_id=agent.id,
            version_number=1,
            config={"test": "data"},
            created_by=test_user.id
        )
        db.add(version)
        db.commit()

        agent.current_version_id = version.id
        db.commit()
        db.refresh(agent)

        assert agent.current_version_id == version.id
        # Note: current_version relationship will be tested in integration tests

    def test_agent_version_repr(self, db, test_user):
        """Test agent version string representation"""
        agent = Agent(user_id=test_user.id, name="Agent")
        db.add(agent)
        db.commit()

        version = AgentVersion(
            agent_id=agent.id,
            version_number=1,
            config={},
            created_by=test_user.id
        )
        db.add(version)
        db.commit()

        repr_str = repr(version)
        assert "AgentVersion" in repr_str
        assert str(version.id) in repr_str
        assert str(agent.id) in repr_str
        assert "1" in repr_str
