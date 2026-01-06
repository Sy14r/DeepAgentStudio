"""
Tests for Prompt and PromptVersion models
"""
import pytest
from sqlalchemy.exc import IntegrityError
from app.models.prompt import Prompt, PromptVersion, MessageType, PromptUseCase
from app.models.user import User
from app.security import hash_password


class TestPromptModel:
    """Test cases for Prompt model"""

    def test_create_prompt(self, db, test_user):
        """Test creating a prompt"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Test Prompt",
            description="A test prompt",
            use_case=PromptUseCase.CODING,
            tags=["python", "testing"]
        )
        db.add(prompt)
        db.commit()
        db.refresh(prompt)

        assert prompt.id is not None
        assert prompt.name == "Test Prompt"
        assert prompt.use_case == PromptUseCase.CODING
        assert prompt.tags == ["python", "testing"]
        assert prompt.is_active is True
        assert prompt.current_version_id is None

    def test_create_prompt_minimal(self, db, test_user):
        """Test creating a prompt with minimal fields"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Minimal Prompt"
        )
        db.add(prompt)
        db.commit()
        db.refresh(prompt)

        assert prompt.id is not None
        assert prompt.description is None
        assert prompt.use_case == PromptUseCase.OTHER  # Default
        assert prompt.tags == []  # Default

    def test_prompt_without_user_fails(self, db):
        """Test that prompt without user_id fails"""
        prompt = Prompt(
            name="No User Prompt"
        )
        db.add(prompt)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_prompt_without_name_fails(self, db, test_user):
        """Test that prompt without name fails"""
        prompt = Prompt(
            user_id=test_user.id
        )
        db.add(prompt)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_prompt_use_cases(self, db, test_user):
        """Test different prompt use cases"""
        use_cases = [
            PromptUseCase.RESEARCH,
            PromptUseCase.CODING,
            PromptUseCase.ANALYSIS,
            PromptUseCase.WRITING,
            PromptUseCase.CONVERSATION,
            PromptUseCase.PLANNING,
            PromptUseCase.OTHER
        ]

        for use_case in use_cases:
            prompt = Prompt(
                user_id=test_user.id,
                name=f"Prompt {use_case.value}",
                use_case=use_case
            )
            db.add(prompt)
            db.commit()
            db.refresh(prompt)
            assert prompt.use_case == use_case

    def test_query_prompts_by_use_case(self, db, test_user):
        """Test querying prompts by use case"""
        coding_prompt = Prompt(
            user_id=test_user.id,
            name="Coding Prompt",
            use_case=PromptUseCase.CODING
        )
        writing_prompt = Prompt(
            user_id=test_user.id,
            name="Writing Prompt",
            use_case=PromptUseCase.WRITING
        )
        db.add_all([coding_prompt, writing_prompt])
        db.commit()

        coding_prompts = db.query(Prompt).filter(Prompt.use_case == PromptUseCase.CODING).all()
        assert len(coding_prompts) == 1
        assert coding_prompts[0].name == "Coding Prompt"

    def test_update_prompt(self, db, test_user):
        """Test updating prompt metadata"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Original Name",
            description="Original description"
        )
        db.add(prompt)
        db.commit()

        prompt.name = "Updated Name"
        prompt.description = "Updated description"
        prompt.tags = ["updated"]
        db.commit()
        db.refresh(prompt)

        assert prompt.name == "Updated Name"
        assert prompt.description == "Updated description"
        assert prompt.tags == ["updated"]

    def test_soft_delete_prompt(self, db, test_user):
        """Test soft deleting a prompt"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Soft Delete Test"
        )
        db.add(prompt)
        db.commit()

        prompt.is_active = False
        db.commit()
        db.refresh(prompt)

        assert prompt.is_active is False

    def test_delete_prompt(self, db, test_user):
        """Test deleting a prompt"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Delete Me"
        )
        db.add(prompt)
        db.commit()
        prompt_id = prompt.id

        db.delete(prompt)
        db.commit()

        deleted = db.query(Prompt).filter(Prompt.id == prompt_id).first()
        assert deleted is None

    def test_prompt_cascade_delete_with_user(self, db):
        """Test that deleting user cascades to prompts"""
        user = User(
            username="promptuser",
            email="prompt@example.com",
            hashed_password=hash_password("password123")
        )
        db.add(user)
        db.commit()

        prompt = Prompt(
            user_id=user.id,
            name="User Prompt"
        )
        db.add(prompt)
        db.commit()
        prompt_id = prompt.id

        db.delete(user)
        db.commit()

        deleted_prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
        assert deleted_prompt is None

    def test_prompt_repr(self, db, test_user):
        """Test prompt string representation"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Test Prompt",
            use_case=PromptUseCase.CODING
        )
        db.add(prompt)
        db.commit()

        repr_str = repr(prompt)
        assert "Prompt" in repr_str
        assert str(prompt.id) in repr_str
        assert "Test Prompt" in repr_str
        assert "coding" in repr_str


