"""
LLM Provider Configuration API endpoints

Provides CRUD operations for managing LLM provider configurations with:
- Encrypted API key storage
- Connection testing
- Provider-specific configuration
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
import time
from datetime import datetime

from ...database import get_db
from ...models.user import User
from ...models.llm_provider import LLMProviderConfig
from ...schemas.llm_provider import (
    LLMProviderConfigCreate,
    LLMProviderConfigUpdate,
    LLMProviderConfigUpdateAPIKey,
    LLMProviderConfigResponse,
    LLMProviderConfigListResponse,
    LLMProviderTestRequest,
    LLMProviderTestResponse,
)
from ...encryption import encrypt_api_key, decrypt_api_key
from ...llm.openai_client import create_openai_client
from ...llm.anthropic_client import create_anthropic_client
from ...llm.base import LLMMessage, LLMAuthenticationError, LLMProviderError
from ..deps import get_current_user

router = APIRouter()


def _provider_to_response(provider: LLMProviderConfig) -> LLMProviderConfigResponse:
    """Convert LLMProviderConfig model to response schema"""
    return LLMProviderConfigResponse(
        id=provider.id,
        user_id=provider.user_id,
        provider_type=provider.provider_type,
        name=provider.name,
        description=provider.description,
        config=provider.config,
        is_active=provider.is_active,
        last_used_at=provider.last_used_at,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
        has_api_key=bool(provider.encrypted_api_key),
    )


@router.post("", response_model=LLMProviderConfigResponse, status_code=status.HTTP_201_CREATED)
def create_provider_config(
    provider_data: LLMProviderConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new LLM provider configuration.

    The API key will be encrypted before storage and never returned in responses.
    """
    # Encrypt the API key
    encrypted_key = encrypt_api_key(provider_data.api_key)

    # Create provider config
    provider = LLMProviderConfig(
        user_id=current_user.id,
        provider_type=provider_data.provider_type,
        name=provider_data.name,
        description=provider_data.description,
        encrypted_api_key=encrypted_key,
        config=provider_data.config,
    )

    db.add(provider)
    db.commit()
    db.refresh(provider)

    return _provider_to_response(provider)


@router.get("", response_model=LLMProviderConfigListResponse)
def list_provider_configs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    active_only: bool = Query(False, description="Only return active providers"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all LLM provider configurations for the current user.

    API keys are NEVER included in the response.
    """
    query = db.query(LLMProviderConfig).filter(
        LLMProviderConfig.user_id == current_user.id
    )

    if active_only:
        query = query.filter(LLMProviderConfig.is_active == True)

    total = query.count()
    providers = query.order_by(
        LLMProviderConfig.updated_at.desc()
    ).offset(skip).limit(limit).all()

    return LLMProviderConfigListResponse(
        providers=[_provider_to_response(p) for p in providers],
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/{provider_id}", response_model=LLMProviderConfigResponse)
def get_provider_config(
    provider_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific LLM provider configuration.

    The API key is NEVER included in the response.
    """
    provider = db.query(LLMProviderConfig).filter(
        LLMProviderConfig.id == provider_id,
        LLMProviderConfig.user_id == current_user.id
    ).first()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider configuration not found"
        )

    return _provider_to_response(provider)


@router.put("/{provider_id}", response_model=LLMProviderConfigResponse)
def update_provider_config(
    provider_id: int,
    provider_data: LLMProviderConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update LLM provider configuration.

    This endpoint CANNOT update the API key. Use the separate
    PUT /{provider_id}/api-key endpoint for security.
    """
    provider = db.query(LLMProviderConfig).filter(
        LLMProviderConfig.id == provider_id,
        LLMProviderConfig.user_id == current_user.id
    ).first()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider configuration not found"
        )

    # Update fields
    if provider_data.name is not None:
        provider.name = provider_data.name
    if provider_data.description is not None:
        provider.description = provider_data.description
    if provider_data.config is not None:
        provider.config = provider_data.config
    if provider_data.is_active is not None:
        provider.is_active = provider_data.is_active

    db.commit()
    db.refresh(provider)

    return _provider_to_response(provider)


@router.put("/{provider_id}/api-key", response_model=LLMProviderConfigResponse)
def update_provider_api_key(
    provider_id: int,
    api_key_data: LLMProviderConfigUpdateAPIKey,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the API key for a provider configuration.

    This is a separate endpoint for security - API keys should only be
    updated when explicitly intended, not as part of regular updates.

    The new API key will be encrypted and never returned in the response.
    """
    provider = db.query(LLMProviderConfig).filter(
        LLMProviderConfig.id == provider_id,
        LLMProviderConfig.user_id == current_user.id
    ).first()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider configuration not found"
        )

    # Encrypt and update the API key
    provider.encrypted_api_key = encrypt_api_key(api_key_data.api_key)

    db.commit()
    db.refresh(provider)

    return _provider_to_response(provider)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider_config(
    provider_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an LLM provider configuration.

    This permanently deletes the configuration and its encrypted API key.
    """
    provider = db.query(LLMProviderConfig).filter(
        LLMProviderConfig.id == provider_id,
        LLMProviderConfig.user_id == current_user.id
    ).first()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider configuration not found"
        )

    db.delete(provider)
    db.commit()

    return None


@router.post("/{provider_id}/test", response_model=LLMProviderTestResponse)
async def test_provider_connection(
    provider_id: int,
    test_request: LLMProviderTestRequest = LLMProviderTestRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Test the connection to an LLM provider.

    Sends a minimal test request to verify the API key and configuration work.
    This will make an actual API call to the provider and may incur small costs.
    """
    provider = db.query(LLMProviderConfig).filter(
        LLMProviderConfig.id == provider_id,
        LLMProviderConfig.user_id == current_user.id
    ).first()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider configuration not found"
        )

    # Decrypt the API key
    try:
        api_key = decrypt_api_key(provider.encrypted_api_key)
    except Exception as e:
        return LLMProviderTestResponse(
            success=False,
            error="Failed to decrypt API key. The encryption key may have changed."
        )

    # Create the appropriate client
    start_time = time.time()

    try:
        if provider.provider_type == "openai":
            client = create_openai_client(api_key, provider.config)
        elif provider.provider_type == "anthropic":
            client = create_anthropic_client(api_key, provider.config)
        else:
            return LLMProviderTestResponse(
                success=False,
                error=f"Provider type '{provider.provider_type}' not yet implemented for testing"
            )

        # Send a minimal test message
        test_messages = [
            LLMMessage(role="user", content=test_request.test_message)
        ]

        response = await client.generate(
            messages=test_messages,
            max_tokens=50  # Minimal tokens to save cost
        )

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Update last_used_at
        provider.last_used_at = datetime.utcnow()
        db.commit()

        return LLMProviderTestResponse(
            success=True,
            response=response.content,
            latency_ms=latency_ms,
            tokens_used=response.usage.get("total_tokens")
        )

    except LLMAuthenticationError as e:
        return LLMProviderTestResponse(
            success=False,
            error=f"Authentication failed: {str(e)}"
        )
    except LLMProviderError as e:
        return LLMProviderTestResponse(
            success=False,
            error=f"Provider error: {str(e)}"
        )
    except Exception as e:
        return LLMProviderTestResponse(
            success=False,
            error=f"Unexpected error: {str(e)}"
        )
