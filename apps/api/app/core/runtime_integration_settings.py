from __future__ import annotations

import os
import re
from dataclasses import dataclass
from threading import RLock

from app.core.config import settings
from app.core.secure_store import SecretsStore, get_secrets_store

_INTEGRATIONS_SECTION = "integrations"
_MASK = "••••••••"


@dataclass(frozen=True, slots=True)
class IntegrationFieldSpec:
    key: str
    label: str
    required: bool
    masked_at_rest: bool
    validation_rule: str
    secret: bool = True


@dataclass(frozen=True, slots=True)
class IntegrationProviderSpec:
    id: str
    name: str
    description: str
    fields: tuple[str, ...]


INTEGRATION_FIELDS: tuple[IntegrationFieldSpec, ...] = (
    IntegrationFieldSpec("tmdb.api_key", "TMDb API Key", False, True, "min_length:16"),
    IntegrationFieldSpec("omdb.api_key", "OMDb API Key", False, True, "min_length:8"),
    IntegrationFieldSpec("lastfm.api_key", "Last.fm API Key", False, True, "min_length:8"),
    IntegrationFieldSpec("listenbrainz.token", "ListenBrainz Token", False, True, "min_length:8"),
    IntegrationFieldSpec("fanart.api_key", "Fanart API Key", False, True, "min_length:8"),
    IntegrationFieldSpec("deezer.api_key", "Deezer API Key", False, True, "min_length:8"),
    IntegrationFieldSpec("spotify.client_id", "Spotify Client ID", False, True, "min_length:8"),
    IntegrationFieldSpec("spotify.client_secret", "Spotify Client Secret", False, True, "min_length:8"),
    IntegrationFieldSpec("discogs.token_or_key", "Discogs Token or API Key", False, True, "min_length:8"),
    IntegrationFieldSpec("musicbrainz.client_id", "MusicBrainz Client ID", False, True, "min_length:2"),
    IntegrationFieldSpec("musicbrainz.client_secret", "MusicBrainz Client Secret", False, True, "min_length:2"),
    IntegrationFieldSpec(
        "musicbrainz.user_agent",
        "MusicBrainz User Agent",
        False,
        False,
        r"regex:^[A-Za-z0-9][A-Za-z0-9 ._\-/()@:+]{1,127}$",
        False,
    ),
)

INTEGRATION_PROVIDERS: tuple[IntegrationProviderSpec, ...] = (
    IntegrationProviderSpec("tmdb", "TMDb", "Movie and TV metadata and artwork.", ("tmdb.api_key",)),
    IntegrationProviderSpec("omdb", "OMDb", "IMDb ratings and movie metadata fallback.", ("omdb.api_key",)),
    IntegrationProviderSpec("lastfm", "Last.fm", "Music tags and popularity metadata.", ("lastfm.api_key",)),
    IntegrationProviderSpec("listenbrainz", "ListenBrainz", "Listening history and artist insights.", ("listenbrainz.token",)),
    IntegrationProviderSpec("fanart", "Fanart.tv", "Additional images and artwork.", ("fanart.api_key",)),
    IntegrationProviderSpec("deezer", "Deezer", "Music discovery metadata enrichment.", ("deezer.api_key",)),
    IntegrationProviderSpec("spotify", "Spotify", "Spotify metadata integration.", ("spotify.client_id", "spotify.client_secret")),
    IntegrationProviderSpec("discogs", "Discogs", "Album and artist metadata enrichment.", ("discogs.token_or_key",)),
    IntegrationProviderSpec(
        "musicbrainz",
        "MusicBrainz",
        "MusicBrainz search and release metadata.",
        ("musicbrainz.client_id", "musicbrainz.client_secret", "musicbrainz.user_agent"),
    ),
)

FIELD_BY_KEY = {field.key: field for field in INTEGRATION_FIELDS}
PROVIDER_BY_ID = {provider.id: provider for provider in INTEGRATION_PROVIDERS}

LEGACY_KEY_MAP = {
    "tmdb.api_key": ("tmdb", "TMDB_API_KEY"),
    "omdb.api_key": ("omdb", "OMDB_API_KEY"),
    "lastfm.api_key": ("lastfm", "LASTFM_API_KEY"),
    "listenbrainz.token": ("listenbrainz", "LISTENBRAINZ_TOKEN"),
    "fanart.api_key": ("fanart", "FANART_API_KEY"),
    "deezer.api_key": ("deezer", "DEEZER_API_KEY"),
    "spotify.client_id": ("spotify_client_id", "SPOTIFY_CLIENT_ID"),
    "spotify.client_secret": ("spotify_client_secret", "SPOTIFY_CLIENT_SECRET"),
    "discogs.token_or_key": ("discogs", "DISCOGS_TOKEN"),
    "musicbrainz.user_agent": ("musicbrainz_user_agent", "MB_USER_AGENT"),
}


def _validate(field: IntegrationFieldSpec, value: str | None) -> str | None:
    cleaned = value.strip() if isinstance(value, str) else None
    if not cleaned:
        return None
    if field.validation_rule.startswith("min_length:"):
        min_length = int(field.validation_rule.split(":", maxsplit=1)[1])
        if len(cleaned) < min_length:
            raise ValueError(f"{field.key} must be at least {min_length} characters")
    if field.validation_rule.startswith("regex:"):
        pattern = field.validation_rule.split(":", maxsplit=1)[1]
        if not re.fullmatch(pattern, cleaned):
            raise ValueError(f"{field.key} format is invalid")
    return cleaned


