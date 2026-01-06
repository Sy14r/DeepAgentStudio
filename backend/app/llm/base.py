"""
Base classes and interfaces for LLM provider clients.

This module defines the abstract interface that all LLM providers must implement,
enabling consistent interaction regardless of the underlying provider.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class LLMMessage:
    """Represents a message in a conversation"""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None  # For tool messages
    tool_calls: Optional[List[Dict[str, Any]]] = None  # For assistant tool calls


@dataclass
class LLMResponse:
    """Represents a response from an LLM"""
    content: str
    model: str
    finish_reason: str  # "stop", "length", "tool_calls", etc.
    usage: Dict[str, int]  # {"prompt_tokens": X, "completion_tokens": Y, "total_tokens": Z}
    tool_calls: Optional[List[Dict[str, Any]]] = None
    raw_response: Optional[Dict[str, Any]] = None  # Full API response for debugging


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM provider clients.

    All LLM providers (OpenAI, Anthropic, Google, etc.) must implement this interface
    to ensure consistent behavior across the application.
    """

    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        """
        Initialize the LLM client.

        Args:
            api_key: The API key for the provider
            config: Provider-specific configuration
        """
        self.api_key = api_key
        self.config = config or {}

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.

        Args:
            messages: List of conversation messages
            model: Model to use (overrides default from config)
            temperature: Temperature for sampling
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse with the generated completion

        Raises:
            LLMProviderError: If the API call fails
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test the connection to the provider.

        Returns:
            True if connection is successful, False otherwise
        """
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """
        Get the default model for this provider.

        Returns:
            Model identifier string
        """
        pass


class LLMProviderError(Exception):
    """Base exception for LLM provider errors"""

    def __init__(
        self,
        message: str,
        provider: str,
        status_code: Optional[int] = None,
        error_type: Optional[str] = None
    ):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.error_type = error_type


class LLMAuthenticationError(LLMProviderError):
    """Raised when authentication fails (invalid API key)"""
    pass


class LLMRateLimitError(LLMProviderError):
    """Raised when rate limit is exceeded"""
    pass


class LLMInvalidRequestError(LLMProviderError):
    """Raised when the request is invalid"""
    pass


class LLMConnectionError(LLMProviderError):
    """Raised when connection to the provider fails"""
    pass
