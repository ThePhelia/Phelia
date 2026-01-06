"""Settings management endpoints for provider credentials."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.runtime_settings import runtime_settings

router = APIRouter(prefix="/settings", tags=["settings"])


# API Key Management Models
class ApiKeyResponse(BaseModel):
    provider: str
    configured: bool
    value: str | None = None


class ApiKeysResponse(BaseModel):
    api_keys: list[ApiKeyResponse]


class ApiKeyUpdateRequest(BaseModel):
    value: str | None


class ApiKeysUpdateRequest(BaseModel):
    api_keys: dict[str, str | None]


# API Key Management Endpoints
@router.get("/api-keys", response_model=ApiKeysResponse)
def get_api_keys() -> ApiKeysResponse:
    """Get all configured API keys (without exposing the actual values)."""
    api_keys = []
    for provider in runtime_settings.supported_providers():
        configured = runtime_settings.is_configured(provider)
        api_keys.append(
            ApiKeyResponse(
                provider=provider,
                configured=configured,
                value=None,  # Never expose actual API keys
            )
        )
    return ApiKeysResponse(api_keys=api_keys)


@router.get("/api-keys/{provider}", response_model=ApiKeyResponse)
def get_api_key(provider: str) -> ApiKeyResponse:
    """Get configuration status for a specific API key provider."""
    if provider not in runtime_settings.supported_providers():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "provider_not_found", "provider": provider},
        )

    configured = runtime_settings.is_configured(provider)
    return ApiKeyResponse(
        provider=provider,
        configured=configured,
        value=None,  # Never expose actual API keys
    )


@router.post("/api-keys/{provider}", response_model=ApiKeyResponse)
def update_api_key(provider: str, request: ApiKeyUpdateRequest) -> ApiKeyResponse:
    """Update an API key for a specific provider."""
    if provider not in runtime_settings.supported_providers():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "provider_not_found", "provider": provider},
        )

    runtime_settings.set(provider, request.value)
    configured = runtime_settings.is_configured(provider)

    return ApiKeyResponse(
        provider=provider,
        configured=configured,
        value=None,  # Never expose actual API keys
    )


@router.post("/api-keys", response_model=ApiKeysResponse)
def update_api_keys(request: ApiKeysUpdateRequest) -> ApiKeysResponse:
    """Bulk update multiple API keys."""
    # Validate all providers exist before updating any
    for provider in request.api_keys.keys():
        if provider not in runtime_settings.supported_providers():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "provider_not_found", "provider": provider},
            )

    # Update all keys
    runtime_settings.update_many(request.api_keys)

    # Return updated status
    api_keys = []
    for provider in runtime_settings.supported_providers():
        configured = runtime_settings.is_configured(provider)
        api_keys.append(
            ApiKeyResponse(
                provider=provider,
                configured=configured,
                value=None,  # Never expose actual API keys
            )
        )
    return ApiKeysResponse(api_keys=api_keys)
