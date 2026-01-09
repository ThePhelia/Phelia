"""Settings management endpoints for provider credentials."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.runtime_settings import runtime_settings
from app.core.runtime_service_settings import runtime_service_settings
from app.services.search.jackett.provider import JackettProvider
from app.services.search.registry import search_registry


logger = logging.getLogger(__name__)

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


class JackettSettingsResponse(BaseModel):
    url: str
    api_key_configured: bool


class JackettSettingsUpdateRequest(BaseModel):
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
    jackett: JackettSettingsResponse
    qbittorrent: QbittorrentSettingsResponse
    downloads: DownloadSettingsResponse


def _refresh_jackett_provider() -> None:
    try:
        settings = runtime_service_settings.jackett_settings()
        search_registry.register(
            JackettProvider(settings, logger=logging.getLogger("phelia.jackett"))
        )
    except Exception:
        logger.exception("Failed to refresh Jackett provider settings")



@router.get("/services", response_model=ServiceSettingsResponse)
def get_service_settings() -> ServiceSettingsResponse:
    jackett = runtime_service_settings.jackett_snapshot()
    qbittorrent = runtime_service_settings.qbittorrent_snapshot()
    downloads = runtime_service_settings.download_snapshot()
    return ServiceSettingsResponse(
        jackett=JackettSettingsResponse(
            url=jackett.url,
            api_key_configured=bool(jackett.api_key),
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


@router.post("/services/jackett", response_model=JackettSettingsResponse)
def update_jackett_settings(request: JackettSettingsUpdateRequest) -> JackettSettingsResponse:
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

    runtime_service_settings.update_jackett(url=url, api_key=api_key or None)
    _refresh_jackett_provider()
    snapshot = runtime_service_settings.jackett_snapshot()
    return JackettSettingsResponse(
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
    _refresh_jackett_provider()
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
