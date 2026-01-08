"""
Tests for PromptService - prompt resolution and variable substitution.
"""
import pytest
from app.services.prompt_service import (
    PromptService,
    PromptNotFoundError,
    PromptVariableError,
    PromptResolutionResult,
)
from app.models.prompt import Prompt, PromptVersion, PromptUseCase, MessageType


class TestPromptServiceVariableExtraction:
    """Test cases for variable extraction from templates"""

    def test_extract_single_variable(self, db, test_user):
        """Test extracting a single variable"""
        service = PromptService(db)
        variables = service.extract_variables("Hello {name}!")
        assert variables == ["name"]

    def test_extract_multiple_variables(self, db, test_user):
        """Test extracting multiple variables"""
        service = PromptService(db)
        variables = service.extract_variables("Hello {name}, you are {age} years old.")
        assert variables == ["name", "age"]

    def test_extract_duplicate_variables(self, db, test_user):
        """Test that duplicate variables are returned only once"""
        service = PromptService(db)
        variables = service.extract_variables("{name} says hello to {name}")
        assert variables == ["name"]

    def test_extract_no_variables(self, db, test_user):
        """Test template with no variables"""
        service = PromptService(db)
        variables = service.extract_variables("No variables here")
        assert variables == []

    def test_extract_underscore_variables(self, db, test_user):
        """Test variables with underscores"""
        service = PromptService(db)
        variables = service.extract_variables("{user_name} has {total_items} items")
        assert variables == ["user_name", "total_items"]

    def test_extract_numeric_suffix_variables(self, db, test_user):
        """Test variables with numeric suffixes"""
        service = PromptService(db)
        variables = service.extract_variables("{var1} and {var2}")
        assert variables == ["var1", "var2"]

    def test_invalid_variable_patterns_ignored(self, db, test_user):
        """Test that invalid patterns like {123} are ignored"""
        service = PromptService(db)
        variables = service.extract_variables("{123} and {valid_var}")
        assert variables == ["valid_var"]


class TestPromptServiceVariableSubstitution:
    """Test cases for variable substitution"""

    def test_substitute_single_variable(self, db, test_user):
        """Test substituting a single variable"""
        service = PromptService(db)
        result = service.substitute_variables(
            "Hello {name}!",
            {"name": "World"}
        )
        assert result == "Hello World!"

    def test_substitute_multiple_variables(self, db, test_user):
        """Test substituting multiple variables"""
        service = PromptService(db)
        result = service.substitute_variables(
            "{greeting} {name}!",
            {"greeting": "Hello", "name": "World"}
        )
        assert result == "Hello World!"

    def test_substitute_duplicate_occurrences(self, db, test_user):
        """Test substituting a variable that appears multiple times"""
        service = PromptService(db)
        result = service.substitute_variables(
            "{name} greets {name}",
            {"name": "Alice"}
        )
        assert result == "Alice greets Alice"

    def test_substitute_missing_variable_non_strict(self, db, test_user):
        """Test that missing variables are kept as-is in non-strict mode"""
        service = PromptService(db)
        result = service.substitute_variables(
            "Hello {name}, you have {count} messages",
            {"name": "Alice"},
            strict=False
        )
        assert result == "Hello Alice, you have {count} messages"

    def test_substitute_missing_variable_strict(self, db, test_user):
        """Test that missing variables raise error in strict mode"""
        service = PromptService(db)
        with pytest.raises(PromptVariableError) as exc_info:
            service.substitute_variables(
                "Hello {name}, you have {count} messages",
                {"name": "Alice"},
                strict=True
            )
        assert "count" in str(exc_info.value)

    def test_substitute_extra_variables_ignored(self, db, test_user):
        """Test that extra variables are ignored"""
        service = PromptService(db)
        result = service.substitute_variables(
            "Hello {name}!",
            {"name": "World", "extra": "ignored"}
        )
        assert result == "Hello World!"

    def test_substitute_empty_values(self, db, test_user):
        """Test substituting with empty string values"""
        service = PromptService(db)
        result = service.substitute_variables(
            "Hello {name}!",
            {"name": ""}
        )
        assert result == "Hello !"

    def test_substitute_numeric_values(self, db, test_user):
        """Test substituting with numeric values"""
        service = PromptService(db)
        result = service.substitute_variables(
            "Count: {count}",
            {"count": "42"}
        )
        assert result == "Count: 42"


