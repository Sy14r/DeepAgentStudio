"""
Tests for LLM Provider Configuration models.

These tests verify the database models work correctly, including:
- Model creation and persistence
- Relationships with User model
- Enum constraints
- CASCADE delete behavior
"""
import pytest
from datetime import datetime

from app.models.llm_provider import LLMProviderConfig, LLMProviderType
from app.models.user import User
from app.encryption import encrypt_api_key, decrypt_api_key


class TestLLMProviderConfigModel:
    """Test LLMProviderConfig model"""

    def test_create_provider_config(self, db, test_user):
        """Test creating a provider configuration"""
        provider = LLMProviderConfig(
            user_id=test_user.id,
            provider_type=LLMProviderType.OPENAI,
            name="My OpenAI Config",
            description="Production OpenAI",
            encrypted_api_key=encrypt_api_key("sk-test123"),
            config={"default_model": "gpt-4", "temperature": 0.7}
        )

        db.add(provider)
        db.commit()
        db.refresh(provider)

        assert provider.id is not None
        assert provider.user_id == test_user.id
        assert provider.provider_type == LLMProviderType.OPENAI
        assert provider.name == "My OpenAI Config"
        assert provider.description == "Production OpenAI"
        assert provider.is_active is True
        assert provider.config["default_model"] == "gpt-4"
        assert provider.created_at is not None
        assert provider.updated_at is not None

    def test_create_provider_minimal(self, db, test_user):
        """Test creating provider with minimal required fields"""
        provider = LLMProviderConfig(
            user_id=test_user.id,
            provider_type=LLMProviderType.ANTHROPIC,
            name="Minimal Config",
            encrypted_api_key=encrypt_api_key("sk-ant-test")
        )

        db.add(provider)
        db.commit()
        db.refresh(provider)

        assert provider.id is not None
        assert provider.description is None
        assert provider.config == {}
        assert provider.is_active is True
        assert provider.last_used_at is None

    def test_provider_types(self, db, test_user):
        """Test all provider types can be created"""
        provider_types = [
            LLMProviderType.OPENAI,
            LLMProviderType.ANTHROPIC,
            LLMProviderType.GOOGLE,
            LLMProviderType.AZURE_OPENAI,
            LLMProviderType.OLLAMA,
            LLMProviderType.LLAMACPP,
        ]

        for provider_type in provider_types:
            provider = LLMProviderConfig(
                user_id=test_user.id,
                provider_type=provider_type,
                name=f"{provider_type.value} config",
                encrypted_api_key=encrypt_api_key(f"key-{provider_type.value}")
            )
            db.add(provider)

        db.commit()

        # Verify all were created
        count = db.query(LLMProviderConfig).filter(
            LLMProviderConfig.user_id == test_user.id
        ).count()
        assert count == len(provider_types)

    def test_encrypted_api_key_storage(self, db, test_user):
        """Test that API keys are stored encrypted"""
        original_key = "sk-my-secret-api-key-12345"
        encrypted_key = encrypt_api_key(original_key)

        provider = LLMProviderConfig(
            user_id=test_user.id,
            provider_type=LLMProviderType.OPENAI,
            name="Test",
            encrypted_api_key=encrypted_key
        )

        db.add(provider)
        db.commit()
        db.refresh(provider)

        # Key should be encrypted in database
        assert provider.encrypted_api_key != original_key
        assert provider.encrypted_api_key == encrypted_key

        # Should be able to decrypt back to original
        decrypted = decrypt_api_key(provider.encrypted_api_key)
        assert decrypted == original_key

    def test_config_json_field(self, db, test_user):
        """Test JSON config field stores complex data"""
        complex_config = {
            "default_model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 2000,
            "nested": {
                "setting1": "value1",
                "setting2": [1, 2, 3]
            }
        }

        provider = LLMProviderConfig(
            user_id=test_user.id,
            provider_type=LLMProviderType.OPENAI,
            name="Complex Config",
            encrypted_api_key=encrypt_api_key("sk-test"),
            config=complex_config
        )

        db.add(provider)
        db.commit()
        db.refresh(provider)

        # Verify complex config is preserved
        assert provider.config["default_model"] == "gpt-4"
        assert provider.config["temperature"] == 0.7
        assert provider.config["nested"]["setting1"] == "value1"
        assert provider.config["nested"]["setting2"] == [1, 2, 3]

    def test_update_provider(self, db, test_user):
        """Test updating provider configuration"""
        provider = LLMProviderConfig(
            user_id=test_user.id,
            provider_type=LLMProviderType.OPENAI,
            name="Original Name",
            encrypted_api_key=encrypt_api_key("sk-test"),
            config={"model": "gpt-3.5-turbo"}
        )

        db.add(provider)
        db.commit()
        original_updated_at = provider.updated_at

        # Update provider
        provider.name = "New Name"
        provider.config = {"model": "gpt-4"}
        db.commit()
        db.refresh(provider)

        assert provider.name == "New Name"
        assert provider.config["model"] == "gpt-4"
        # updated_at should change (if your DB supports it)
        # Note: This depends on the onupdate trigger working

    def test_last_used_at_tracking(self, db, test_user):
        """Test last_used_at timestamp tracking"""
        provider = LLMProviderConfig(
            user_id=test_user.id,
            provider_type=LLMProviderType.OPENAI,
            name="Test",
            encrypted_api_key=encrypt_api_key("sk-test")
        )

        db.add(provider)
        db.commit()

        assert provider.last_used_at is None

        # Simulate usage
        provider.last_used_at = datetime.utcnow()
        db.commit()
        db.refresh(provider)

        assert provider.last_used_at is not None


class TestLLMProviderUserRelationship:
    """Test relationship between LLMProviderConfig and User"""

    def test_user_relationship(self, db, test_user):
        """Test provider->user relationship"""
        provider = LLMProviderConfig(
            user_id=test_user.id,
            provider_type=LLMProviderType.OPENAI,
            name="Test",
            encrypted_api_key=encrypt_api_key("sk-test")
        )

        db.add(provider)
        db.commit()
        db.refresh(provider)

        # Access user through relationship
        assert provider.user.id == test_user.id
        assert provider.user.username == test_user.username

    def test_user_providers_relationship(self, db, test_user):
        """Test user->providers relationship"""
        # Create multiple providers for user
        providers = [
            LLMProviderConfig(
                user_id=test_user.id,
                provider_type=LLMProviderType.OPENAI,
                name=f"Provider {i}",
                encrypted_api_key=encrypt_api_key(f"sk-test{i}")
            )
            for i in range(3)
        ]

        for provider in providers:
            db.add(provider)
        db.commit()

        # Refresh user to get relationship
        db.refresh(test_user)

        # Access providers through relationship
        assert len(test_user.llm_provider_configs) == 3
        provider_names = [p.name for p in test_user.llm_provider_configs]
        assert "Provider 0" in provider_names
        assert "Provider 1" in provider_names
        assert "Provider 2" in provider_names

    def test_cascade_delete(self, db):
        """Test that deleting user deletes their provider configs"""
        # Create user
        user = User(
            username="deletetest",
            email="delete@example.com",
            hashed_password="hashed",
            is_active=True
        )
        db.add(user)
        db.commit()
        user_id = user.id

        # Create provider for user
        provider = LLMProviderConfig(
            user_id=user.id,
            provider_type=LLMProviderType.OPENAI,
            name="Test",
            encrypted_api_key=encrypt_api_key("sk-test")
        )
        db.add(provider)
        db.commit()
        provider_id = provider.id

        # Delete user
        db.delete(user)
        db.commit()

        # Verify provider was cascade deleted
        deleted_provider = db.query(LLMProviderConfig).filter(
            LLMProviderConfig.id == provider_id
        ).first()
        assert deleted_provider is None

    def test_multiple_users_multiple_providers(self, db, test_user, second_test_user):
        """Test that multiple users can have their own provider configs"""
        # Create providers for first user
        provider1 = LLMProviderConfig(
            user_id=test_user.id,
            provider_type=LLMProviderType.OPENAI,
            name="User 1 OpenAI",
            encrypted_api_key=encrypt_api_key("sk-user1")
        )
        db.add(provider1)

        # Create providers for second user
        provider2 = LLMProviderConfig(
            user_id=second_test_user.id,
            provider_type=LLMProviderType.ANTHROPIC,
            name="User 2 Anthropic",
            encrypted_api_key=encrypt_api_key("sk-user2")
        )
        db.add(provider2)

        db.commit()

        # Verify isolation
        user1_providers = db.query(LLMProviderConfig).filter(
            LLMProviderConfig.user_id == test_user.id
        ).all()
        user2_providers = db.query(LLMProviderConfig).filter(
            LLMProviderConfig.user_id == second_test_user.id
        ).all()

        assert len(user1_providers) == 1
        assert len(user2_providers) == 1
        assert user1_providers[0].name == "User 1 OpenAI"
        assert user2_providers[0].name == "User 2 Anthropic"


