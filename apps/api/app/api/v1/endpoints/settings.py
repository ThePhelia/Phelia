"""Settings management endpoints for provider credentials."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from app.core.runtime_integration_settings import (
    FIELD_BY_KEY,
    PROVIDER_BY_ID,
    runtime_integration_settings,
)
from app.core.runtime_service_settings import runtime_service_settings
from app.services.search.prowlarr.provider import ProwlarrProvider
from app.services.prowlarr_client import ProwlarrApiError, ProwlarrClient
from app.services.search.registry import search_registry


logger = logging.getLogger(__name__)

_PROWLARR_CONFIG_XML_PATHS = (
    Path("/mnt/prowlarr_config/config.xml"),
    Path("/config/config.xml"),
)

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
    providers: list[dict[str, Any]] = Field(default_factory=list)


class IntegrationUpdateRequest(BaseModel):
    value: str | None


class IntegrationsBulkUpdateRequest(BaseModel):
    integrations: dict[str, str | None]


class ProviderIntegrationUpdateRequest(BaseModel):
    values: dict[str, str | None]
    enabled: bool | None = None


class IntegrationsProviderBulkUpdateRequest(BaseModel):
    providers: dict[str, ProviderIntegrationUpdateRequest]


_URL_PATTERN = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")


def _is_valid_http_url(value: str) -> bool:
    return bool(_URL_PATTERN.match(value))


def _validate_provider_payloads(
    providers: dict[str, ProviderIntegrationUpdateRequest],
) -> tuple[dict[str, str | None], dict[str, bool]]:
    updates: dict[str, str | None] = {}
    enabled_updates: dict[str, bool] = {}
    for provider_name, payload in providers.items():
        if provider_name not in PROVIDER_BY_ID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "provider_not_found", "provider": provider_name},
            )
        if payload.enabled is not None:
            enabled_updates[provider_name] = payload.enabled
        if not payload.values:
            if payload.enabled is not None:
                continue
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "validation_failed",
                    "provider": provider_name,
                    "message": "Provider payload must include at least one field",
                },
            )
        for field_name, value in payload.values.items():
            integration_key = f"{provider_name}.{field_name}"
            if integration_key not in FIELD_BY_KEY:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "integration_not_found",
                        "provider": provider_name,
                        "field": field_name,
                        "integration_key": integration_key,
                        "message": f"Unknown field '{field_name}' for provider '{provider_name}'",
                    },
                )
            if value is not None and not isinstance(value, str):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "validation_failed",
                        "provider": provider_name,
                        "field": field_name,
                        "integration_key": integration_key,
                        "message": "Field value must be a string or null",
                    },
                )
            updates[integration_key] = value
    return updates, enabled_updates


def _build_integrations_response(*, include_secrets: bool = False) -> IntegrationsResponse:
    described = runtime_integration_settings.describe(include_secrets=include_secrets)
    fields = [
        IntegrationFieldResponse(key=key, **payload)
        for key, payload in described.items()
    ]
    return IntegrationsResponse(integrations=fields, providers=runtime_integration_settings.provider_catalog())


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


@router.patch("/integrations", response_model=IntegrationsResponse)
def patch_integrations(request: IntegrationsProviderBulkUpdateRequest) -> IntegrationsResponse:
    """Partially update integration settings by provider payload."""
    updates, enabled_updates = _validate_provider_payloads(request.providers)
    try:
        if updates:
            runtime_integration_settings.update_many(updates)
        for provider_id, enabled in enabled_updates.items():
            runtime_integration_settings.set_provider_enabled(provider_id, enabled)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_failed", "message": str(exc)},
        ) from exc

    logger.info(
        "Integration settings updated",
        extra={
            "changed_fields": sorted(updates.keys()),
            "changed_enabled": enabled_updates,
            "source": "settings.patch_integrations",
        },
    )
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
    provider_field_map = {
        "tmdb": "tmdb.api_key",
        "omdb": "omdb.api_key",
        "discogs": "discogs.token_or_key",
        "lastfm": "lastfm.api_key",
        "listenbrainz": "listenbrainz.token",
        "fanart": "fanart.api_key",
        "deezer": "deezer.api_key",
        "spotify_client_id": "spotify.client_id",
        "spotify_client_secret": "spotify.client_secret",
    }
    for provider, field_key in provider_field_map.items():
        configured = bool(runtime_integration_settings.get(field_key))
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
    provider_field_map = {
        "tmdb": "tmdb.api_key",
        "omdb": "omdb.api_key",
        "discogs": "discogs.token_or_key",
        "lastfm": "lastfm.api_key",
        "listenbrainz": "listenbrainz.token",
        "fanart": "fanart.api_key",
        "deezer": "deezer.api_key",
        "spotify_client_id": "spotify.client_id",
        "spotify_client_secret": "spotify.client_secret",
    }
    if provider not in provider_field_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "provider_not_found", "provider": provider},
        )

    configured = bool(runtime_integration_settings.get(provider_field_map[provider]))
    return ApiKeyResponse(
        provider=provider,
        configured=configured,
        value=None,  # Never expose actual API keys
    )


@router.post("/api-keys/{provider}", response_model=ApiKeyResponse)
def update_api_key(provider: str, request: ApiKeyUpdateRequest) -> ApiKeyResponse:
    """Update an API key for a specific provider."""
    provider_field_map = {
        "tmdb": "tmdb.api_key",
        "omdb": "omdb.api_key",
        "discogs": "discogs.token_or_key",
        "lastfm": "lastfm.api_key",
        "listenbrainz": "listenbrainz.token",
        "fanart": "fanart.api_key",
        "deezer": "deezer.api_key",
        "spotify_client_id": "spotify.client_id",
        "spotify_client_secret": "spotify.client_secret",
    }
    if provider not in provider_field_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "provider_not_found", "provider": provider},
        )

    runtime_integration_settings.set(provider_field_map[provider], request.value)
    configured = bool(runtime_integration_settings.get(provider_field_map[provider]))

    return ApiKeyResponse(
        provider=provider,
        configured=configured,
        value=None,  # Never expose actual API keys
    )


@router.post("/api-keys", response_model=ApiKeysResponse)
def update_api_keys(request: ApiKeysUpdateRequest) -> ApiKeysResponse:
    """Bulk update multiple API keys."""
    # Validate all providers exist before updating any
    provider_field_map = {
        "tmdb": "tmdb.api_key",
        "omdb": "omdb.api_key",
        "discogs": "discogs.token_or_key",
        "lastfm": "lastfm.api_key",
        "listenbrainz": "listenbrainz.token",
        "fanart": "fanart.api_key",
        "deezer": "deezer.api_key",
        "spotify_client_id": "spotify.client_id",
        "spotify_client_secret": "spotify.client_secret",
    }
    for provider in request.api_keys.keys():
        if provider not in provider_field_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "provider_not_found", "provider": provider},
            )

    # Update all keys
    runtime_integration_settings.update_many(
        {provider_field_map[provider]: value for provider, value in request.api_keys.items()}
    )

    # Return updated status
    api_keys = []
    for provider, field_key in provider_field_map.items():
        configured = bool(runtime_integration_settings.get(field_key))
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


class ProwlarrApiKeyDiscoveryAuthContext(BaseModel):
    username: str
    password: str


class ProwlarrApiKeyDiscoveryRequest(BaseModel):
    force_refresh: bool = False
    auth: ProwlarrApiKeyDiscoveryAuthContext | None = None


class ProwlarrApiKeyDiscoveryResponse(BaseModel):
    connected: bool
    api_key_configured: bool
    status: str
    message: str


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


class ProwlarrIndexerFieldResponse(BaseModel):
    name: str
    label: str
    value: Any | None = None
    type: str | None = None
    required: bool = False
    help_text: str | None = None
    options: list[dict[str, Any]] = Field(default_factory=list)


class ProwlarrIndexerResponse(BaseModel):
    id: int
    name: str
    enable: bool
    implementation: str | None = None
    implementation_name: str | None = None
    protocol: str | None = None
    app_profile_id: int | None = None
    priority: int | None = None
    fields: list[ProwlarrIndexerFieldResponse] = Field(default_factory=list)


class ProwlarrIndexerListResponse(BaseModel):
    indexers: list[ProwlarrIndexerResponse]


class ProwlarrIndexerTemplateResponse(BaseModel):
    id: int
    name: str
    implementation: str | None = None
    implementation_name: str | None = None
    protocol: str | None = None
    fields: list[ProwlarrIndexerFieldResponse] = Field(default_factory=list)


class ProwlarrIndexerTemplateListResponse(BaseModel):
    templates: list[ProwlarrIndexerTemplateResponse]


class ProwlarrIndexerUpsertRequest(BaseModel):
    name: str | None = None
    enable: bool | None = None
    app_profile_id: int | None = None
    priority: int | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class ProwlarrIndexerCreateRequest(ProwlarrIndexerUpsertRequest):
    template_id: int


class ProwlarrIndexerTestResponse(BaseModel):
    success: bool
    message: str
    details: Any | None = None


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


def _read_prowlarr_api_key_from_config_xml(path: Path) -> str | None:
    try:
        root = ET.parse(path).getroot()
    except FileNotFoundError:
        logger.info("Prowlarr volume discovery path missing", extra={"path": str(path)})
        return None
    except ET.ParseError as exc:
        logger.warning(
            "Prowlarr volume discovery failed to parse XML",
            extra={"path": str(path), "error": f"{type(exc).__name__}: {exc}"},
        )
        return None
    except OSError as exc:
        logger.warning(
            "Prowlarr volume discovery failed reading config",
            extra={"path": str(path), "error": f"{type(exc).__name__}: {exc}"},
        )
        return None

    api_key = root.findtext("ApiKey")
    if isinstance(api_key, str) and api_key.strip():
        logger.info("Prowlarr volume discovery succeeded", extra={"path": str(path)})
        return api_key.strip()
    logger.info("Prowlarr volume discovery missing ApiKey", extra={"path": str(path)})
    return None


def _discover_prowlarr_api_key_from_volume() -> tuple[str | None, str | None]:
    for path in _PROWLARR_CONFIG_XML_PATHS:
        api_key = _read_prowlarr_api_key_from_config_xml(path)
        if api_key:
            return api_key, str(path)
    return None, None


def _discover_prowlarr_api_key(
    *,
    force_refresh: bool = False,
    auth: ProwlarrApiKeyDiscoveryAuthContext | None = None,
) -> tuple[str | None, bool]:
    snapshot = runtime_service_settings.prowlarr_snapshot()
    logger.info("Prowlarr API key discovery started", extra={"prowlarr_url": snapshot.url})
    if snapshot.api_key and not force_refresh:
        logger.info("Prowlarr API key discovery finished using cached key")
        return snapshot.api_key, True
    request_auth = None
    if auth is not None and auth.username.strip():
        request_auth = httpx.BasicAuth(auth.username.strip(), auth.password)
    for path in ("/api/v1/config/host", "/api/v2.0/server/config"):
        url = f"{snapshot.url.rstrip('/')}" + path
        try:
            response = httpx.get(url, timeout=5.0, auth=request_auth)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(
                "Prowlarr HTTP discovery failed",
                extra={
                    "url": url,
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )
            continue
        try:
            payload = response.json()
        except ValueError:
            continue
        api_key = _extract_prowlarr_api_key(payload)
        if api_key:
            if runtime_service_settings.update_prowlarr(api_key=api_key):
                _refresh_prowlarr_provider()
            logger.info("Prowlarr API key discovery finished", extra={"source": "http", "url": url})
            return api_key, False
    api_key, config_path = _discover_prowlarr_api_key_from_volume()
    if api_key:
        if runtime_service_settings.update_prowlarr(api_key=api_key):
            _refresh_prowlarr_provider()
        logger.info(
            "Prowlarr API key discovery finished",
            extra={"source": "volume", "path": config_path},
        )
        return api_key, False

    logger.warning(
        "Prowlarr API key discovery failed",
        extra={"prowlarr_url": snapshot.url, "volume_paths": [str(path) for path in _PROWLARR_CONFIG_XML_PATHS]},
    )
    return None, False


def _autoload_prowlarr_api_key() -> None:
    _discover_prowlarr_api_key()


def _normalize_field(field: dict[str, Any]) -> ProwlarrIndexerFieldResponse:
    options = field.get("selectOptions") or field.get("options") or []
    if not isinstance(options, list):
        options = []
    return ProwlarrIndexerFieldResponse(
        name=str(field.get("name") or ""),
        label=str(field.get("label") or field.get("name") or ""),
        value=field.get("value"),
        type=field.get("type"),
        required=bool(field.get("required", False)),
        help_text=field.get("helpText") or field.get("helpTextWarning") or None,
        options=[item for item in options if isinstance(item, dict)],
    )


def _normalize_indexer(payload: dict[str, Any]) -> ProwlarrIndexerResponse:
    fields = payload.get("fields")
    normalized_fields = []
    if isinstance(fields, list):
        normalized_fields = [_normalize_field(field) for field in fields if isinstance(field, dict)]
    return ProwlarrIndexerResponse(
        id=int(payload.get("id") or 0),
        name=str(payload.get("name") or ""),
        enable=bool(payload.get("enable", False)),
        implementation=payload.get("implementation"),
        implementation_name=payload.get("implementationName"),
        protocol=payload.get("protocol"),
        app_profile_id=payload.get("appProfileId"),
        priority=payload.get("priority"),
        fields=normalized_fields,
    )


def _apply_settings(base: dict[str, Any], request: ProwlarrIndexerUpsertRequest) -> dict[str, Any]:
    payload = dict(base)
    if request.name is not None:
        payload["name"] = request.name
    if request.enable is not None:
        payload["enable"] = request.enable
    if request.app_profile_id is not None:
        payload["appProfileId"] = request.app_profile_id
    if request.priority is not None:
        payload["priority"] = request.priority

    fields = payload.get("fields")
    if isinstance(fields, list):
        by_name = {
            str(field.get("name")): field
            for field in fields
            if isinstance(field, dict) and isinstance(field.get("name"), str)
        }
        for key, value in request.settings.items():
            if key in by_name:
                by_name[key]["value"] = value
    return payload


async def _prowlarr_client() -> ProwlarrClient:
    _autoload_prowlarr_api_key()
    return ProwlarrClient()


def _raise_prowlarr_error(exc: ProwlarrApiError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={
            "error": "prowlarr_request_failed",
            "message": exc.message,
            "prowlarr": exc.details,
        },
    ) from exc



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
            detail={"error": "validation_failed", "field": "url", "message": "url cannot be blank"},
        )
    if url is not None and not _is_valid_http_url(url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_failed", "field": "url", "message": "url must be a valid http(s) URL"},
        )
    if api_key is not None and len(api_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_failed", "field": "api_key", "message": "api_key must be at least 8 characters"},
        )

    runtime_service_settings.update_prowlarr(url=url, api_key=api_key or None)
    _refresh_prowlarr_provider()
    changed_fields = sorted(fields_set.intersection({"url", "api_key"}))
    if changed_fields:
        logger.info("Prowlarr settings updated", extra={"changed_fields": changed_fields})
    snapshot = runtime_service_settings.prowlarr_snapshot()
    return ProwlarrSettingsResponse(
        url=snapshot.url,
        api_key_configured=bool(snapshot.api_key),
    )


@router.post("/services/prowlarr/discover-api-key", response_model=ProwlarrApiKeyDiscoveryResponse)
def discover_prowlarr_api_key(request: ProwlarrApiKeyDiscoveryRequest) -> ProwlarrApiKeyDiscoveryResponse:
    snapshot = runtime_service_settings.prowlarr_snapshot()
    if not snapshot.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "prowlarr_url_missing",
                "message": "Set the Prowlarr base URL before fetching the API key.",
                "manual_entry_hint": "Enter the API key manually if automatic discovery cannot be used.",
            },
        )

    api_key, from_cache = _discover_prowlarr_api_key(
        force_refresh=request.force_refresh,
        auth=request.auth,
    )
    if api_key:
        return ProwlarrApiKeyDiscoveryResponse(
            connected=True,
            api_key_configured=True,
            status="cached" if from_cache else "success",
            message="Using cached API key." if from_cache else "Fetched and saved API key from Prowlarr.",
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "error": "prowlarr_api_key_discovery_failed",
            "message": (
                "Unable to discover a Prowlarr API key from the supported config endpoints. "
                "Verify URL/authentication and try again."
            ),
            "manual_entry_hint": "Enter the API key manually in Prowlarr settings as a fallback.",
            "supported_endpoints": ["/api/v1/config/host", "/api/v2.0/server/config"],
        },
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
            detail={"error": "validation_failed", "field": "url", "message": "url cannot be blank"},
        )
    if url is not None and not _is_valid_http_url(url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_failed", "field": "url", "message": "url must be a valid http(s) URL"},
        )
    if username is not None and not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_failed", "field": "username", "message": "username cannot be blank"},
        )
    if password is not None and len(password) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_failed", "field": "password", "message": "password must be at least 4 characters"},
        )

    runtime_service_settings.update_qbittorrent(
        url=url,
        username=username,
        password=password,
    )
    _refresh_prowlarr_provider()
    changed_fields = sorted(fields_set.intersection({"url", "username", "password"}))
    if changed_fields:
        logger.info("qBittorrent settings updated", extra={"changed_fields": changed_fields})
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
            detail={"error": "validation_failed", "field": "default_dir", "message": "default_dir cannot be blank"},
        )
    if allowed_dirs is not None and not allowed_dirs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_failed", "field": "allowed_dirs", "message": "allowed_dirs cannot be empty"},
        )

    runtime_service_settings.update_downloads(
        allowed_dirs=allowed_dirs,
        default_dir=default_dir,
    )
    changed_fields = sorted(fields_set.intersection({"allowed_dirs", "default_dir"}))
    if changed_fields:
        logger.info("Download settings updated", extra={"changed_fields": changed_fields})
    snapshot = runtime_service_settings.download_snapshot()
    return DownloadSettingsResponse(
        allowed_dirs=snapshot.allowed_dirs,
        default_dir=snapshot.default_dir,
    )


@router.get("/services/prowlarr/indexers", response_model=ProwlarrIndexerListResponse)
async def list_prowlarr_indexers() -> ProwlarrIndexerListResponse:
    client = await _prowlarr_client()
    try:
        indexers = await client.list_indexers()
    except ProwlarrApiError as exc:
        _raise_prowlarr_error(exc)
    return ProwlarrIndexerListResponse(
        indexers=[_normalize_indexer(indexer) for indexer in indexers if isinstance(indexer, dict)]
    )


@router.get("/services/prowlarr/indexer-templates", response_model=ProwlarrIndexerTemplateListResponse)
async def list_prowlarr_indexer_templates() -> ProwlarrIndexerTemplateListResponse:
    client = await _prowlarr_client()
    try:
        templates = await client.list_indexer_templates()
    except ProwlarrApiError as exc:
        _raise_prowlarr_error(exc)

    normalized = []
    for template in templates:
        if not isinstance(template, dict):
            continue
        fields = template.get("fields") if isinstance(template.get("fields"), list) else []
        normalized.append(
            ProwlarrIndexerTemplateResponse(
                id=int(template.get("id") or 0),
                name=str(template.get("name") or ""),
                implementation=template.get("implementation"),
                implementation_name=template.get("implementationName"),
                protocol=template.get("protocol"),
                fields=[_normalize_field(field) for field in fields if isinstance(field, dict)],
            )
        )

    return ProwlarrIndexerTemplateListResponse(templates=normalized)


@router.post("/services/prowlarr/indexers", response_model=ProwlarrIndexerResponse)
async def create_prowlarr_indexer(request: ProwlarrIndexerCreateRequest) -> ProwlarrIndexerResponse:
    client = await _prowlarr_client()
    try:
        templates = await client.list_indexer_templates()
    except ProwlarrApiError as exc:
        _raise_prowlarr_error(exc)

    template = next(
        (
            item
            for item in templates
            if isinstance(item, dict) and int(item.get("id") or 0) == request.template_id
        ),
        None,
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "template_not_found", "template_id": request.template_id},
        )

    payload = _apply_settings(template, request)

    try:
        created = await client.create_indexer(payload)
    except ProwlarrApiError as exc:
        _raise_prowlarr_error(exc)
    return _normalize_indexer(created)


@router.put("/services/prowlarr/indexers/{indexer_id}", response_model=ProwlarrIndexerResponse)
async def update_prowlarr_indexer(indexer_id: int, request: ProwlarrIndexerUpsertRequest) -> ProwlarrIndexerResponse:
    client = await _prowlarr_client()
    try:
        indexers = await client.list_indexers()
    except ProwlarrApiError as exc:
        _raise_prowlarr_error(exc)

    current = next(
        (
            item
            for item in indexers
            if isinstance(item, dict) and int(item.get("id") or 0) == indexer_id
        ),
        None,
    )
    if current is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "indexer_not_found", "indexer_id": indexer_id},
        )

    payload = _apply_settings(current, request)
    try:
        updated = await client.update_indexer(indexer_id, payload)
    except ProwlarrApiError as exc:
        _raise_prowlarr_error(exc)
    return _normalize_indexer(updated)


@router.delete("/services/prowlarr/indexers/{indexer_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_prowlarr_indexer(indexer_id: int) -> Response:
    client = await _prowlarr_client()
    try:
        await client.delete_indexer(indexer_id)
    except ProwlarrApiError as exc:
        _raise_prowlarr_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/services/prowlarr/indexers/{indexer_id}/test", response_model=ProwlarrIndexerTestResponse)
async def test_prowlarr_indexer(indexer_id: int) -> ProwlarrIndexerTestResponse:
    client = await _prowlarr_client()
    try:
        indexers = await client.list_indexers()
    except ProwlarrApiError as exc:
        _raise_prowlarr_error(exc)

    current = next(
        (
            item
            for item in indexers
            if isinstance(item, dict) and int(item.get("id") or 0) == indexer_id
        ),
        None,
    )
    if current is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "indexer_not_found", "indexer_id": indexer_id},
        )

    try:
        result = await client.test_indexer(current)
    except ProwlarrApiError as exc:
        _raise_prowlarr_error(exc)

    return ProwlarrIndexerTestResponse(success=True, message="Indexer test succeeded.", details=result)
