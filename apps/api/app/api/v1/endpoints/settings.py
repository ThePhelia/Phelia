"""Settings management endpoints for provider credentials."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.core.runtime_settings import runtime_settings
from app.core.runtime_integration_settings import (
    FIELD_BY_KEY,
    runtime_integration_settings,
)
from app.core.runtime_service_settings import runtime_service_settings
from app.services.search.prowlarr.provider import ProwlarrProvider
from app.services.search.registry import search_registry


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


class IntegrationFieldResponse(BaseModel):
    key: str
    label: str
    required: bool
    masked_at_rest: bool
    validation_rule: str
    configured: bool
    value: str | None = None


class IntegrationsResponse(BaseModel):
    integrations: list[IntegrationFieldResponse]


class IntegrationUpdateRequest(BaseModel):
    value: str | None


class IntegrationsBulkUpdateRequest(BaseModel):
    integrations: dict[str, str | None]


def _build_integrations_response(*, include_secrets: bool = False) -> IntegrationsResponse:
    described = runtime_integration_settings.describe(include_secrets=include_secrets)
    fields = [
        IntegrationFieldResponse(key=key, **payload)
        for key, payload in described.items()
    ]
    return IntegrationsResponse(integrations=fields)


@router.get("/integrations", response_model=IntegrationsResponse)
def get_integrations(include_secrets: bool = Query(default=False)) -> IntegrationsResponse:
    """Get third-party integration settings with metadata and masked secret values."""
    return _build_integrations_response(include_secrets=include_secrets)


@router.post("/integrations/{integration_key}", response_model=IntegrationFieldResponse)
def update_integration(
    integration_key: str, request: IntegrationUpdateRequest
) -> IntegrationFieldResponse:
    """Update a third-party integration field."""
    if integration_key not in FIELD_BY_KEY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "integration_not_found", "integration_key": integration_key},
        )
    try:
        runtime_integration_settings.set(integration_key, request.value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_failed", "integration_key": integration_key, "message": str(exc)},
        ) from exc

    described = runtime_integration_settings.describe(include_secrets=False)[integration_key]
    return IntegrationFieldResponse(key=integration_key, **described)


@router.post("/integrations", response_model=IntegrationsResponse)
def update_integrations(request: IntegrationsBulkUpdateRequest) -> IntegrationsResponse:
    """Bulk update third-party integration fields."""
    for integration_key in request.integrations.keys():
        if integration_key not in FIELD_BY_KEY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "integration_not_found", "integration_key": integration_key},
            )
    try:
        runtime_integration_settings.update_many(request.integrations)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_failed", "message": str(exc)},
        ) from exc

    return _build_integrations_response(include_secrets=False)


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


class ProwlarrSettingsResponse(BaseModel):
    url: str
    api_key_configured: bool


class ProwlarrSettingsUpdateRequest(BaseModel):
    url: str | None = None
    api_key: str | None = None


class QbittorrentSettingsResponse(BaseModel):
    url: str
    username: str
    password_configured: bool


class QbittorrentSettingsUpdateRequest(BaseModel):
    url: str | None = None
    username: str | None = None
    password: str | None = None


class DownloadSettingsResponse(BaseModel):
    allowed_dirs: list[str]
    default_dir: str


class DownloadSettingsUpdateRequest(BaseModel):
    allowed_dirs: list[str] | None = None
    default_dir: str | None = None


class ServiceSettingsResponse(BaseModel):
    prowlarr: ProwlarrSettingsResponse
    qbittorrent: QbittorrentSettingsResponse
    downloads: DownloadSettingsResponse


def _refresh_prowlarr_provider() -> None:
    try:
        settings = runtime_service_settings.prowlarr_settings()
        search_registry.register(
            ProwlarrProvider(settings, logger=logging.getLogger("phelia.search.prowlarr"))
        )
    except Exception:
        logger.exception("Failed to refresh Prowlarr provider settings")


def _extract_prowlarr_api_key(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(key, str) and key.lower().replace("_", "") == "apikey":
                if isinstance(value, str) and value.strip():
                    return value.strip()
            candidate = _extract_prowlarr_api_key(value)
            if candidate:
                return candidate
    elif isinstance(payload, list):
        for value in payload:
            candidate = _extract_prowlarr_api_key(value)
            if candidate:
                return candidate
    return None


def _autoload_prowlarr_api_key() -> None:
    snapshot = runtime_service_settings.prowlarr_snapshot()
    if snapshot.api_key:
        return
    for path in ("/api/v1/config/host", "/api/v2.0/server/config"):
        url = f"{snapshot.url.rstrip('/')}" + path
        try:
            response = httpx.get(url, timeout=5.0)
            response.raise_for_status()
        except httpx.HTTPError:
            continue
        try:
            payload = response.json()
        except ValueError:
            continue
        api_key = _extract_prowlarr_api_key(payload)
        if api_key and runtime_service_settings.update_prowlarr(api_key=api_key):
            _refresh_prowlarr_provider()
        if api_key:
            return



@router.get("/services", response_model=ServiceSettingsResponse)
def get_service_settings() -> ServiceSettingsResponse:
    _autoload_prowlarr_api_key()
    prowlarr = runtime_service_settings.prowlarr_snapshot()
    qbittorrent = runtime_service_settings.qbittorrent_snapshot()
    downloads = runtime_service_settings.download_snapshot()
    return ServiceSettingsResponse(
        prowlarr=ProwlarrSettingsResponse(
            url=prowlarr.url,
            api_key_configured=bool(prowlarr.api_key),
        ),
        qbittorrent=QbittorrentSettingsResponse(
            url=qbittorrent.url,
            username=qbittorrent.username,
            password_configured=bool(qbittorrent.password),
        ),
        downloads=DownloadSettingsResponse(
            allowed_dirs=downloads.allowed_dirs,
            default_dir=downloads.default_dir,
        ),
    )


@router.post("/services/prowlarr", response_model=ProwlarrSettingsResponse)
def update_prowlarr_settings(request: ProwlarrSettingsUpdateRequest) -> ProwlarrSettingsResponse:
    fields_set = request.model_fields_set
    url = None
    api_key = None
    if "url" in fields_set:
        url = request.url.strip() if request.url is not None else ""
    if "api_key" in fields_set:
        api_key = request.api_key.strip() if request.api_key is not None else ""

    if url is not None and not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_url"},
        )

    runtime_service_settings.update_prowlarr(url=url, api_key=api_key or None)
    _refresh_prowlarr_provider()
    snapshot = runtime_service_settings.prowlarr_snapshot()
    return ProwlarrSettingsResponse(
        url=snapshot.url,
        api_key_configured=bool(snapshot.api_key),
    )



@router.post("/services/qbittorrent", response_model=QbittorrentSettingsResponse)
def update_qbittorrent_settings(
    request: QbittorrentSettingsUpdateRequest,
) -> QbittorrentSettingsResponse:
    fields_set = request.model_fields_set
    url = None
    username = None
    password = None
    if "url" in fields_set:
        url = request.url.strip() if request.url is not None else ""
    if "username" in fields_set:
        username = request.username.strip() if request.username is not None else ""
    if "password" in fields_set:
        password = request.password.strip() if request.password is not None else ""

    if url is not None and not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_url"},
        )

    runtime_service_settings.update_qbittorrent(
        url=url,
        username=username,
        password=password,
    )
    _refresh_prowlarr_provider()
    snapshot = runtime_service_settings.qbittorrent_snapshot()
    return QbittorrentSettingsResponse(
        url=snapshot.url,
        username=snapshot.username,
        password_configured=bool(snapshot.password),
    )


@router.post("/services/downloads", response_model=DownloadSettingsResponse)
def update_download_settings(
    request: DownloadSettingsUpdateRequest,
) -> DownloadSettingsResponse:
    fields_set = request.model_fields_set
    default_dir = None
    allowed_dirs = None
    if "default_dir" in fields_set:
        default_dir = request.default_dir.strip() if request.default_dir is not None else ""
    if "allowed_dirs" in fields_set:
        allowed_dirs = request.allowed_dirs
    if allowed_dirs is not None:
        allowed_dirs = [path.strip() for path in allowed_dirs if path.strip()]
    if default_dir is not None and not default_dir:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_default_dir"},
        )

    runtime_service_settings.update_downloads(
        allowed_dirs=allowed_dirs,
        default_dir=default_dir,
    )
    snapshot = runtime_service_settings.download_snapshot()
    return DownloadSettingsResponse(
        allowed_dirs=snapshot.allowed_dirs,
        default_dir=snapshot.default_dir,
    )
