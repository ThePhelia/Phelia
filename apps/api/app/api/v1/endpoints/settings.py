"""Settings management endpoints for provider credentials."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.runtime_settings import runtime_settings
from app.db.session import get_db
from app.schemas.settings import (
    ProviderCredentialPayload,
    ProviderCredentialStatus,
    ProviderCredentialsResponse,
    PluginSettingsListResponse,
    PluginSettingsSummary,
    PluginSettingsUpdatePayload,
    PluginSettingsValuesResponse,
)
from app.services import settings as settings_service
from app.services.settings import UnsupportedProviderError
from app.plugins import loader
from app.services import plugin_settings as plugin_settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/providers", response_model=ProviderCredentialsResponse)
def list_providers(db: Session = Depends(get_db)) -> ProviderCredentialsResponse:
    stored = settings_service.list_provider_credentials(db)
    snapshot = runtime_settings.snapshot()
    statuses: list[ProviderCredentialStatus] = []
    for provider in settings_service.supported_providers():
        persisted_key = stored.get(provider)
        api_key = persisted_key if persisted_key is not None else snapshot.get(provider)
        statuses.append(
            ProviderCredentialStatus(
                provider=provider,
                configured=bool(api_key),
                masked_api_key=settings_service.mask_api_key(api_key),
            )
        )
    return ProviderCredentialsResponse(providers=statuses)


@router.put("/providers/{provider}", response_model=ProviderCredentialStatus)
def upsert_provider(
    provider: str,
    payload: ProviderCredentialPayload,
    db: Session = Depends(get_db),
) -> ProviderCredentialStatus:
    raw_key = payload.api_key
    normalized_key = raw_key.strip() if isinstance(raw_key, str) else None
    api_key = normalized_key or None
    try:
        stored_key = settings_service.upsert_provider_credential(db, provider, api_key)
    except UnsupportedProviderError:
        raise HTTPException(status_code=404, detail={"error": "unknown_provider"})

    return ProviderCredentialStatus(
        provider=provider.strip().lower(),
        configured=bool(stored_key),
        masked_api_key=settings_service.mask_api_key(stored_key),
    )


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
