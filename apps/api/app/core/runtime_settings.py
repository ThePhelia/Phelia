"""Runtime provider credential storage with hot-reload support."""

from __future__ import annotations

import os
from collections.abc import Callable
from threading import RLock
from typing import Optional

from app.core.config import settings
from app.core.secure_store import SecretsStore, get_secrets_store

PROVIDER_ENV_MAP: dict[str, str] = {
    "omdb": "OMDB_API_KEY",
    "discogs": "DISCOGS_TOKEN",
    "lastfm": "LASTFM_API_KEY",
    "listenbrainz": "LISTENBRAINZ_TOKEN",
    "spotify_client_id": "SPOTIFY_CLIENT_ID",
    "spotify_client_secret": "SPOTIFY_CLIENT_SECRET",
    "fanart": "FANART_API_KEY",
    "deezer": "DEEZER_API_KEY",
}

SUPPORTED_PROVIDER_SLUGS = tuple(PROVIDER_ENV_MAP.keys())


def normalize_provider(slug: str) -> str:
    return slug.strip().lower()


class RuntimeProviderSettings:
    """Manage provider API keys that can be updated at runtime."""

    def __init__(self, store: SecretsStore | None = None) -> None:
        self._lock = RLock()
        self._values: dict[str, Optional[str]] = {}
        self._store = store or get_secrets_store()
        self.reset_to_env()

    def reset_to_env(self) -> None:
        """Reset all provider keys back to environment defaults."""

        with self._lock:
            values: dict[str, Optional[str]] = {}
            store_updates: dict[str, Optional[str]] = {}
            for slug, env_name in PROVIDER_ENV_MAP.items():
                value = os.environ.get(env_name)
                if value is None:
                    value = getattr(settings, env_name, None)
                values[slug] = value
            for slug in SUPPORTED_PROVIDER_SLUGS:
                stored_value = self._store.get(slug)
                if isinstance(stored_value, str) and stored_value.strip():
                    values[slug] = stored_value
                elif values.get(slug):
                    store_updates[slug] = values[slug]
            self._values = values
            if store_updates:
                self._store.set_many(store_updates)

    def get(self, slug: str) -> Optional[str]:
        normalized = normalize_provider(slug)
        with self._lock:
            return self._values.get(normalized)

    def set(self, slug: str, value: Optional[str]) -> bool:
        """Update ``slug`` with ``value`` and return ``True`` when it changed."""

        normalized = normalize_provider(slug)
        new_value = value or None
        with self._lock:
            current = self._values.get(normalized)
            if current == new_value:
                return False
            self._values[normalized] = new_value
            self._persist()
            return True

    def update_many(self, values: dict[str, Optional[str]]) -> bool:
        """Bulk update providers returning ``True`` when any value changes."""

        mutated = False
        for slug, value in values.items():
            mutated |= self.set(slug, value)
        return mutated

    def _persist(self) -> None:
        payload = {
            slug: self._values.get(slug)
            for slug in SUPPORTED_PROVIDER_SLUGS
        }
        self._store.set_many(payload)

    def snapshot(self) -> dict[str, Optional[str]]:
        with self._lock:
            return dict(self._values)

    def is_configured(self, slug: str) -> bool:
        return bool(self.get(slug))

    def key_getter(self, slug: str) -> Callable[[], Optional[str]]:
        normalized = normalize_provider(slug)

        def _getter() -> Optional[str]:
            return self.get(normalized)

        return _getter

    def supported_providers(self) -> list[str]:
        return list(SUPPORTED_PROVIDER_SLUGS)

    @property
    def omdb_enabled(self) -> bool:
        return self.is_configured("omdb")

    @property
    def discogs_enabled(self) -> bool:
        return self.is_configured("discogs")

    @property
    def lastfm_enabled(self) -> bool:
        return self.is_configured("lastfm")


runtime_settings = RuntimeProviderSettings()

__all__ = [
    "normalize_provider",
    "runtime_settings",
    "RuntimeProviderSettings",
    "SUPPORTED_PROVIDER_SLUGS",
    "PROVIDER_ENV_MAP",
]
