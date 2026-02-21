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


INTEGRATION_FIELDS: tuple[IntegrationFieldSpec, ...] = (
    IntegrationFieldSpec(
        key="tmdb.api_key",
        label="TMDb API Key",
        required=False,
        masked_at_rest=True,
        validation_rule="min_length:16",
    ),
    IntegrationFieldSpec(
        key="discogs.token_or_key",
        label="Discogs Token or API Key",
        required=False,
        masked_at_rest=True,
        validation_rule="min_length:8",
    ),
    IntegrationFieldSpec(
        key="musicbrainz.client_name",
        label="MusicBrainz Client Name",
        required=True,
        masked_at_rest=False,
        validation_rule=r"regex:^[A-Za-z0-9][A-Za-z0-9 ._-]{1,63}$",
        secret=False,
    ),
    IntegrationFieldSpec(
        key="musicbrainz.client_version",
        label="MusicBrainz Client Version",
        required=True,
        masked_at_rest=False,
        validation_rule=r"regex:^v?\d+(?:\.\d+){0,2}(?:[-+][A-Za-z0-9._-]+)?$",
        secret=False,
    ),
    IntegrationFieldSpec(
        key="musicbrainz.contact",
        label="MusicBrainz Contact URL or Email",
        required=True,
        masked_at_rest=False,
        validation_rule=r"regex:^(https?://\S+|[^\s@]+@[^\s@]+\.[^\s@]+)$",
        secret=False,
    ),
)

FIELD_BY_KEY = {field.key: field for field in INTEGRATION_FIELDS}

LEGACY_KEY_MAP = {
    "tmdb.api_key": ("tmdb", "TMDB_API_KEY"),
    "discogs.token_or_key": ("discogs", "DISCOGS_TOKEN"),
}


def _parse_musicbrainz_user_agent(value: str | None) -> tuple[str | None, str | None, str | None]:
    if not value:
        return None, None, None
    match = re.match(r"\s*([^/]+)/([^\s]+)\s*\(([^)]+)\)\s*", value)
    if not match:
        return value.strip() or None, None, None
    return (part.strip() or None for part in match.groups())


def _validate(field: IntegrationFieldSpec, value: str | None) -> str | None:
    cleaned = value.strip() if isinstance(value, str) else None
    if not cleaned:
        return None
    if field.key == "tmdb.api_key" and len(cleaned) < 16:
        raise ValueError("tmdb.api_key must be at least 16 characters")
    if field.key == "discogs.token_or_key" and len(cleaned) < 8:
        raise ValueError("discogs.token_or_key must be at least 8 characters")
    if field.key == "musicbrainz.client_name" and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]{1,63}", cleaned):
        raise ValueError("musicbrainz.client_name must be 2-64 chars and start with alphanumeric")
    if field.key == "musicbrainz.client_version" and not re.fullmatch(r"v?\d+(?:\.\d+){0,2}(?:[-+][A-Za-z0-9._-]+)?", cleaned):
        raise ValueError("musicbrainz.client_version must look like 1.0 or v1.0.0")
    if field.key == "musicbrainz.contact" and not re.fullmatch(r"(https?://\S+|[^\s@]+@[^\s@]+\.[^\s@]+)", cleaned):
        raise ValueError("musicbrainz.contact must be an email or URL")
    return cleaned


class RuntimeIntegrationSettings:
    def __init__(self, store: SecretsStore | None = None) -> None:
        self._lock = RLock()
        self._store = store or get_secrets_store()
        self._values: dict[str, str | None] = {}
        self.reset_to_defaults()

    def _defaults(self) -> dict[str, str | None]:
        defaults = {field.key: None for field in INTEGRATION_FIELDS}
        for field_key, (_, env_name) in LEGACY_KEY_MAP.items():
            env = os.environ.get(env_name)
            if env is None:
                env = getattr(settings, env_name, None)
            defaults[field_key] = env.strip() if isinstance(env, str) and env.strip() else None

        mb_name, mb_version, mb_contact = _parse_musicbrainz_user_agent(
            os.environ.get("MB_USER_AGENT") or getattr(settings, "MB_USER_AGENT", None)
        )
        defaults["musicbrainz.client_name"] = mb_name
        defaults["musicbrainz.client_version"] = mb_version
        defaults["musicbrainz.contact"] = mb_contact
        return defaults

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
            values = self._defaults()
            persisted = self._store.load_section(_INTEGRATIONS_SECTION)
            if isinstance(persisted, dict):
                for key, value in persisted.items():
                    if key in FIELD_BY_KEY and isinstance(value, str) and value.strip():
                        values[key] = value.strip()
            migrated = self._legacy_store_migration(values)
            self._values = values
            if migrated or not persisted:
                self._persist()

    def _persist(self) -> None:
        payload = {
            key: value
            for key, value in self._values.items()
            if isinstance(value, str) and value.strip()
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

    def musicbrainz_user_agent(self) -> str | None:
        with self._lock:
            name = self._values.get("musicbrainz.client_name")
            version = self._values.get("musicbrainz.client_version")
            contact = self._values.get("musicbrainz.contact")
            if name and version and contact:
                return f"{name}/{version} ({contact})"
            return None


runtime_integration_settings = RuntimeIntegrationSettings()

__all__ = [
    "IntegrationFieldSpec",
    "INTEGRATION_FIELDS",
    "RuntimeIntegrationSettings",
    "runtime_integration_settings",
]