class RuntimeIntegrationSettings:
    def __init__(self, store: SecretsStore | None = None) -> None:
        self._lock = RLock()
        self._store = store or get_secrets_store()
        self._values: dict[str, str | None] = {}
        self._enabled: dict[str, bool] = {}
        self.reset_to_defaults()

    def _defaults(self) -> tuple[dict[str, str | None], dict[str, bool]]:
        defaults = {field.key: None for field in INTEGRATION_FIELDS}
        enabled = {provider.id: False for provider in INTEGRATION_PROVIDERS}

        for field_key, (_, env_name) in LEGACY_KEY_MAP.items():
            env = os.environ.get(env_name)
            if env is None:
                env = getattr(settings, env_name, None)
            defaults[field_key] = env.strip() if isinstance(env, str) and env.strip() else None

        for provider in INTEGRATION_PROVIDERS:
            enabled[provider.id] = any(defaults.get(key) for key in provider.fields)
        return defaults, enabled

    def _legacy_store_migration(self, values: dict[str, str | None]) -> dict[str, str | None]:
        migrated: dict[str, str | None] = {}
        for field_key, (legacy_store_key, _) in LEGACY_KEY_MAP.items():
            legacy_value = self._store.get(legacy_store_key)
            if isinstance(legacy_value, str) and legacy_value.strip():
                values[field_key] = legacy_value.strip()
                migrated[field_key] = values[field_key]
        return migrated

    def reset_to_defaults(self) -> None:
        with self._lock:
            values, enabled = self._defaults()
            persisted = self._store.load_section(_INTEGRATIONS_SECTION)
            if isinstance(persisted, dict):
                for key, value in persisted.get("values", {}).items() if isinstance(persisted.get("values"), dict) else []:
                    if key in FIELD_BY_KEY and isinstance(value, str) and value.strip():
                        values[key] = value.strip()
                for provider_id, value in persisted.get("enabled", {}).items() if isinstance(persisted.get("enabled"), dict) else []:
                    if provider_id in PROVIDER_BY_ID:
                        enabled[provider_id] = bool(value)
                for key, value in persisted.items():
                    if key in FIELD_BY_KEY and isinstance(value, str) and value.strip():
                        values[key] = value.strip()
            migrated = self._legacy_store_migration(values)
            self._values = values
            self._enabled = enabled
            if migrated or not persisted:
                self._persist()

    def _persist(self) -> None:
        payload = {
            "values": {
                key: value
                for key, value in self._values.items()
                if isinstance(value, str) and value.strip()
            },
            "enabled": dict(self._enabled),
        }
        self._store.save_section(_INTEGRATIONS_SECTION, payload)

    def get(self, key: str) -> str | None:
        with self._lock:
            return self._values.get(key)

    def set(self, key: str, value: str | None) -> bool:
        spec = FIELD_BY_KEY.get(key)
        if spec is None:
            raise KeyError(key)
        validated = _validate(spec, value)
        with self._lock:
            if self._values.get(key) == validated:
                return False
            self._values[key] = validated
            self._persist()
            return True

    def update_many(self, values: dict[str, str | None]) -> bool:
        changed = False
        for key, value in values.items():
            changed |= self.set(key, value)
        return changed

    def provider_enabled(self, provider_id: str) -> bool:
        with self._lock:
            return bool(self._enabled.get(provider_id, False))

    def set_provider_enabled(self, provider_id: str, enabled: bool) -> bool:
        if provider_id not in PROVIDER_BY_ID:
            raise KeyError(provider_id)
        with self._lock:
            if self._enabled.get(provider_id) == enabled:
                return False
            self._enabled[provider_id] = enabled
            self._persist()
            return True

    def describe(self, *, include_secrets: bool = False) -> dict[str, dict[str, str | bool | None]]:
        with self._lock:
            result: dict[str, dict[str, str | bool | None]] = {}
            for spec in INTEGRATION_FIELDS:
                value = self._values.get(spec.key)
                displayed: str | None = value
                if spec.secret and not include_secrets and value:
                    displayed = _MASK
                result[spec.key] = {
                    "label": spec.label,
                    "required": spec.required,
                    "masked_at_rest": spec.masked_at_rest,
                    "validation_rule": spec.validation_rule,
                    "configured": bool(value),
                    "value": displayed,
                }
            return result

    def provider_catalog(self) -> list[dict[str, str | bool]]:
        described = self.describe(include_secrets=False)
        with self._lock:
            catalog: list[dict[str, str | bool]] = []
            for provider in INTEGRATION_PROVIDERS:
                configured = any(bool(self._values.get(key)) for key in provider.fields)
                catalog.append(
                    {
                        "id": provider.id,
                        "name": provider.name,
                        "description": provider.description,
                        "enabled": bool(self._enabled.get(provider.id, False)),
                        "configured": configured,
                    }
                )
            return catalog


runtime_integration_settings = RuntimeIntegrationSettings()

__all__ = [
    "IntegrationFieldSpec",
    "IntegrationProviderSpec",
    "INTEGRATION_FIELDS",
    "INTEGRATION_PROVIDERS",
    "FIELD_BY_KEY",
    "PROVIDER_BY_ID",
    "RuntimeIntegrationSettings",
    "runtime_integration_settings",
]
