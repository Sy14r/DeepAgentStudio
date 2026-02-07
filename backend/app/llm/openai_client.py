"""
OpenAI LLM client implementation.

This module provides a wrapper around the OpenAI API with:
- Consistent interface (BaseLLMClient)
- Error handling and retry logic
- Easy mocking for tests
"""
from typing import Optional, Dict, Any, List
import httpx
from .base import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    LLMProviderError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMInvalidRequestError,
    LLMConnectionError
)


class OpenAIClient(BaseLLMClient):
    """
    OpenAI API client implementation.

    Supports:
    - GPT-4o, GPT-4o-mini, GPT-4 Turbo models
    - Chat completions
    - Organization-specific API keys
    """

    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            config: Optional config with:
                - base_url: Custom API base URL (default: "https://api.openai.com/v1")
                - organization_id: OpenAI organization ID
                - default_model: Default model (default: "gpt-4o-mini")
                - timeout: Request timeout in seconds (default: 60)
        """
        super().__init__(api_key, config)
        self.base_url = self.config.get("base_url", "https://api.openai.com/v1")
        self.organization_id = self.config.get("organization_id")
        self.default_model = self.config.get("default_model", "gpt-4o-mini")
        self.timeout = self.config.get("timeout", 60)

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for OpenAI API requests"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if self.organization_id:
            headers["OpenAI-Organization"] = self.organization_id
        return headers

    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """Convert LLMMessage objects to OpenAI format"""
        openai_messages = []
        for msg in messages:
            openai_msg = {
                "role": msg.role,
                "content": msg.content
            }
            if msg.name:
                openai_msg["name"] = msg.name
            if msg.tool_calls:
                openai_msg["tool_calls"] = msg.tool_calls
            openai_messages.append(openai_msg)
        return openai_messages

    async def generate(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a completion using OpenAI's API.

        Args:
            messages: Conversation messages
            model: Model to use (default: from config)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Max tokens to generate
            **kwargs: Additional OpenAI parameters (top_p, frequency_penalty, etc.)

        Returns:
            LLMResponse with the completion

        Raises:
            LLMAuthenticationError: Invalid API key
            LLMRateLimitError: Rate limit exceeded
            LLMInvalidRequestError: Invalid request
            LLMConnectionError: Connection failed
        """
        payload = {
            "model": model or self.default_model,
            "messages": self._convert_messages(messages)
        }

        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        # Add any additional parameters
        payload.update(kwargs)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload
                )

                # Handle errors
                if response.status_code == 401:
                    raise LLMAuthenticationError(
                        "Invalid OpenAI API key",
                        provider="openai",
                        status_code=401,
                        error_type="authentication_error"
                    )
                elif response.status_code == 429:
                    raise LLMRateLimitError(
                        "OpenAI rate limit exceeded",
                        provider="openai",
                        status_code=429,
                        error_type="rate_limit_error"
                    )
                elif response.status_code >= 400:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("error", {}).get("message", "Unknown error")
                    raise LLMInvalidRequestError(
                        f"OpenAI API error: {error_message}",
                        provider="openai",
                        status_code=response.status_code,
                        error_type="invalid_request_error"
                    )

                response.raise_for_status()
                data = response.json()

                # Extract response
                choice = data["choices"][0]
                message = choice["message"]

                return LLMResponse(
                    content=message.get("content", ""),
                    model=data["model"],
                    finish_reason=choice["finish_reason"],
                    usage={
                        "prompt_tokens": data["usage"]["prompt_tokens"],
                        "completion_tokens": data["usage"]["completion_tokens"],
                        "total_tokens": data["usage"]["total_tokens"]
                    },
                    tool_calls=message.get("tool_calls"),
                    raw_response=data
                )

        except httpx.TimeoutException as e:
            raise LLMConnectionError(
                f"OpenAI request timed out after {self.timeout}s",
                provider="openai",
                error_type="timeout_error"
            ) from e
        except httpx.RequestError as e:
            raise LLMConnectionError(
                f"OpenAI connection error: {str(e)}",
                provider="openai",
                error_type="connection_error"
            ) from e

    async def test_connection(self) -> bool:
        """
        Test the connection to OpenAI API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Send a minimal test request
            test_messages = [
                LLMMessage(role="user", content="test")
            ]
            await self.generate(
                messages=test_messages,
                max_tokens=5  # Minimal tokens to save cost
            )
            return True
        except Exception:
            return False

    def get_default_model(self) -> str:
        """Get the default model"""
        return self.default_model


def create_openai_client(api_key: str, config: Dict[str, Any] = None) -> OpenAIClient:
    """
    Factory function to create an OpenAI client.

    This function exists to make mocking easier in tests.

    Args:
        api_key: OpenAI API key
        config: Optional configuration

    Returns:
        OpenAIClient instance
    """
    return OpenAIClient(api_key, config)
