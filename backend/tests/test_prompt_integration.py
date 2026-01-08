"""
Integration tests for prompt resolution during agent execution.

Tests the complete flow from prompt creation to usage during agent invocation.
"""
import pytest
from app.models.prompt import Prompt, PromptVersion, PromptUseCase, MessageType
from app.services.prompt_service import PromptService, PromptNotFoundError
from app.services.agent_executor import AgentExecutorService


class TestPromptResolutionIntegration:
    """Integration tests for prompt resolution in agent executor"""

    @pytest.fixture
    def prompt_with_variables(self, db, test_user):
        """Create a prompt with variables for testing"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Integration Test Prompt",
            description="A prompt for integration testing",
            use_case=PromptUseCase.CODING
        )
        db.add(prompt)
        db.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="You are a {language} expert. Help the user with {task}.",
            variables=["language", "task"],
            message_type=MessageType.SYSTEM,
            is_active=True,
            usage_count=0,
            created_by=test_user.id
        )
        db.add(version)
        db.flush()

        prompt.current_version_id = version.id
        db.commit()
        db.refresh(prompt)
        db.refresh(version)

        return prompt, version

    def test_resolve_system_prompt_with_prompt_id(
        self, db, test_user, prompt_with_variables
    ):
        """Test that system prompt is resolved from prompt_id"""
        prompt, version = prompt_with_variables

        # Create executor
        executor = AgentExecutorService(db, test_user.id)

        # Config with prompt_id
        config = {
            "prompt_id": prompt.id,
            "prompt_variables": {"language": "Python", "task": "debugging"},
            "system_prompt": "This should be ignored"
        }

        resolved_prompt, version_id = executor._resolve_system_prompt(
            config, "Default prompt"
        )

        assert "Python expert" in resolved_prompt
        assert "debugging" in resolved_prompt
        assert version_id == version.id
        # Ensure system_prompt was not used
        assert "This should be ignored" not in resolved_prompt

    def test_resolve_system_prompt_fallback_to_config(self, db, test_user):
        """Test fallback to system_prompt when no prompt_id"""
        executor = AgentExecutorService(db, test_user.id)

        config = {
            "system_prompt": "You are a helpful assistant."
        }

        resolved_prompt, version_id = executor._resolve_system_prompt(
            config, "Default prompt"
        )

        assert resolved_prompt == "You are a helpful assistant."
        assert version_id is None

    def test_resolve_system_prompt_fallback_to_default(self, db, test_user):
        """Test fallback to default when no prompt_id or system_prompt"""
        executor = AgentExecutorService(db, test_user.id)

        config = {}

        resolved_prompt, version_id = executor._resolve_system_prompt(
            config, "Default system prompt"
        )

        assert resolved_prompt == "Default system prompt"
        assert version_id is None

    def test_resolve_system_prompt_invalid_prompt_id(self, db, test_user):
        """Test graceful fallback when prompt_id is invalid"""
        executor = AgentExecutorService(db, test_user.id)

        config = {
            "prompt_id": 99999,  # Non-existent
            "system_prompt": "Fallback prompt"
        }

        resolved_prompt, version_id = executor._resolve_system_prompt(
            config, "Default"
        )

        # Should fall back to system_prompt
        assert resolved_prompt == "Fallback prompt"
        assert version_id is None

    def test_resolve_system_prompt_other_user_prompt(
        self, db, test_user, second_test_user, prompt_with_variables
    ):
        """Test that users cannot resolve other users' prompts"""
        prompt, _ = prompt_with_variables

        # Create executor for different user
        executor = AgentExecutorService(db, second_test_user.id)

        config = {
            "prompt_id": prompt.id,  # Belongs to test_user
            "system_prompt": "Fallback prompt"
        }

        resolved_prompt, version_id = executor._resolve_system_prompt(
            config, "Default"
        )

        # Should fall back to system_prompt due to access check
        assert resolved_prompt == "Fallback prompt"
        assert version_id is None

    def test_usage_count_incremented_on_resolution(
        self, db, test_user, prompt_with_variables
    ):
        """Test that usage count is incremented when prompt is used"""
        prompt, version = prompt_with_variables
        initial_count = version.usage_count

        executor = AgentExecutorService(db, test_user.id)

        config = {
            "prompt_id": prompt.id,
            "prompt_variables": {"language": "Python", "task": "testing"}
        }

        executor._resolve_system_prompt(config, "Default")

        # Refresh version to get updated count
        db.refresh(version)
        assert version.usage_count == initial_count + 1

    def test_variable_substitution_partial(
        self, db, test_user, prompt_with_variables
    ):
        """Test that partial variables leave placeholders"""
        prompt, _ = prompt_with_variables

        executor = AgentExecutorService(db, test_user.id)

        config = {
            "prompt_id": prompt.id,
            "prompt_variables": {"language": "JavaScript"}
            # Missing 'task' variable
        }

        resolved_prompt, _ = executor._resolve_system_prompt(config, "Default")

        # 'language' should be substituted, 'task' should remain as placeholder
        assert "JavaScript expert" in resolved_prompt
        assert "{task}" in resolved_prompt

    def test_variable_substitution_empty_values(
        self, db, test_user, prompt_with_variables
    ):
        """Test substitution with empty string values"""
        prompt, _ = prompt_with_variables

        executor = AgentExecutorService(db, test_user.id)

        config = {
            "prompt_id": prompt.id,
            "prompt_variables": {"language": "", "task": "coding"}
        }

        resolved_prompt, _ = executor._resolve_system_prompt(config, "Default")

        # Empty value should replace the placeholder
        assert "You are a  expert" in resolved_prompt
        assert "coding" in resolved_prompt


