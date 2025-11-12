"""Settings management endpoints for provider credentials."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.schemas.settings import (
    PluginSettingsListResponse,
    PluginSettingsSummary,
    PluginSettingsUpdatePayload,
    PluginSettingsValuesResponse,
)
from app.plugins import loader
from app.services import plugin_settings as plugin_settings_service
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


@router.get("/plugins", response_model=PluginSettingsListResponse)
def list_plugin_settings() -> PluginSettingsListResponse:
    runtimes = loader.list_plugins()
    plugins: list[PluginSettingsSummary] = []
    for runtime in runtimes:
        manifest = runtime.manifest
        contributes = manifest.contributes_settings
        if contributes is None:
            contributes = bool(manifest.settings_schema)
        plugins.append(
            PluginSettingsSummary(
                id=manifest.id,
                name=manifest.name,
                contributes_settings=bool(contributes),
                settings_schema=manifest.settings_schema,
            )
        )
    return PluginSettingsListResponse(plugins=plugins)


def _ensure_plugin_runtime(plugin_id: str) -> loader.PluginRuntime:
    runtime = loader.get_runtime(plugin_id)
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "plugin_not_found"},
        )
    return runtime


@router.get("/plugins/{plugin_id}", response_model=PluginSettingsValuesResponse)
def get_plugin_settings(
    plugin_id: str,
    db: Session = Depends(get_db),
) -> PluginSettingsValuesResponse:
    runtime = _ensure_plugin_runtime(plugin_id)
    schema = runtime.manifest.settings_schema
    stored = plugin_settings_service.get_settings(db, plugin_id)
    merged = plugin_settings_service.apply_defaults(schema, stored)
    return PluginSettingsValuesResponse(values=merged)


@router.post("/plugins/{plugin_id}", response_model=PluginSettingsValuesResponse)
def update_plugin_settings(
    plugin_id: str,
    payload: PluginSettingsUpdatePayload,
    db: Session = Depends(get_db),
) -> PluginSettingsValuesResponse:
    runtime = _ensure_plugin_runtime(plugin_id)
    schema = runtime.manifest.settings_schema
    try:
        sanitized, allowed_keys = plugin_settings_service.validate_against_schema(
            schema, payload.values
        )
    except plugin_settings_service.PluginSettingsValidationError as exc:
        detail = {"error": "invalid_plugin_settings", "message": str(exc)}
        if exc.field is not None:
            detail["field"] = exc.field
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    plugin_settings_service.replace_settings(db, plugin_id, sanitized, allowed_keys)
    stored = plugin_settings_service.get_settings(db, plugin_id)
    merged = plugin_settings_service.apply_defaults(schema, stored)
    return PluginSettingsValuesResponse(values=merged)


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
                value=None  # Never expose actual API keys
            )
        )
    return ApiKeysResponse(api_keys=api_keys)


@router.get("/api-keys/{provider}", response_model=ApiKeyResponse)
def get_api_key(provider: str) -> ApiKeyResponse:
    """Get configuration status for a specific API key provider."""
    if provider not in runtime_settings.supported_providers():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "provider_not_found", "provider": provider}
        )
    
    configured = runtime_settings.is_configured(provider)
    return ApiKeyResponse(
        provider=provider,
        configured=configured,
        value=None  # Never expose actual API keys
    )


@router.post("/api-keys/{provider}", response_model=ApiKeyResponse)
def update_api_key(provider: str, request: ApiKeyUpdateRequest) -> ApiKeyResponse:
    """Update an API key for a specific provider."""
    if provider not in runtime_settings.supported_providers():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "provider_not_found", "provider": provider}
        )
    
    runtime_settings.set(provider, request.value)
    configured = runtime_settings.is_configured(provider)
    
    return ApiKeyResponse(
        provider=provider,
        configured=configured,
        value=None  # Never expose actual API keys
    )


@router.post("/api-keys", response_model=ApiKeysResponse)
def update_api_keys(request: ApiKeysUpdateRequest) -> ApiKeysResponse:
    """Bulk update multiple API keys."""
    # Validate all providers exist before updating any
    for provider in request.api_keys.keys():
        if provider not in runtime_settings.supported_providers():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "provider_not_found", "provider": provider}
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
                value=None  # Never expose actual API keys
            )
        )
    return ApiKeysResponse(api_keys=api_keys)
