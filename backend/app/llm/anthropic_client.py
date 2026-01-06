"""
Anthropic (Claude) LLM client implementation.

This module provides a wrapper around the Anthropic API with:
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


class AnthropicClient(BaseLLMClient):
    """
    Anthropic API client implementation.

    Supports:
    - Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku
    - Messages API
    """

    BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"

    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key
            config: Optional config with:
                - default_model: Default model (default: "claude-3-haiku-20240307")
                - timeout: Request timeout in seconds (default: 60)
        """
        super().__init__(api_key, config)
        self.default_model = self.config.get("default_model", "claude-3-haiku-20240307")
        self.timeout = self.config.get("timeout", 60)

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Anthropic API requests"""
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "Content-Type": "application/json"
        }

    def _convert_messages(self, messages: List[LLMMessage]) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Convert LLMMessage objects to Anthropic format.

        Anthropic separates system messages from conversation messages.

        Returns:
            Tuple of (system_message, conversation_messages)
        """
        system_message = None
        conversation_messages = []

        for msg in messages:
            if msg.role == "system":
                # Anthropic uses a separate system parameter
                system_message = msg.content
            else:
                anthropic_msg = {
                    "role": msg.role if msg.role != "tool" else "user",  # Anthropic uses "user" for tool results
                    "content": msg.content
                }
                conversation_messages.append(anthropic_msg)

        return system_message, conversation_messages

    async def generate(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a completion using Anthropic's API.

        Args:
            messages: Conversation messages
            model: Model to use (default: from config)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Max tokens to generate (default: 1024)
            **kwargs: Additional Anthropic parameters (top_p, top_k, etc.)

        Returns:
            LLMResponse with the completion

        Raises:
            LLMAuthenticationError: Invalid API key
            LLMRateLimitError: Rate limit exceeded
            LLMInvalidRequestError: Invalid request
            LLMConnectionError: Connection failed
        """
        system_message, conversation_messages = self._convert_messages(messages)

        payload = {
            "model": model or self.default_model,
            "messages": conversation_messages,
            "max_tokens": max_tokens or 1024  # Anthropic requires max_tokens
        }

        if system_message:
            payload["system"] = system_message
        if temperature is not None:
            payload["temperature"] = temperature

        # Add any additional parameters
        payload.update(kwargs)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/messages",
                    headers=self._get_headers(),
                    json=payload
                )

                # Handle errors
                if response.status_code == 401:
                    raise LLMAuthenticationError(
                        "Invalid Anthropic API key",
                        provider="anthropic",
                        status_code=401,
                        error_type="authentication_error"
                    )
                elif response.status_code == 429:
                    raise LLMRateLimitError(
                        "Anthropic rate limit exceeded",
                        provider="anthropic",
                        status_code=429,
                        error_type="rate_limit_error"
                    )
                elif response.status_code >= 400:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("error", {}).get("message", "Unknown error")
                    raise LLMInvalidRequestError(
                        f"Anthropic API error: {error_message}",
                        provider="anthropic",
                        status_code=response.status_code,
                        error_type="invalid_request_error"
                    )

                response.raise_for_status()
                data = response.json()

                # Extract response
                content = data["content"][0]["text"]

                return LLMResponse(
                    content=content,
                    model=data["model"],
                    finish_reason=data["stop_reason"],
                    usage={
                        "prompt_tokens": data["usage"]["input_tokens"],
                        "completion_tokens": data["usage"]["output_tokens"],
                        "total_tokens": data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
                    },
                    tool_calls=None,  # Tool use would be in content blocks
                    raw_response=data
                )

        except httpx.TimeoutException as e:
            raise LLMConnectionError(
                f"Anthropic request timed out after {self.timeout}s",
                provider="anthropic",
                error_type="timeout_error"
            ) from e
        except httpx.RequestError as e:
            raise LLMConnectionError(
                f"Anthropic connection error: {str(e)}",
                provider="anthropic",
                error_type="connection_error"
            ) from e

    async def test_connection(self) -> bool:
        """
        Test the connection to Anthropic API.

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


def create_anthropic_client(api_key: str, config: Dict[str, Any] = None) -> AnthropicClient:
    """
    Factory function to create an Anthropic client.

    This function exists to make mocking easier in tests.

    Args:
        api_key: Anthropic API key
        config: Optional configuration

    Returns:
        AnthropicClient instance
    """
    return AnthropicClient(api_key, config)
