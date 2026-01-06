"""
Optional Integration Tests for Real LLM APIs.

These tests make actual API calls to OpenAI and Anthropic.
They are SKIPPED by default and only run when:
1. The pytest marker --integration is used
2. The required environment variables are set

To run these tests:
1. Set environment variables:
   export OPENAI_API_KEY="your-openai-key"
   export ANTHROPIC_API_KEY="your-anthropic-key"

2. Run with the integration marker:
   pytest tests/test_llm_integration.py -m integration -v

⚠️  WARNING: These tests will make real API calls and incur costs!
"""
import pytest
import os
from app.llm.openai_client import create_openai_client
from app.llm.anthropic_client import create_anthropic_client
from app.llm.base import LLMMessage, LLMResponse


# Skip all tests in this module unless --integration flag is used
pytestmark = pytest.mark.integration


@pytest.fixture
def openai_api_key():
    """Get OpenAI API key from environment"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")
    return api_key


@pytest.fixture
def anthropic_api_key():
    """Get Anthropic API key from environment"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY environment variable not set")
    return api_key


class TestOpenAIIntegration:
    """Integration tests for OpenAI API"""

    @pytest.mark.asyncio
    async def test_openai_real_api_call(self, openai_api_key):
        """
        Test real API call to OpenAI.

        ⚠️  This test makes a real API call and will incur costs!
        """
        client = create_openai_client(
            openai_api_key,
            {"default_model": "gpt-4o-mini"}
        )

        messages = [
            LLMMessage(role="user", content="Say 'Hello, World!' and nothing else.")
        ]

        response = await client.generate(
            messages=messages,
            max_tokens=10,  # Minimal to save costs
            temperature=0  # Deterministic
        )

        # Verify response structure
        assert isinstance(response, LLMResponse)
        assert response.content is not None
        assert len(response.content) > 0
        assert response.model is not None
        assert "gpt" in response.model.lower()
        assert response.finish_reason in ["stop", "length"]
        assert response.usage["total_tokens"] > 0
        assert response.usage["prompt_tokens"] > 0
        assert response.usage["completion_tokens"] > 0

    @pytest.mark.asyncio
    async def test_openai_with_system_message(self, openai_api_key):
        """
        Test OpenAI with system message.

        ⚠️  This test makes a real API call and will incur costs!
        """
        client = create_openai_client(openai_api_key)

        messages = [
            LLMMessage(role="system", content="You are a helpful assistant."),
            LLMMessage(role="user", content="What is 2+2? Answer with just the number.")
        ]

        response = await client.generate(
            messages=messages,
            max_tokens=10,
            temperature=0
        )

        assert isinstance(response, LLMResponse)
        assert "4" in response.content

    @pytest.mark.asyncio
    async def test_openai_connection_test(self, openai_api_key):
        """
        Test connection testing method.

        ⚠️  This test makes a real API call and will incur costs!
        """
        client = create_openai_client(openai_api_key)
        success = await client.test_connection()
        assert success is True


