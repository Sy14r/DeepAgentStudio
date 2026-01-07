"""
Tests for the DALL-E Image Generation Tool.

Tests cover:
- Tool creation with/without API key
- Parameter validation
- Image generation (mocked)
- Error handling
"""
import pytest
import json
from unittest.mock import patch, MagicMock
import httpx

from app.services.image_generation_tools import (
    create_image_generation_tools,
    _get_openai_api_key,
    _create_dalle_tool,
    DalleImageInput,
    is_image_generation_tool_class,
    IMAGE_GENERATION_TOOL_NAMES,
)
from app.models.session import Session
from app.models.agent import Agent
from app.models.agent_type import AgentTypeConfig, ExecutionStrategy, StrategyType
from app.models.llm_provider import LLMProviderConfig, LLMProviderType
from app.encryption import encrypt_api_key


@pytest.fixture
def test_agent_type(db, test_user):
    """Create a test agent type configuration."""
    agent_type = AgentTypeConfig(
        user_id=test_user.id,
        name="Test ReAct Type",
        description="A test agent type",
        execution_strategy=ExecutionStrategy.react,
        strategy_type=StrategyType.builtin,
        is_builtin=False,
        is_active=True,
    )
    db.add(agent_type)
    db.commit()
    db.refresh(agent_type)
    return agent_type


@pytest.fixture
def test_agent(db, test_user, test_agent_type):
    """Create a test agent."""
    agent = Agent(
        user_id=test_user.id,
        name="Test Agent",
        description="A test agent",
        agent_type_id=test_agent_type.id,
        is_active=True,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@pytest.fixture
def test_session(db, test_user, test_agent):
    """Create a test session."""
    session = Session(
        user_id=test_user.id,
        agent_id=test_agent.id,
        status="running",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def openai_provider(db, test_user):
    """Create an OpenAI provider with API key."""
    provider = LLMProviderConfig(
        user_id=test_user.id,
        provider_type=LLMProviderType.OPENAI,
        name="Test OpenAI",
        encrypted_api_key=encrypt_api_key("sk-test-key-12345"),
        is_active=True,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


class TestDalleImageInput:
    """Tests for the DALL-E input schema."""

    def test_default_values(self):
        """Test default values are set correctly."""
        input_data = DalleImageInput(prompt="A cat")
        assert input_data.prompt == "A cat"
        assert input_data.size == "1024x1024"

    def test_custom_values(self):
        """Test custom values are accepted."""
        input_data = DalleImageInput(
            prompt="A dog",
            size="512x512"
        )
        assert input_data.prompt == "A dog"
        assert input_data.size == "512x512"


class TestGetOpenAIApiKey:
    """Tests for API key retrieval."""

    def test_get_api_key_with_provider(self, db, test_user, openai_provider):
        """Test getting API key when provider exists."""
        api_key = _get_openai_api_key(db, test_user.id)
        assert api_key == "sk-test-key-12345"

    def test_get_api_key_no_provider(self, db, test_user):
        """Test getting API key when no provider exists."""
        api_key = _get_openai_api_key(db, test_user.id)
        assert api_key is None

    def test_get_api_key_inactive_provider(self, db, test_user):
        """Test that inactive providers are not used."""
        provider = LLMProviderConfig(
            user_id=test_user.id,
            provider_type=LLMProviderType.OPENAI,
            name="Inactive OpenAI",
            encrypted_api_key=encrypt_api_key("sk-inactive-key"),
            is_active=False,  # Inactive
        )
        db.add(provider)
        db.commit()

        api_key = _get_openai_api_key(db, test_user.id)
        assert api_key is None

    def test_get_api_key_wrong_provider_type(self, db, test_user):
        """Test that non-OpenAI providers are not used."""
        provider = LLMProviderConfig(
            user_id=test_user.id,
            provider_type=LLMProviderType.ANTHROPIC,  # Not OpenAI
            name="Anthropic Provider",
            encrypted_api_key=encrypt_api_key("sk-ant-key"),
            is_active=True,
        )
        db.add(provider)
        db.commit()

        api_key = _get_openai_api_key(db, test_user.id)
        assert api_key is None


class TestCreateDalleTool:
    """Tests for DALL-E tool creation."""

    def test_create_tool_with_api_key(self, db, test_user, test_session, openai_provider):
        """Test tool is created when API key exists."""
        tool = _create_dalle_tool(db, test_session.id, test_user.id)

        assert tool is not None
        assert tool.name == "generate_image"
        assert "DALL-E" in tool.description

    def test_create_tool_without_api_key(self, db, test_user, test_session):
        """Test tool is not created without API key."""
        tool = _create_dalle_tool(db, test_session.id, test_user.id)
        assert tool is None

    def test_create_image_generation_tools(self, db, test_user, test_session, openai_provider):
        """Test the main tool creation function."""
        tools = create_image_generation_tools(db, test_session.id, test_user.id)

        assert len(tools) == 1
        assert tools[0].name == "generate_image"

    def test_create_image_generation_tools_empty(self, db, test_user, test_session):
        """Test returns empty list without API key."""
        tools = create_image_generation_tools(db, test_session.id, test_user.id)
        assert tools == []


class TestGenerateImageFunction:
    """Tests for the image generation function."""

    @patch('app.services.image_generation_tools.httpx.Client')
    @patch('app.services.media_storage.Path.mkdir')
    @patch('app.services.media_storage.Path.write_bytes')
    def test_generate_image_success(
        self, mock_write, mock_mkdir, mock_httpx,
        db, test_user, test_session, openai_provider
    ):
        """Test successful image generation."""
        # Mock DALL-E API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{
                "b64_json": "aW1hZ2VkYXRh",  # base64 of "imagedata"
                "revised_prompt": "A beautiful cat"
            }]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.return_value = mock_client

        # Create tool and call it
        tool = _create_dalle_tool(db, test_session.id, test_user.id)
        result = tool.func(prompt="A cat", size="1024x1024")

        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "image" in result_data
        assert "content_block" in result_data
        assert result_data["content_block"]["type"] == "image"

    @patch('app.services.image_generation_tools.httpx.Client')
    def test_generate_image_invalid_size(
        self, mock_httpx,
        db, test_user, test_session, openai_provider
    ):
        """Test error handling for invalid size parameter."""
        tool = _create_dalle_tool(db, test_session.id, test_user.id)
        result = tool.func(prompt="A cat", size="999x999")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Invalid size" in result_data["error"]

    @patch('app.services.image_generation_tools.httpx.Client')
    def test_generate_image_invalid_size_dalle3_format(
        self, mock_httpx,
        db, test_user, test_session, openai_provider
    ):
        """Test that DALL-E 3 sizes are rejected (DALL-E 2 only supports square sizes)."""
        tool = _create_dalle_tool(db, test_session.id, test_user.id)
        result = tool.func(prompt="A cat", size="1792x1024")  # DALL-E 3 landscape size

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Invalid size" in result_data["error"]

    @patch('app.services.image_generation_tools.httpx.Client')
    def test_generate_image_api_error(
        self, mock_httpx,
        db, test_user, test_session, openai_provider
    ):
        """Test handling of API errors."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": {"message": "Rate limit exceeded"}
        }
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=mock_response
        )

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.return_value = mock_client

        tool = _create_dalle_tool(db, test_session.id, test_user.id)
        result = tool.func(prompt="A cat")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "DALL-E API error" in result_data["error"]

    @patch('app.services.image_generation_tools.httpx.Client')
    def test_generate_image_timeout(
        self, mock_httpx,
        db, test_user, test_session, openai_provider
    ):
        """Test handling of timeout errors."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.TimeoutException("Timeout")
        mock_httpx.return_value = mock_client

        tool = _create_dalle_tool(db, test_session.id, test_user.id)
        result = tool.func(prompt="A cat")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "timed out" in result_data["error"]

    @patch('app.services.image_generation_tools.httpx.Client')
    def test_generate_image_no_data_in_response(
        self, mock_httpx,
        db, test_user, test_session, openai_provider
    ):
        """Test handling when API returns no image data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{}]}  # Empty data
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.return_value = mock_client

        tool = _create_dalle_tool(db, test_session.id, test_user.id)
        result = tool.func(prompt="A cat")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "No image data" in result_data["error"]


class TestImageGenerationToolIdentifiers:
    """Tests for tool identification helpers."""

    def test_is_image_generation_tool_class(self):
        """Test identification of image generation tool classes."""
        assert is_image_generation_tool_class("DalleImageGeneration") is True
        assert is_image_generation_tool_class("SomethingElse") is False
        assert is_image_generation_tool_class("generate_image") is False

    def test_tool_names(self):
        """Test tool names list."""
        assert "generate_image" in IMAGE_GENERATION_TOOL_NAMES