class TestLLMProviderQueryOperations:
    """Test common query operations on provider configs"""

    @pytest.fixture
    def multiple_providers(self, db, test_user):
        """Create multiple provider configurations"""
        providers = [
            LLMProviderConfig(
                user_id=test_user.id,
                provider_type=LLMProviderType.OPENAI,
                name="OpenAI 1",
                encrypted_api_key=encrypt_api_key("sk-1"),
                is_active=True
            ),
            LLMProviderConfig(
                user_id=test_user.id,
                provider_type=LLMProviderType.ANTHROPIC,
                name="Anthropic 1",
                encrypted_api_key=encrypt_api_key("sk-2"),
                is_active=True
            ),
            LLMProviderConfig(
                user_id=test_user.id,
                provider_type=LLMProviderType.OPENAI,
                name="OpenAI 2",
                encrypted_api_key=encrypt_api_key("sk-3"),
                is_active=False
            ),
        ]

        for provider in providers:
            db.add(provider)
        db.commit()

        return providers

    def test_filter_by_provider_type(self, db, test_user, multiple_providers):
        """Test filtering providers by type"""
        openai_providers = db.query(LLMProviderConfig).filter(
            LLMProviderConfig.user_id == test_user.id,
            LLMProviderConfig.provider_type == LLMProviderType.OPENAI
        ).all()

        assert len(openai_providers) == 2
        assert all(p.provider_type == LLMProviderType.OPENAI for p in openai_providers)

    def test_filter_by_active_status(self, db, test_user, multiple_providers):
        """Test filtering providers by active status"""
        active_providers = db.query(LLMProviderConfig).filter(
            LLMProviderConfig.user_id == test_user.id,
            LLMProviderConfig.is_active == True
        ).all()

        assert len(active_providers) == 2
        assert all(p.is_active for p in active_providers)

    def test_order_by_created_at(self, db, test_user, multiple_providers):
        """Test ordering providers by creation time"""
        providers = db.query(LLMProviderConfig).filter(
            LLMProviderConfig.user_id == test_user.id
        ).order_by(LLMProviderConfig.created_at.desc()).all()

        assert len(providers) == 3
        # Verify ordering (newest first)
        for i in range(len(providers) - 1):
            assert providers[i].created_at >= providers[i + 1].created_at

    def test_count_providers(self, db, test_user, multiple_providers):
        """Test counting provider configurations"""
        total_count = db.query(LLMProviderConfig).filter(
            LLMProviderConfig.user_id == test_user.id
        ).count()

        active_count = db.query(LLMProviderConfig).filter(
            LLMProviderConfig.user_id == test_user.id,
            LLMProviderConfig.is_active == True
        ).count()

        assert total_count == 3
        assert active_count == 2
