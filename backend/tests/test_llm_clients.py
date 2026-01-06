"""
Tests for LLM client implementations with mocked API responses.

These tests verify the LLM clients work correctly without making real API calls.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from app.llm.base import (
    LLMMessage,
    LLMResponse,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMInvalidRequestError,
    LLMConnectionError,
)
from app.llm.openai_client import OpenAIClient, create_openai_client
from app.llm.anthropic_client import AnthropicClient, create_anthropic_client


class TestOpenAIClient:
    """Test OpenAI client with mocked responses"""

    @pytest.fixture
    def openai_client(self):
        """Create an OpenAI client for testing"""
        return OpenAIClient(
            api_key="test-api-key",
            config={"default_model": "gpt-4", "timeout": 60}
        )

    @pytest.mark.asyncio
    async def test_generate_success(self, openai_client):
        """Test successful completion generation"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-4",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you today?"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 9,
                "completion_tokens": 12,
                "total_tokens": 21
            }
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            messages = [LLMMessage(role="user", content="Hello")]
            result = await openai_client.generate(messages=messages)

            assert isinstance(result, LLMResponse)
            assert result.content == "Hello! How can I help you today?"
            assert result.model == "gpt-4"
            assert result.finish_reason == "stop"
            assert result.usage["total_tokens"] == 21
            assert result.usage["prompt_tokens"] == 9
            assert result.usage["completion_tokens"] == 12

    @pytest.mark.asyncio
    async def test_generate_with_parameters(self, openai_client):
        """Test generation with custom parameters"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "gpt-4",
            "choices": [{
                "message": {"content": "Response"},
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            messages = [LLMMessage(role="user", content="Test")]
            await openai_client.generate(
                messages=messages,
                model="gpt-3.5-turbo",
                temperature=0.8,
                max_tokens=100
            )

            # Verify the request payload
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["model"] == "gpt-3.5-turbo"
            assert payload["temperature"] == 0.8
            assert payload["max_tokens"] == 100

    @pytest.mark.asyncio
    async def test_generate_authentication_error(self, openai_client):
        """Test handling of authentication errors (401)"""
        mock_response = Mock()
        mock_response.status_code = 401

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            messages = [LLMMessage(role="user", content="Hello")]

            with pytest.raises(LLMAuthenticationError) as exc_info:
                await openai_client.generate(messages=messages)

            assert exc_info.value.provider == "openai"
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_rate_limit_error(self, openai_client):
        """Test handling of rate limit errors (429)"""
        mock_response = Mock()
        mock_response.status_code = 429

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            messages = [LLMMessage(role="user", content="Hello")]

            with pytest.raises(LLMRateLimitError) as exc_info:
                await openai_client.generate(messages=messages)

            assert exc_info.value.provider == "openai"
            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_generate_invalid_request_error(self, openai_client):
        """Test handling of invalid request errors (400)"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.content = b'{"error": {"message": "Invalid request"}}'
        mock_response.json.return_value = {
            "error": {"message": "Invalid request"}
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            messages = [LLMMessage(role="user", content="Hello")]

            with pytest.raises(LLMInvalidRequestError) as exc_info:
                await openai_client.generate(messages=messages)

            assert exc_info.value.provider == "openai"
            assert "Invalid request" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_timeout_error(self, openai_client):
        """Test handling of timeout errors"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            messages = [LLMMessage(role="user", content="Hello")]

            with pytest.raises(LLMConnectionError) as exc_info:
                await openai_client.generate(messages=messages)

            assert exc_info.value.provider == "openai"
            assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_connection_error(self, openai_client):
        """Test handling of connection errors"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.RequestError("Connection failed")

            messages = [LLMMessage(role="user", content="Hello")]

            with pytest.raises(LLMConnectionError) as exc_info:
                await openai_client.generate(messages=messages)

            assert exc_info.value.provider == "openai"

    @pytest.mark.asyncio
    async def test_message_conversion(self, openai_client):
        """Test conversion of messages to OpenAI format"""
        messages = [
            LLMMessage(role="system", content="You are helpful"),
            LLMMessage(role="user", content="Hello"),
            LLMMessage(role="assistant", content="Hi there!"),
        ]

        converted = openai_client._convert_messages(messages)

        assert len(converted) == 3
        assert converted[0]["role"] == "system"
        assert converted[0]["content"] == "You are helpful"
        assert converted[1]["role"] == "user"
        assert converted[2]["role"] == "assistant"

    def test_get_default_model(self, openai_client):
        """Test getting default model"""
        assert openai_client.get_default_model() == "gpt-4"

    def test_create_openai_client_factory(self):
        """Test factory function for creating OpenAI client"""
        client = create_openai_client("test-key", {"default_model": "gpt-3.5-turbo"})
        assert isinstance(client, OpenAIClient)
        assert client.api_key == "test-key"
        assert client.default_model == "gpt-3.5-turbo"


class TestAnthropicClient:
    """Test Anthropic client with mocked responses"""

    @pytest.fixture
    def anthropic_client(self):
        """Create an Anthropic client for testing"""
        return AnthropicClient(
            api_key="test-api-key",
            config={"default_model": "claude-3-5-sonnet-20241022", "timeout": 60}
        )

    @pytest.mark.asyncio
    async def test_generate_success(self, anthropic_client):
        """Test successful completion generation"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "Hello! How can I help you today?"
                }
            ],
            "model": "claude-3-5-sonnet-20241022",
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 12
            }
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            messages = [LLMMessage(role="user", content="Hello")]
            result = await anthropic_client.generate(messages=messages)

            assert isinstance(result, LLMResponse)
            assert result.content == "Hello! How can I help you today?"
            assert result.model == "claude-3-5-sonnet-20241022"
            assert result.finish_reason == "end_turn"
            assert result.usage["total_tokens"] == 22
            assert result.usage["prompt_tokens"] == 10
            assert result.usage["completion_tokens"] == 12

    @pytest.mark.asyncio
    async def test_generate_with_system_message(self, anthropic_client):
        """Test generation with system message (Anthropic specific)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Response"}],
            "model": "claude-3-5-sonnet-20241022",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 5}
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            messages = [
                LLMMessage(role="system", content="You are helpful"),
                LLMMessage(role="user", content="Hello")
            ]
            await anthropic_client.generate(messages=messages)

            # Verify system message is separate
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["system"] == "You are helpful"
            assert len(payload["messages"]) == 1
            assert payload["messages"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_generate_requires_max_tokens(self, anthropic_client):
        """Test that max_tokens is always included (Anthropic requirement)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Response"}],
            "model": "claude-3-5-sonnet-20241022",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 5}
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            messages = [LLMMessage(role="user", content="Hello")]
            await anthropic_client.generate(messages=messages)

            # Verify max_tokens is included even when not specified
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert "max_tokens" in payload
            assert payload["max_tokens"] == 1024  # Default value

    @pytest.mark.asyncio
    async def test_generate_authentication_error(self, anthropic_client):
        """Test handling of authentication errors (401)"""
        mock_response = Mock()
        mock_response.status_code = 401

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            messages = [LLMMessage(role="user", content="Hello")]

            with pytest.raises(LLMAuthenticationError) as exc_info:
                await anthropic_client.generate(messages=messages)

            assert exc_info.value.provider == "anthropic"
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_rate_limit_error(self, anthropic_client):
        """Test handling of rate limit errors (429)"""
        mock_response = Mock()
        mock_response.status_code = 429

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            messages = [LLMMessage(role="user", content="Hello")]

            with pytest.raises(LLMRateLimitError) as exc_info:
                await anthropic_client.generate(messages=messages)

            assert exc_info.value.provider == "anthropic"
            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_message_conversion(self, anthropic_client):
        """Test conversion of messages to Anthropic format"""
        messages = [
            LLMMessage(role="system", content="You are helpful"),
            LLMMessage(role="user", content="Hello"),
            LLMMessage(role="assistant", content="Hi!"),
        ]

        system_msg, conversation_msgs = anthropic_client._convert_messages(messages)

        # System message should be separate
        assert system_msg == "You are helpful"
        # Only user and assistant messages in conversation
        assert len(conversation_msgs) == 2
        assert conversation_msgs[0]["role"] == "user"
        assert conversation_msgs[1]["role"] == "assistant"

    def test_get_default_model(self, anthropic_client):
        """Test getting default model"""
        assert anthropic_client.get_default_model() == "claude-3-5-sonnet-20241022"

    def test_create_anthropic_client_factory(self):
        """Test factory function for creating Anthropic client"""
        client = create_anthropic_client("test-key", {"default_model": "claude-opus"})
        assert isinstance(client, AnthropicClient)
        assert client.api_key == "test-key"
        assert client.default_model == "claude-opus"
