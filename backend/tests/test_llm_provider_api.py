"""
Tests for LLM Provider Configuration API endpoints.

These tests verify the provider management API works correctly with mocked LLM clients.
"""
import pytest
from fastapi import status
from unittest.mock import AsyncMock, patch

from app.models.llm_provider import LLMProviderConfig, LLMProviderType
from app.encryption import encrypt_api_key, decrypt_api_key
from app.llm.base import LLMResponse


@pytest.fixture
def openai_provider_data():
    """Valid OpenAI provider configuration data"""
    return {
        "provider_type": "openai",
        "name": "My OpenAI Config",
        "description": "OpenAI for production",
        "api_key": "sk-test1234567890abcdef",
        "config": {
            "organization_id": "org-123",
            "default_model": "gpt-4",
            "timeout": 60
        }
    }


@pytest.fixture
def anthropic_provider_data():
    """Valid Anthropic provider configuration data"""
    return {
        "provider_type": "anthropic",
        "name": "My Anthropic Config",
        "description": "Anthropic for testing",
        "api_key": "sk-ant-test1234567890abcdef",
        "config": {
            "default_model": "claude-3-5-sonnet-20241022",
            "timeout": 60
        }
    }


class TestCreateProviderConfig:
    """Test cases for POST /api/v1/llm-providers"""

    def test_create_openai_provider_success(self, client, auth_headers, openai_provider_data):
        """Test successful creation of OpenAI provider configuration"""
        response = client.post(
            "/api/v1/llm-providers",
            json=openai_provider_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "My OpenAI Config"
        assert data["provider_type"] == "openai"
        assert data["description"] == "OpenAI for production"
        assert data["is_active"] is True
        assert data["has_api_key"] is True
        assert "api_key" not in data  # API key should NEVER be in response
        assert "encrypted_api_key" not in data
        assert data["config"]["default_model"] == "gpt-4"

    def test_create_anthropic_provider_success(self, client, auth_headers, anthropic_provider_data):
        """Test successful creation of Anthropic provider configuration"""
        response = client.post(
            "/api/v1/llm-providers",
            json=anthropic_provider_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "My Anthropic Config"
        assert data["provider_type"] == "anthropic"
        assert data["has_api_key"] is True
        assert "api_key" not in data

    def test_create_provider_minimal(self, client, auth_headers):
        """Test creating provider with minimal required fields"""
        provider_data = {
            "provider_type": "openai",
            "name": "Minimal Config",
            "api_key": "sk-test123"
        }

        response = client.post(
            "/api/v1/llm-providers",
            json=provider_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Minimal Config"
        assert data["description"] is None
        assert data["config"] == {}

    def test_create_provider_unauthorized(self, client, openai_provider_data):
        """Test creating provider without authentication"""
        response = client.post("/api/v1/llm-providers", json=openai_provider_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_provider_invalid_type(self, client, auth_headers):
        """Test creating provider with invalid provider type"""
        provider_data = {
            "provider_type": "invalid_provider",
            "name": "Invalid",
            "api_key": "sk-test123"
        }

        response = client.post(
            "/api/v1/llm-providers",
            json=provider_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_api_key_is_encrypted(self, client, auth_headers, db, test_user, openai_provider_data):
        """Test that API key is encrypted in database"""
        response = client.post(
            "/api/v1/llm-providers",
            json=openai_provider_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        provider_id = response.json()["id"]

        # Check database directly
        provider = db.query(LLMProviderConfig).filter(
            LLMProviderConfig.id == provider_id
        ).first()

        assert provider is not None
        assert provider.encrypted_api_key != openai_provider_data["api_key"]

        # Verify we can decrypt it back
        decrypted = decrypt_api_key(provider.encrypted_api_key)
        assert decrypted == openai_provider_data["api_key"]


class TestListProviderConfigs:
    """Test cases for GET /api/v1/llm-providers"""

    @pytest.fixture
    def sample_providers(self, db, test_user):
        """Create sample provider configurations"""
        providers = [
            LLMProviderConfig(
                user_id=test_user.id,
                provider_type=LLMProviderType.OPENAI,
                name="OpenAI Primary",
                encrypted_api_key=encrypt_api_key("sk-test1"),
                config={"default_model": "gpt-4"},
                is_active=True
            ),
            LLMProviderConfig(
                user_id=test_user.id,
                provider_type=LLMProviderType.ANTHROPIC,
                name="Anthropic Dev",
                encrypted_api_key=encrypt_api_key("sk-ant-test1"),
                config={"default_model": "claude-3-5-sonnet-20241022"},
                is_active=True
            ),
            LLMProviderConfig(
                user_id=test_user.id,
                provider_type=LLMProviderType.OPENAI,
                name="OpenAI Inactive",
                encrypted_api_key=encrypt_api_key("sk-test2"),
                config={},
                is_active=False
            ),
        ]

        for provider in providers:
            db.add(provider)
        db.commit()

        return providers

    def test_list_providers_success(self, client, auth_headers, sample_providers):
        """Test successful listing of provider configurations"""
        response = client.get("/api/v1/llm-providers", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3
        assert len(data["providers"]) == 3

        # Verify no API keys in response
        for provider in data["providers"]:
            assert "api_key" not in provider
            assert "encrypted_api_key" not in provider
            assert provider["has_api_key"] is True

    def test_list_providers_active_only(self, client, auth_headers, sample_providers):
        """Test listing only active providers"""
        response = client.get(
            "/api/v1/llm-providers?active_only=true",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert all(p["is_active"] for p in data["providers"])

    def test_list_providers_pagination(self, client, auth_headers, sample_providers):
        """Test pagination of provider list"""
        response = client.get(
            "/api/v1/llm-providers?skip=0&limit=2",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["providers"]) == 2
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_list_providers_empty(self, client, auth_headers):
        """Test listing when user has no providers"""
        response = client.get("/api/v1/llm-providers", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["providers"]) == 0

    def test_list_providers_unauthorized(self, client):
        """Test listing without authentication"""
        response = client.get("/api/v1/llm-providers")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_providers_user_isolation(self, client, auth_headers, second_test_user, db):
        """Test that users can only see their own providers"""
        # Create provider for second user
        provider = LLMProviderConfig(
            user_id=second_test_user.id,
            provider_type=LLMProviderType.OPENAI,
            name="Other User's Provider",
            encrypted_api_key=encrypt_api_key("sk-other"),
            config={}
        )
        db.add(provider)
        db.commit()

        # First user should not see second user's provider
        response = client.get("/api/v1/llm-providers", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0


class TestGetProviderConfig:
    """Test cases for GET /api/v1/llm-providers/{provider_id}"""

    @pytest.fixture
    def test_provider(self, db, test_user):
        """Create a test provider configuration"""
        provider = LLMProviderConfig(
            user_id=test_user.id,
            provider_type=LLMProviderType.OPENAI,
            name="Test Provider",
            description="For testing",
            encrypted_api_key=encrypt_api_key("sk-test123"),
            config={"default_model": "gpt-4"}
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)
        return provider

    def test_get_provider_success(self, client, auth_headers, test_provider):
        """Test successful retrieval of provider configuration"""
        response = client.get(
            f"/api/v1/llm-providers/{test_provider.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_provider.id
        assert data["name"] == "Test Provider"
        assert data["provider_type"] == "openai"
        assert "api_key" not in data
        assert data["has_api_key"] is True

    def test_get_provider_not_found(self, client, auth_headers):
        """Test getting non-existent provider"""
        response = client.get("/api/v1/llm-providers/99999", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_provider_unauthorized(self, client, test_provider):
        """Test getting provider without authentication"""
        response = client.get(f"/api/v1/llm-providers/{test_provider.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_provider_wrong_user(self, client, auth_headers, second_test_user, db):
        """Test that users cannot access other users' providers"""
        # Create provider for second user
        provider = LLMProviderConfig(
            user_id=second_test_user.id,
            provider_type=LLMProviderType.OPENAI,
            name="Other User's Provider",
            encrypted_api_key=encrypt_api_key("sk-other"),
            config={}
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)

        # First user tries to access second user's provider
        response = client.get(f"/api/v1/llm-providers/{provider.id}", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateProviderConfig:
    """Test cases for PUT /api/v1/llm-providers/{provider_id}"""

    @pytest.fixture
    def test_provider(self, db, test_user):
        """Create a test provider configuration"""
        provider = LLMProviderConfig(
            user_id=test_user.id,
            provider_type=LLMProviderType.OPENAI,
            name="Original Name",
            description="Original description",
            encrypted_api_key=encrypt_api_key("sk-original"),
            config={"default_model": "gpt-3.5-turbo"}
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)
        return provider

    def test_update_provider_success(self, client, auth_headers, test_provider, db):
        """Test successful update of provider configuration"""
        update_data = {
            "name": "Updated Name",
            "description": "Updated description",
            "config": {"default_model": "gpt-4"}
        }

        response = client.put(
            f"/api/v1/llm-providers/{test_provider.id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert data["config"]["default_model"] == "gpt-4"

        # Verify API key was NOT changed
        db.refresh(test_provider)
        decrypted = decrypt_api_key(test_provider.encrypted_api_key)
        assert decrypted == "sk-original"

    def test_update_provider_partial(self, client, auth_headers, test_provider):
        """Test partial update of provider configuration"""
        update_data = {"name": "New Name Only"}

        response = client.put(
            f"/api/v1/llm-providers/{test_provider.id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "New Name Only"
        assert data["description"] == "Original description"  # Unchanged

    def test_update_provider_deactivate(self, client, auth_headers, test_provider):
        """Test deactivating a provider"""
        update_data = {"is_active": False}

        response = client.put(
            f"/api/v1/llm-providers/{test_provider.id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is False

    def test_update_provider_not_found(self, client, auth_headers):
        """Test updating non-existent provider"""
        response = client.put(
            "/api/v1/llm-providers/99999",
            json={"name": "New Name"},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateProviderAPIKey:
    """Test cases for PUT /api/v1/llm-providers/{provider_id}/api-key"""

    @pytest.fixture
    def test_provider(self, db, test_user):
        """Create a test provider configuration"""
        provider = LLMProviderConfig(
            user_id=test_user.id,
            provider_type=LLMProviderType.OPENAI,
            name="Test Provider",
            encrypted_api_key=encrypt_api_key("sk-old-key"),
            config={}
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)
        return provider

    def test_update_api_key_success(self, client, auth_headers, test_provider, db):
        """Test successful update of API key"""
        new_key_data = {"api_key": "sk-new-key-12345"}

        response = client.put(
            f"/api/v1/llm-providers/{test_provider.id}/api-key",
            json=new_key_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "api_key" not in data  # Should not return the key
        assert data["has_api_key"] is True

        # Verify key was updated in database
        db.refresh(test_provider)
        decrypted = decrypt_api_key(test_provider.encrypted_api_key)
        assert decrypted == "sk-new-key-12345"

    def test_update_api_key_not_found(self, client, auth_headers):
        """Test updating API key for non-existent provider"""
        response = client.put(
            "/api/v1/llm-providers/99999/api-key",
            json={"api_key": "sk-new"},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteProviderConfig:
    """Test cases for DELETE /api/v1/llm-providers/{provider_id}"""

    @pytest.fixture
    def test_provider(self, db, test_user):
        """Create a test provider configuration"""
        provider = LLMProviderConfig(
            user_id=test_user.id,
            provider_type=LLMProviderType.OPENAI,
            name="Test Provider",
            encrypted_api_key=encrypt_api_key("sk-test"),
            config={}
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)
        return provider

    def test_delete_provider_success(self, client, auth_headers, test_provider, db):
        """Test successful deletion of provider configuration"""
        response = client.delete(
            f"/api/v1/llm-providers/{test_provider.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify provider is deleted from database
        provider = db.query(LLMProviderConfig).filter(
            LLMProviderConfig.id == test_provider.id
        ).first()
        assert provider is None

    def test_delete_provider_not_found(self, client, auth_headers):
        """Test deleting non-existent provider"""
        response = client.delete("/api/v1/llm-providers/99999", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestProviderConnectionTest:
    """Test cases for POST /api/v1/llm-providers/{provider_id}/test"""

    @pytest.fixture
    def openai_provider(self, db, test_user):
        """Create an OpenAI provider configuration"""
        provider = LLMProviderConfig(
            user_id=test_user.id,
            provider_type=LLMProviderType.OPENAI,
            name="OpenAI Test",
            encrypted_api_key=encrypt_api_key("sk-test-key"),
            config={"default_model": "gpt-4"}
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)
        return provider

    @pytest.fixture
    def anthropic_provider(self, db, test_user):
        """Create an Anthropic provider configuration"""
        provider = LLMProviderConfig(
            user_id=test_user.id,
            provider_type=LLMProviderType.ANTHROPIC,
            name="Anthropic Test",
            encrypted_api_key=encrypt_api_key("sk-ant-test-key"),
            config={"default_model": "claude-3-5-sonnet-20241022"}
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)
        return provider

    @pytest.mark.asyncio
    async def test_test_openai_connection_success(self, client, auth_headers, openai_provider):
        """Test successful OpenAI connection test"""
        mock_response = LLMResponse(
            content="Test response",
            model="gpt-4",
            finish_reason="stop",
            usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}
        )

        with patch('app.llm.openai_client.OpenAIClient.generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response

            response = client.post(
                f"/api/v1/llm-providers/{openai_provider.id}/test",
                json={"test_message": "Hello"},
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["response"] == "Test response"
            assert data["tokens_used"] == 8
            assert "latency_ms" in data

    @pytest.mark.asyncio
    async def test_test_anthropic_connection_success(self, client, auth_headers, anthropic_provider):
        """Test successful Anthropic connection test"""
        mock_response = LLMResponse(
            content="Test response from Claude",
            model="claude-3-5-sonnet-20241022",
            finish_reason="end_turn",
            usage={"prompt_tokens": 6, "completion_tokens": 4, "total_tokens": 10}
        )

        with patch('app.llm.anthropic_client.AnthropicClient.generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response

            response = client.post(
                f"/api/v1/llm-providers/{anthropic_provider.id}/test",
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["response"] == "Test response from Claude"
            assert data["tokens_used"] == 10

    def test_test_connection_not_found(self, client, auth_headers):
        """Test connection test for non-existent provider"""
        response = client.post("/api/v1/llm-providers/99999/test", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND
