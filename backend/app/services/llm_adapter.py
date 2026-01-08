"""
LLM Provider Adapter for LangChain Integration.

This module adapts our LLMProviderConfig and credentials to create
LangChain-compatible chat model instances.

Supports:
- OpenAI (ChatOpenAI)
- Anthropic (ChatAnthropic)
- Future: Google, Azure, Ollama, etc.
"""
from typing import Any, Dict, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from sqlalchemy.orm import Session
import logging

from ..models.llm_provider import LLMProviderConfig, LLMProviderType
from ..encryption import decrypt_api_key

logger = logging.getLogger(__name__)


class ChatOpenAINoStop(ChatOpenAI):
    """
    ChatOpenAI wrapper that strips the 'stop' parameter.

    Newer OpenAI models (o1, o3, gpt-4o, etc.) don't support the 'stop' parameter.
    This wrapper strips it before making API calls, allowing these models to work
    with LangChain agents that pass stop sequences.
    """

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate without stop parameter."""
        logger.debug(f"ChatOpenAINoStop._generate: stripping stop parameter (was: {stop})")
        return super()._generate(messages, stop=None, **kwargs)

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Async generate without stop parameter."""
        logger.debug(f"ChatOpenAINoStop._agenerate: stripping stop parameter (was: {stop})")
        return await super()._agenerate(messages, stop=None, **kwargs)

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        """Stream without stop parameter."""
        logger.debug(f"ChatOpenAINoStop._stream: stripping stop parameter (was: {stop})")
        return super()._stream(messages, stop=None, **kwargs)

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        """Async stream without stop parameter."""
        logger.debug(f"ChatOpenAINoStop._astream: stripping stop parameter (was: {stop})")
        async for chunk in super()._astream(messages, stop=None, **kwargs):
            yield chunk


class LLMAdapterError(Exception):
    """Exception raised when LLM adapter fails"""
    pass


class UnsupportedProviderError(LLMAdapterError):
    """Exception raised for unsupported provider types"""
    pass