class TestPromptVersionModel:
    """Test cases for PromptVersion model"""

    def test_create_prompt_version(self, db, test_user):
        """Test creating a prompt version"""
        # Create prompt
        prompt = Prompt(
            user_id=test_user.id,
            name="Versioned Prompt"
        )
        db.add(prompt)
        db.flush()

        # Create version
        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Hello {name}, welcome to {platform}!",
            variables=["name", "platform"],
            message_type=MessageType.USER,
            created_by=test_user.id
        )
        db.add(version)
        db.commit()
        db.refresh(version)

        assert version.id is not None
        assert version.version_number == 1
        assert version.template == "Hello {name}, welcome to {platform}!"
        assert version.variables == ["name", "platform"]
        assert version.message_type == MessageType.USER
        assert version.is_active is True
        assert version.usage_count == 0

    def test_message_types(self, db, test_user):
        """Test different message types"""
        prompt = Prompt(user_id=test_user.id, name="Message Type Test")
        db.add(prompt)
        db.flush()

        message_types = [MessageType.SYSTEM, MessageType.USER, MessageType.ASSISTANT]

        for msg_type in message_types:
            version = PromptVersion(
                prompt_id=prompt.id,
                version_number=msg_type.value,  # Just for uniqueness
                template=f"Template for {msg_type.value}",
                variables=[],
                message_type=msg_type,
                created_by=test_user.id
            )
            db.add(version)
            db.commit()
            db.refresh(version)
            assert version.message_type == msg_type

    def test_multiple_versions_same_prompt(self, db, test_user):
        """Test creating multiple versions for same prompt"""
        prompt = Prompt(user_id=test_user.id, name="Multi-Version Prompt")
        db.add(prompt)
        db.flush()

        for i in range(1, 4):
            version = PromptVersion(
                prompt_id=prompt.id,
                version_number=i,
                template=f"Version {i} template",
                variables=[],
                created_by=test_user.id
            )
            db.add(version)

        db.commit()

        versions = db.query(PromptVersion).filter(
            PromptVersion.prompt_id == prompt.id
        ).order_by(PromptVersion.version_number).all()

        assert len(versions) == 3
        assert versions[0].version_number == 1
        assert versions[1].version_number == 2
        assert versions[2].version_number == 3

    def test_version_is_active_flag(self, db, test_user):
        """Test version is_active flag for A/B testing"""
        prompt = Prompt(user_id=test_user.id, name="A/B Test Prompt")
        db.add(prompt)
        db.flush()

        # Create two active versions
        version1 = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Template A",
            variables=[],
            is_active=True,
            created_by=test_user.id
        )
        version2 = PromptVersion(
            prompt_id=prompt.id,
            version_number=2,
            template="Template B",
            variables=[],
            is_active=True,
            created_by=test_user.id
        )
        db.add_all([version1, version2])
        db.commit()

        # Both should be active
        active_versions = db.query(PromptVersion).filter(
            PromptVersion.prompt_id == prompt.id,
            PromptVersion.is_active == True
        ).all()
        assert len(active_versions) == 2

    def test_version_usage_count(self, db, test_user):
        """Test incrementing usage count"""
        prompt = Prompt(user_id=test_user.id, name="Usage Test")
        db.add(prompt)
        db.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Test template",
            variables=[],
            created_by=test_user.id
        )
        db.add(version)
        db.commit()

        assert version.usage_count == 0

        # Increment usage
        version.usage_count += 1
        db.commit()
        db.refresh(version)
        assert version.usage_count == 1

    def test_version_cascade_delete_with_prompt(self, db, test_user):
        """Test that deleting prompt cascades to versions"""
        prompt = Prompt(user_id=test_user.id, name="Cascade Test")
        db.add(prompt)
        db.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Template",
            variables=[],
            created_by=test_user.id
        )
        db.add(version)
        db.commit()
        version_id = version.id

        db.delete(prompt)
        db.commit()

        deleted_version = db.query(PromptVersion).filter(PromptVersion.id == version_id).first()
        assert deleted_version is None

    def test_prompt_current_version_relationship(self, db, test_user):
        """Test setting current version"""
        prompt = Prompt(user_id=test_user.id, name="Current Version Test")
        db.add(prompt)
        db.flush()

        version1 = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Version 1",
            variables=[],
            created_by=test_user.id
        )
        db.add(version1)
        db.flush()

        # Set current version
        prompt.current_version_id = version1.id
        db.commit()
        db.refresh(prompt)

        assert prompt.current_version_id == version1.id

    def test_version_repr(self, db, test_user):
        """Test version string representation"""
        prompt = Prompt(user_id=test_user.id, name="Repr Test")
        db.add(prompt)
        db.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Test",
            variables=[],
            message_type=MessageType.SYSTEM,
            is_active=True,
            created_by=test_user.id
        )
        db.add(version)
        db.commit()

        repr_str = repr(version)
        assert "PromptVersion" in repr_str
        assert str(version.id) in repr_str
        assert "version=1" in repr_str
        assert "system" in repr_str
        assert "active=True" in repr_str