class TestAnthropicIntegration:
    """Integration tests for Anthropic API"""

    @pytest.mark.asyncio
    async def test_anthropic_real_api_call(self, anthropic_api_key):
        """
        Test real API call to Anthropic.

        ⚠️  This test makes a real API call and will incur costs!
        """
        client = create_anthropic_client(
            anthropic_api_key,
            {"default_model": "claude-3-haiku-20240307"}
        )

        messages = [
            LLMMessage(role="user", content="Say 'Hello, World!' and nothing else.")
        ]

        response = await client.generate(
            messages=messages,
            max_tokens=20,  # Minimal to save costs
            temperature=0  # Deterministic
        )

        # Verify response structure
        assert isinstance(response, LLMResponse)
        assert response.content is not None
        assert len(response.content) > 0
        assert response.model is not None
        assert "claude" in response.model.lower()
        assert response.finish_reason in ["end_turn", "max_tokens"]
        assert response.usage["total_tokens"] > 0
        assert response.usage["prompt_tokens"] > 0
        assert response.usage["completion_tokens"] > 0

    @pytest.mark.asyncio
    async def test_anthropic_with_system_message(self, anthropic_api_key):
        """
        Test Anthropic with system message (special handling).

        ⚠️  This test makes a real API call and will incur costs!
        """
        client = create_anthropic_client(anthropic_api_key)

        messages = [
            LLMMessage(role="system", content="You are a helpful assistant."),
            LLMMessage(role="user", content="What is 2+2? Answer with just the number.")
        ]

        response = await client.generate(
            messages=messages,
            max_tokens=20,
            temperature=0
        )

        assert isinstance(response, LLMResponse)
        assert "4" in response.content

    @pytest.mark.asyncio
    async def test_anthropic_connection_test(self, anthropic_api_key):
        """
        Test connection testing method.

        ⚠️  This test makes a real API call and will incur costs!
        """
        client = create_anthropic_client(anthropic_api_key)
        success = await client.test_connection()
        assert success is True


class TestProviderComparison:
    """Integration tests comparing provider responses"""

    @pytest.mark.asyncio
    async def test_both_providers_basic_response(self, openai_api_key, anthropic_api_key):
        """
        Test that both providers can handle the same prompt.

        ⚠️  This test makes real API calls to both providers and will incur costs!
        """
        openai_client = create_openai_client(openai_api_key, {"default_model": "gpt-4o-mini"})
        anthropic_client = create_anthropic_client(
            anthropic_api_key,
            {"default_model": "claude-3-haiku-20240307"}
        )

        messages = [
            LLMMessage(
                role="user",
                content="What is the capital of France? Answer with just the city name."
            )
        ]

        # Get responses from both
        openai_response = await openai_client.generate(
            messages=messages,
            max_tokens=10,
            temperature=0
        )

        anthropic_response = await anthropic_client.generate(
            messages=messages,
            max_tokens=10,
            temperature=0
        )

        # Both should respond
        assert isinstance(openai_response, LLMResponse)
        assert isinstance(anthropic_response, LLMResponse)

        # Both should mention Paris
        assert "paris" in openai_response.content.lower()
        assert "paris" in anthropic_response.content.lower()

        # Both should have usage info
        assert openai_response.usage["total_tokens"] > 0
        assert anthropic_response.usage["total_tokens"] > 0


# Instructions for running integration tests
"""
INTEGRATION TEST INSTRUCTIONS
==============================

These tests are OPTIONAL and make real API calls to OpenAI and Anthropic.
They are skipped by default to avoid accidental costs.

Setup:
------
1. Get API keys:
   - OpenAI: https://platform.openai.com/api-keys
   - Anthropic: https://console.anthropic.com/

2. Set environment variables:
   export OPENAI_API_KEY="sk-your-openai-key-here"
   export ANTHROPIC_API_KEY="sk-ant-your-anthropic-key-here"

Running Tests:
--------------
# Run all integration tests (requires both API keys):
pytest tests/test_llm_integration.py -m integration -v

# Run only OpenAI integration tests:
pytest tests/test_llm_integration.py::TestOpenAIIntegration -m integration -v

# Run only Anthropic integration tests:
pytest tests/test_llm_integration.py::TestAnthropicIntegration -m integration -v

# Skip integration tests (default behavior):
pytest tests/test_llm_integration.py -v
# OR
pytest -m "not integration"

Costs:
------
These tests are designed to minimize costs by:
- Using small max_tokens limits
- Using temperature=0 for deterministic responses
- Using cheaper models (gpt-4o-mini for OpenAI, claude-3-haiku for Anthropic)

Estimated cost per full test run: < $0.01 USD

Important Notes:
----------------
⚠️  Never commit API keys to version control
⚠️  Use environment variables or .env files (gitignored)
⚠️  Monitor your API usage on provider dashboards
⚠️  These tests will fail if you hit rate limits
"""
