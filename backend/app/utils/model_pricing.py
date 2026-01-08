"""
Model Pricing Configuration.

Provides pricing information for various LLM models to calculate costs per span.
Prices are in USD per 1,000 tokens.
"""
from typing import Dict, Optional, Tuple
from decimal import Decimal


# Pricing per 1K tokens (input, output)
# Updated: January 2026
MODEL_PRICING: Dict[str, Tuple[Decimal, Decimal]] = {
    # OpenAI GPT-4o series
    "gpt-4o": (Decimal("0.0025"), Decimal("0.01")),
    "gpt-4o-2024-11-20": (Decimal("0.0025"), Decimal("0.01")),
    "gpt-4o-2024-08-06": (Decimal("0.0025"), Decimal("0.01")),
    "gpt-4o-2024-05-13": (Decimal("0.005"), Decimal("0.015")),
    "gpt-4o-mini": (Decimal("0.00015"), Decimal("0.0006")),
    "gpt-4o-mini-2024-07-18": (Decimal("0.00015"), Decimal("0.0006")),

    # OpenAI GPT-4 series
    "gpt-4-turbo": (Decimal("0.01"), Decimal("0.03")),
    "gpt-4-turbo-preview": (Decimal("0.01"), Decimal("0.03")),
    "gpt-4-turbo-2024-04-09": (Decimal("0.01"), Decimal("0.03")),
    "gpt-4": (Decimal("0.03"), Decimal("0.06")),
    "gpt-4-0613": (Decimal("0.03"), Decimal("0.06")),
    "gpt-4-32k": (Decimal("0.06"), Decimal("0.12")),

    # OpenAI GPT-3.5 series
    "gpt-3.5-turbo": (Decimal("0.0005"), Decimal("0.0015")),
    "gpt-3.5-turbo-0125": (Decimal("0.0005"), Decimal("0.0015")),
    "gpt-3.5-turbo-1106": (Decimal("0.001"), Decimal("0.002")),
    "gpt-3.5-turbo-16k": (Decimal("0.003"), Decimal("0.004")),

    # Anthropic Claude 3.5 series
    "claude-3-5-sonnet-20241022": (Decimal("0.003"), Decimal("0.015")),
    "claude-3-5-sonnet-20240620": (Decimal("0.003"), Decimal("0.015")),
    "claude-3-5-haiku-20241022": (Decimal("0.001"), Decimal("0.005")),

    # Anthropic Claude 3 series
    "claude-3-opus-20240229": (Decimal("0.015"), Decimal("0.075")),
    "claude-3-sonnet-20240229": (Decimal("0.003"), Decimal("0.015")),
    "claude-3-haiku-20240307": (Decimal("0.00025"), Decimal("0.00125")),

    # Anthropic Claude 2 series (legacy)
    "claude-2.1": (Decimal("0.008"), Decimal("0.024")),
    "claude-2.0": (Decimal("0.008"), Decimal("0.024")),
    "claude-instant-1.2": (Decimal("0.0008"), Decimal("0.0024")),

    # Google Gemini series
    "gemini-1.5-pro": (Decimal("0.00125"), Decimal("0.005")),
    "gemini-1.5-flash": (Decimal("0.000075"), Decimal("0.0003")),
    "gemini-1.0-pro": (Decimal("0.0005"), Decimal("0.0015")),

    # Embedding models (output price same as input for embeddings)
    "text-embedding-3-large": (Decimal("0.00013"), Decimal("0.00013")),
    "text-embedding-3-small": (Decimal("0.00002"), Decimal("0.00002")),
    "text-embedding-ada-002": (Decimal("0.0001"), Decimal("0.0001")),
}

# Default pricing for unknown models (conservative estimate)
DEFAULT_PRICING = (Decimal("0.01"), Decimal("0.03"))


def get_model_pricing(model_name: str) -> Tuple[Decimal, Decimal]:
    """
    Get pricing for a model.

    Args:
        model_name: Name of the model

    Returns:
        Tuple of (input_price_per_1k, output_price_per_1k) in USD
    """
    # Try exact match first
    if model_name in MODEL_PRICING:
        return MODEL_PRICING[model_name]

    # Try prefix matching for versioned models
    model_lower = model_name.lower()
    for known_model, pricing in MODEL_PRICING.items():
        if model_lower.startswith(known_model.lower()):
            return pricing
        if known_model.lower().startswith(model_lower):
            return pricing

    # Return default pricing for unknown models
    return DEFAULT_PRICING


def calculate_cost(
    model_name: str,
    input_tokens: int,
    output_tokens: int
) -> Decimal:
    """
    Calculate cost for a model invocation.

    Args:
        model_name: Name of the model
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Total cost in USD
    """
    input_price, output_price = get_model_pricing(model_name)

    input_cost = (Decimal(input_tokens) / Decimal(1000)) * input_price
    output_cost = (Decimal(output_tokens) / Decimal(1000)) * output_price

    return input_cost + output_cost


def get_provider_from_model(model_name: str) -> str:
    """
    Infer provider from model name.

    Args:
        model_name: Name of the model

    Returns:
        Provider name (openai, anthropic, google, unknown)
    """
    model_lower = model_name.lower()

    if model_lower.startswith("gpt-") or model_lower.startswith("text-embedding"):
        return "openai"
    elif model_lower.startswith("claude"):
        return "anthropic"
    elif model_lower.startswith("gemini"):
        return "google"
    elif model_lower.startswith("llama"):
        return "meta"
    elif model_lower.startswith("mistral"):
        return "mistral"
    else:
        return "unknown"