class TestPromptServiceIntegration:
    """Integration tests for PromptService with database"""

    def test_resolve_and_track_usage(self, db, test_user):
        """Test complete flow of resolving and tracking usage"""
        # Create prompt
        prompt = Prompt(
            user_id=test_user.id,
            name="Usage Tracking Test",
            use_case=PromptUseCase.RESEARCH
        )
        db.add(prompt)
        db.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Research {topic} thoroughly",
            variables=["topic"],
            is_active=True,
            usage_count=0,
            created_by=test_user.id
        )
        db.add(version)
        db.flush()

        prompt.current_version_id = version.id
        db.commit()

        # Resolve prompt multiple times
        service = PromptService(db)

        for i in range(3):
            result = service.resolve_prompt(
                prompt_id=prompt.id,
                variables={"topic": f"Topic {i}"},
                user_id=test_user.id,
                increment_usage=True
            )
            assert f"Topic {i}" in result.rendered

        # Verify usage count
        db.refresh(version)
        assert version.usage_count == 3

    def test_resolve_specific_version(self, db, test_user):
        """Test resolving a specific version instead of current"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Multi-Version Test"
        )
        db.add(prompt)
        db.flush()

        version1 = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Version 1: {msg}",
            variables=["msg"],
            is_active=True,
            created_by=test_user.id
        )
        version2 = PromptVersion(
            prompt_id=prompt.id,
            version_number=2,
            template="Version 2: {msg}",
            variables=["msg"],
            is_active=True,
            created_by=test_user.id
        )
        db.add_all([version1, version2])
        db.flush()

        prompt.current_version_id = version2.id
        db.commit()

        service = PromptService(db)

        # Resolve current version (v2)
        result_current = service.resolve_prompt(
            prompt_id=prompt.id,
            variables={"msg": "test"},
            user_id=test_user.id
        )
        assert "Version 2" in result_current.rendered
        assert result_current.version_id == version2.id

        # Resolve specific version (v1)
        result_v1 = service.resolve_prompt(
            prompt_id=prompt.id,
            variables={"msg": "test"},
            version_id=version1.id,
            user_id=test_user.id
        )
        assert "Version 1" in result_v1.rendered
        assert result_v1.version_id == version1.id

    def test_resolve_inactive_prompt_fails(self, db, test_user):
        """Test that inactive prompts cannot be resolved"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Inactive Prompt",
            is_active=False
        )
        db.add(prompt)
        db.commit()

        service = PromptService(db)

        with pytest.raises(PromptNotFoundError):
            service.resolve_prompt(
                prompt_id=prompt.id,
                variables={},
                user_id=test_user.id
            )


class TestSessionPromptTracking:
    """Tests for session-prompt tracking"""

    @pytest.fixture
    def prompt_for_session(self, db, test_user):
        """Create a prompt for session tracking tests"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Session Test Prompt"
        )
        db.add(prompt)
        db.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Hello {name}",
            variables=["name"],
            is_active=True,
            created_by=test_user.id
        )
        db.add(version)
        db.flush()

        prompt.current_version_id = version.id
        db.commit()

        return prompt, version

    def test_prompt_version_tracked_in_session(
        self, db, test_user, prompt_for_session
    ):
        """Test that prompt_version_id is returned for session tracking"""
        prompt, version = prompt_for_session

        service = PromptService(db)
        result = service.resolve_prompt(
            prompt_id=prompt.id,
            variables={"name": "World"},
            user_id=test_user.id
        )

        # The version_id should be available for storing in session
        assert result.version_id == version.id
        assert result.prompt_id == prompt.id

    def test_prompt_info_retrieval(self, db, test_user, prompt_for_session):
        """Test get_prompt_info for session context"""
        prompt, version = prompt_for_session

        service = PromptService(db)
        info = service.get_prompt_info(prompt.id, test_user.id)

        assert info["id"] == prompt.id
        assert info["name"] == "Session Test Prompt"
        assert info["template"] == "Hello {name}"
        assert info["variables"] == ["name"]
        assert info["version_id"] == version.id