class LLMProviderAdapter:
    """
    Adapter to create LangChain-compatible LLM instances from our
    provider configurations.

    Usage:
        # From database config
        adapter = LLMProviderAdapter(db)
        llm = adapter.create_from_provider_id(
            provider_id=1,
            user_id=1,
            llm_config={"model": "gpt-4", "temperature": 0.7}
        )

        # Or directly from config object
        llm = LLMProviderAdapter.create_llm(provider_config, llm_config)
    """

    def __init__(self, db: Session):
        """
        Initialize adapter with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_from_provider_id(
        self,
        provider_id: int,
        user_id: int,
        llm_config: Dict[str, Any]
    ) -> BaseChatModel:
        """
        Create LangChain LLM from provider ID.

        Args:
            provider_id: ID of LLMProviderConfig in database
            user_id: User ID (for validation)
            llm_config: Agent's LLM configuration with model, temperature, etc.

        Returns:
            LangChain BaseChatModel instance

        Raises:
            LLMAdapterError: If provider not found or user doesn't own it
            UnsupportedProviderError: If provider type not supported
        """
        provider_config = self.db.query(LLMProviderConfig).filter(
            LLMProviderConfig.id == provider_id,
            LLMProviderConfig.user_id == user_id,
            LLMProviderConfig.is_active == True
        ).first()

        if not provider_config:
            raise LLMAdapterError(
                f"Provider config {provider_id} not found or not accessible"
            )

        return self.create_llm(provider_config, llm_config)

    @staticmethod
    def create_llm(
        provider_config: LLMProviderConfig,
        llm_config: Dict[str, Any]
    ) -> BaseChatModel:
        """
        Create a LangChain LLM instance from provider configuration.

        Args:
            provider_config: LLMProviderConfig from database
            llm_config: Agent's LLM configuration containing:
                - model: Model name (e.g., "gpt-4", "claude-3-5-sonnet-20241022")
                - temperature: Sampling temperature (0.0-2.0)
                - max_tokens: Maximum tokens to generate
                - Other provider-specific params

        Returns:
            LangChain BaseChatModel instance ready for use

        Raises:
            UnsupportedProviderError: If provider type not supported
        """
        # Decrypt API key
        try:
            api_key = decrypt_api_key(provider_config.encrypted_api_key)
        except Exception as e:
            raise LLMAdapterError(f"Failed to decrypt API key: {str(e)}")

        provider_type = provider_config.provider_type

        # Merge provider config with agent's llm_config
        # Provider config provides defaults, agent config overrides
        merged_config = {**provider_config.config, **llm_config}

        if provider_type == LLMProviderType.OPENAI:
            return LLMProviderAdapter._create_openai(api_key, merged_config)

        elif provider_type == LLMProviderType.ANTHROPIC:
            return LLMProviderAdapter._create_anthropic(api_key, merged_config)

        elif provider_type == LLMProviderType.GOOGLE:
            raise UnsupportedProviderError(
                "Google Gemini support coming soon"
            )

        elif provider_type == LLMProviderType.AZURE_OPENAI:
            raise UnsupportedProviderError(
                "Azure OpenAI support coming soon"
            )

        elif provider_type == LLMProviderType.OLLAMA:
            raise UnsupportedProviderError(
                "Ollama support coming soon"
            )

        elif provider_type == LLMProviderType.LLAMACPP:
            raise UnsupportedProviderError(
                "LlamaCPP support coming soon"
            )

        else:
            raise UnsupportedProviderError(
                f"Unsupported provider type: {provider_type}"
            )

    @staticmethod
    def _requires_max_completion_tokens(model: str, config: Dict[str, Any] = None) -> bool:
        """
        Check if an OpenAI model requires max_completion_tokens instead of max_tokens.

        Newer OpenAI models (o1, o3 series, and some newer gpt-4 variants) use
        max_completion_tokens parameter instead of max_tokens.

        Also checks custom_models configuration from the provider for custom models
        that have usesMaxCompletionTokens set to True.

        Args:
            model: Model name string
            config: Optional config dict that may contain custom_models list

        Returns:
            True if model requires max_completion_tokens
        """
        # First, check if this is a custom model with usesMaxCompletionTokens flag
        if config:
            custom_models = config.get("custom_models", [])
            for custom_model in custom_models:
                if custom_model.get("id") == model:
                    if custom_model.get("usesMaxCompletionTokens", False):
                        logger.debug(f"Custom model {model} configured for max_completion_tokens")
                        return True
                    # Custom model found but doesn't use max_completion_tokens
                    # Continue to check built-in patterns
                    break

        model_lower = model.lower()

        # o1 and o3 series models require max_completion_tokens
        if model_lower.startswith(("o1", "o3")):
            return True

        # gpt-4o models require max_completion_tokens
        if "gpt-4o" in model_lower:
            return True

        # gpt-4-turbo models (2024 and later) require max_completion_tokens
        if "gpt-4-turbo" in model_lower:
            return True

        return False

    @staticmethod
    def _create_openai(api_key: str, config: Dict[str, Any]) -> ChatOpenAI:
        """
        Create OpenAI chat model.

        Args:
            api_key: OpenAI API key
            config: Configuration dict with model, temperature, etc.

        Returns:
            ChatOpenAI instance
        """
        # Extract OpenAI-specific parameters
        model = config.get("model", "gpt-4")
        temperature = config.get("temperature", 0.7)
        max_tokens = config.get("max_tokens")
        organization_id = config.get("organization_id")
        timeout = config.get("timeout", 60)

        kwargs = {
            "api_key": api_key,
            "model": model,
            "temperature": temperature,
            "timeout": timeout,
            "stream_usage": True,  # Enable token usage reporting for streaming
        }

        # Handle max_tokens vs max_completion_tokens based on model
        # Pass full config to check custom_models for usesMaxCompletionTokens flag
        if max_tokens:
            if LLMProviderAdapter._requires_max_completion_tokens(model, config):
                # Newer models use max_completion_tokens
                kwargs["max_completion_tokens"] = max_tokens
                logger.debug(f"Using max_completion_tokens={max_tokens} for model {model}")
            else:
                # Older models use max_tokens
                kwargs["max_tokens"] = max_tokens

        if organization_id:
            kwargs["organization"] = organization_id

        # Check if this model uses the new API (max_completion_tokens)
        # These models have restrictions on certain parameters
        uses_new_api = LLMProviderAdapter._requires_max_completion_tokens(model, config)

        # Add any additional parameters
        # Note: Newer models (o1, o3, gpt-4o, etc.) don't support 'stop' parameter
        for key in ["top_p", "frequency_penalty", "presence_penalty"]:
            if key in config:
                kwargs[key] = config[key]

        # Only add 'stop' for models that support it (older models)
        if not uses_new_api and "stop" in config:
            kwargs["stop"] = config["stop"]

        logger.debug(f"Creating OpenAI LLM with model={model}, temp={temperature}, uses_new_api={uses_new_api}")

        # Use ChatOpenAINoStop wrapper for models that don't support stop parameter
        # This is needed because LangChain agents pass stop sequences at runtime
        if uses_new_api:
            logger.debug(f"Using ChatOpenAINoStop wrapper for model {model} (doesn't support stop parameter)")
            return ChatOpenAINoStop(**kwargs)

        return ChatOpenAI(**kwargs)

    @staticmethod
    def _create_anthropic(api_key: str, config: Dict[str, Any]) -> ChatAnthropic:
        """
        Create Anthropic chat model.

        Args:
            api_key: Anthropic API key
            config: Configuration dict with model, temperature, etc.

        Returns:
            ChatAnthropic instance
        """
        # Extract Anthropic-specific parameters
        model = config.get("model", "claude-3-5-sonnet-20241022")
        temperature = config.get("temperature", 0.7)
        max_tokens = config.get("max_tokens", 1024)  # Required by Anthropic
        timeout = config.get("timeout", 60)

        # Anthropic only supports temperature 0.0-1.0, clamp if needed
        if temperature > 1.0:
            logger.warning(
                f"Anthropic temperature clamped from {temperature} to 1.0 "
                "(Anthropic max is 1.0)"
            )
            temperature = 1.0

        kwargs = {
            "api_key": api_key,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
        }

        # Add any additional parameters
        for key in ["top_p", "top_k", "stop_sequences"]:
            if key in config:
                kwargs[key] = config[key]

        logger.debug(f"Creating Anthropic LLM with model={model}, temp={temperature}")

        return ChatAnthropic(**kwargs)

    @staticmethod
    def get_supported_providers() -> list[str]:
        """
        Get list of currently supported provider types.

        Returns:
            List of supported provider type strings
        """
        return ["openai", "anthropic"]

    @staticmethod
    def is_provider_supported(provider_type: str) -> bool:
        """
        Check if a provider type is currently supported.

        Args:
            provider_type: Provider type string

        Returns:
            True if supported, False otherwise
        """
        return provider_type.lower() in LLMProviderAdapter.get_supported_providers()


def create_llm_from_agent_config(
    db: Session,
    user_id: int,
    llm_config: Dict[str, Any]
) -> BaseChatModel:
    """
    Convenience function to create LLM from agent's LLM configuration.

    Args:
        db: Database session
        user_id: User ID
        llm_config: Agent's LLM configuration containing:
            - provider_id: ID of LLMProviderConfig to use
            - model: Model name
            - temperature: Sampling temperature
            - max_tokens: Maximum tokens
            - Other provider-specific settings

    Returns:
        LangChain BaseChatModel instance

    Raises:
        LLMAdapterError: If configuration is invalid
    """
    provider_id = llm_config.get("provider_id")
    if not provider_id:
        raise LLMAdapterError("No provider_id specified in LLM config")

    adapter = LLMProviderAdapter(db)
    return adapter.create_from_provider_id(
        provider_id=provider_id,
        user_id=user_id,
        llm_config=llm_config
    )