class TestPromptServiceResolve:
    """Test cases for prompt resolution"""

    @pytest.fixture
    def test_prompt_with_version(self, db, test_user):
        """Create a test prompt with version"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Test Prompt",
            use_case=PromptUseCase.CODING
        )
        db.add(prompt)
        db.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Write a {language} function to {task}",
            variables=["language", "task"],
            message_type=MessageType.USER,
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

    def test_resolve_prompt_with_variables(self, db, test_user, test_prompt_with_version):
        """Test resolving a prompt with variable substitution"""
        prompt, version = test_prompt_with_version
        service = PromptService(db)

        result = service.resolve_prompt(
            prompt_id=prompt.id,
            variables={"language": "Python", "task": "sort a list"},
            user_id=test_user.id
        )

        assert isinstance(result, PromptResolutionResult)
        assert result.rendered == "Write a Python function to sort a list"
        assert result.version_id == version.id
        assert result.prompt_id == prompt.id

    def test_resolve_prompt_without_variables(self, db, test_user, test_prompt_with_version):
        """Test resolving a prompt without providing variables"""
        prompt, version = test_prompt_with_version
        service = PromptService(db)

        result = service.resolve_prompt(
            prompt_id=prompt.id,
            variables={},
            user_id=test_user.id
        )

        # Variables should remain unsubstituted
        assert "{language}" in result.rendered
        assert "{task}" in result.rendered

    def test_resolve_prompt_increments_usage(self, db, test_user, test_prompt_with_version):
        """Test that resolving increments usage count"""
        prompt, version = test_prompt_with_version
        service = PromptService(db)

        initial_count = version.usage_count

        service.resolve_prompt(
            prompt_id=prompt.id,
            variables={},
            user_id=test_user.id,
            increment_usage=True
        )

        db.refresh(version)
        assert version.usage_count == initial_count + 1

    def test_resolve_prompt_skip_usage_increment(self, db, test_user, test_prompt_with_version):
        """Test resolving without incrementing usage"""
        prompt, version = test_prompt_with_version
        service = PromptService(db)

        initial_count = version.usage_count

        service.resolve_prompt(
            prompt_id=prompt.id,
            variables={},
            user_id=test_user.id,
            increment_usage=False
        )

        db.refresh(version)
        assert version.usage_count == initial_count

    def test_resolve_prompt_not_found(self, db, test_user):
        """Test resolving non-existent prompt raises error"""
        service = PromptService(db)

        with pytest.raises(PromptNotFoundError):
            service.resolve_prompt(
                prompt_id=99999,
                variables={},
                user_id=test_user.id
            )

    def test_resolve_prompt_access_control(self, db, test_user, second_test_user, test_prompt_with_version):
        """Test that users cannot resolve other users' prompts"""
        prompt, _ = test_prompt_with_version
        service = PromptService(db)

        with pytest.raises(PromptNotFoundError):
            service.resolve_prompt(
                prompt_id=prompt.id,
                variables={},
                user_id=second_test_user.id
            )

    def test_resolve_prompt_inactive(self, db, test_user):
        """Test resolving inactive prompt raises error"""
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

    def test_resolve_specific_version(self, db, test_user):
        """Test resolving a specific version of a prompt"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Multi-Version Prompt"
        )
        db.add(prompt)
        db.flush()

        version1 = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Version 1: {var}",
            variables=["var"],
            is_active=True,
            created_by=test_user.id
        )
        version2 = PromptVersion(
            prompt_id=prompt.id,
            version_number=2,
            template="Version 2: {var}",
            variables=["var"],
            is_active=True,
            created_by=test_user.id
        )
        db.add(version1)
        db.add(version2)
        db.flush()

        prompt.current_version_id = version2.id
        db.commit()
        db.refresh(prompt)

        service = PromptService(db)

        # Resolve specific version 1
        result = service.resolve_prompt(
            prompt_id=prompt.id,
            variables={"var": "test"},
            version_id=version1.id,
            user_id=test_user.id
        )

        assert result.rendered == "Version 1: test"
        assert result.version_id == version1.id


class TestPromptServiceGetInfo:
    """Test cases for get_prompt_info method"""

    def test_get_prompt_info(self, db, test_user):
        """Test getting prompt information"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Info Test Prompt",
            description="A test prompt",
            use_case=PromptUseCase.ANALYSIS
        )
        db.add(prompt)
        db.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Analyze {topic} in detail",
            variables=["topic"],
            message_type=MessageType.USER,
            is_active=True,
            created_by=test_user.id
        )
        db.add(version)
        db.flush()

        prompt.current_version_id = version.id
        db.commit()
        db.refresh(prompt)

        service = PromptService(db)
        info = service.get_prompt_info(prompt.id, test_user.id)

        assert info["id"] == prompt.id
        assert info["name"] == "Info Test Prompt"
        assert info["description"] == "A test prompt"
        assert info["use_case"] == "analysis"
        assert info["message_type"] == "user"
        assert info["template"] == "Analyze {topic} in detail"
        assert info["variables"] == ["topic"]
        assert info["version_id"] == version.id
        assert info["version_number"] == 1


class TestPromptServiceUsageTracking:
    """Test cases for usage tracking"""

    def test_multiple_usage_increments(self, db, test_user):
        """Test that multiple resolutions increment usage correctly"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Usage Test"
        )
        db.add(prompt)
        db.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Test template",
            variables=[],
            is_active=True,
            usage_count=0,
            created_by=test_user.id
        )
        db.add(version)
        db.flush()

        prompt.current_version_id = version.id
        db.commit()

        service = PromptService(db)

        # Resolve 5 times
        for _ in range(5):
            service.resolve_prompt(
                prompt_id=prompt.id,
                variables={},
                user_id=test_user.id,
                increment_usage=True
            )

        db.refresh(version)
        assert version.usage_count == 5
