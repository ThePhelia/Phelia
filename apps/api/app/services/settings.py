"""Persistence helpers for provider credential configuration."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ProviderCredential
from app.services.metadata import get_metadata_router

SUPPORTED_PROVIDER_SETTINGS: dict[str, str] = {
    "tmdb": "TMDB_API_KEY",
    "omdb": "OMDB_API_KEY",
    "discogs": "DISCOGS_TOKEN",
    "lastfm": "LASTFM_API_KEY",
}


class UnsupportedProviderError(ValueError):
    """Raised when attempting to use a provider that isn't supported."""


def supported_providers() -> list[str]:
    """Return the list of providers supported by the persistence layer."""

    return list(SUPPORTED_PROVIDER_SETTINGS.keys())


def _normalize_provider(provider: str) -> str:
    return provider.strip().lower()


def _apply_to_settings(provider: str, api_key: str | None) -> bool:
    attr = SUPPORTED_PROVIDER_SETTINGS.get(provider)
    if not attr:
        return False
    current = getattr(settings, attr, None)
    if current == api_key:
        return False
    setattr(settings, attr, api_key)
    return True


def _clear_metadata_cache() -> None:
    cache_clear = getattr(get_metadata_router, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()


def load_provider_credentials(db: Session) -> dict[str, str | None]:
    """Load persisted credentials into the running settings instance."""

    try:
        rows = db.execute(select(ProviderCredential)).scalars().all()
    except (OperationalError, ProgrammingError):
        db.rollback()
        return {}

    applied: dict[str, str | None] = {}
    mutated = False
    for row in rows:
        provider = _normalize_provider(row.provider)
        if provider not in SUPPORTED_PROVIDER_SETTINGS:
            continue
        applied[provider] = row.api_key
        mutated |= _apply_to_settings(provider, row.api_key)

    if mutated:
        _clear_metadata_cache()

    return applied


def list_provider_credentials(db: Session) -> dict[str, ProviderCredential]:
    """Return provider credential rows keyed by provider name."""

    try:
        rows = db.execute(select(ProviderCredential)).scalars().all()
    except (OperationalError, ProgrammingError):
        db.rollback()
        return {}
    return {_normalize_provider(row.provider): row for row in rows}


def upsert_provider_credential(
    db: Session, provider: str, api_key: str | None
) -> ProviderCredential:
    """Insert or update the credential for ``provider`` and sync settings."""

    normalized = _normalize_provider(provider)
    if normalized not in SUPPORTED_PROVIDER_SETTINGS:
        raise UnsupportedProviderError(provider)

    stmt = select(ProviderCredential).where(ProviderCredential.provider == normalized)
    existing = db.execute(stmt).scalar_one_or_none()

    if existing is None:
        existing = ProviderCredential(provider=normalized, api_key=api_key)
        db.add(existing)
    else:
        existing.api_key = api_key

    db.flush()

    _apply_to_settings(normalized, api_key)
    _clear_metadata_cache()

    return existing


def mask_api_key(api_key: str | None) -> str | None:
    """Return a masked representation suitable for API responses."""

    if not api_key:
        return None
    if len(api_key) <= 4:
        return "*" * len(api_key)
    return f"{'*' * (len(api_key) - 4)}{api_key[-4:]}"
