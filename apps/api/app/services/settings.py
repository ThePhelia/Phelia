"""Persistence helpers for provider credential configuration."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.runtime_settings import (
    PROVIDER_ENV_MAP,
    normalize_provider,
    runtime_settings,
)
from app.db.models import ProviderCredential
from app.services.metadata import get_metadata_router

logger = logging.getLogger(__name__)


class UnsupportedProviderError(ValueError):
    """Raised when attempting to use a provider that isn't supported."""


def supported_providers() -> list[str]:
    """Return the list of providers supported by the persistence layer."""

    return list(PROVIDER_ENV_MAP.keys())


def _clear_metadata_cache() -> None:
    cache_clear = getattr(get_metadata_router, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()


def _ensure_provider_table(db: Session) -> bool:
    """Ensure the provider credential table exists, returning ``True`` on success."""

    bind = db.get_bind()
    if bind is None:
        return False
    try:
        ProviderCredential.__table__.create(bind=bind, checkfirst=True)
    except SQLAlchemyError:  # pragma: no cover - defensive, logged for observability
        logger.exception("failed to ensure provider credential table exists")
        return False
    return True


def load_provider_credentials(db: Session) -> dict[str, str]:
    """Load persisted credentials into the runtime settings instance."""

    try:
        rows = db.execute(select(ProviderCredential)).scalars().all()
    except (OperationalError, ProgrammingError):
        db.rollback()
        _ensure_provider_table(db)
        return {}

    applied: dict[str, str] = {}
    for row in rows:
        provider = normalize_provider(row.provider_slug)
        if provider not in PROVIDER_ENV_MAP:
            continue
        applied[provider] = row.api_key

    mutated = runtime_settings.update_many(applied)
    if mutated:
        _clear_metadata_cache()

    return applied


def list_provider_credentials(db: Session) -> dict[str, str]:
    """Return persisted API keys keyed by provider slug."""

    try:
        rows = db.execute(select(ProviderCredential)).scalars().all()
    except (OperationalError, ProgrammingError):
        db.rollback()
        _ensure_provider_table(db)
        return {}
    return {normalize_provider(row.provider_slug): row.api_key for row in rows}


def upsert_provider_credential(
    db: Session, provider: str, api_key: Optional[str]
) -> Optional[str]:
    """Insert, update or clear the credential for ``provider`` and sync runtime state."""

    normalized = normalize_provider(provider)
    if normalized not in PROVIDER_ENV_MAP:
        raise UnsupportedProviderError(provider)

    stmt = select(ProviderCredential).where(
        ProviderCredential.provider_slug == normalized
    )
    try:
        existing = db.execute(stmt).scalar_one_or_none()
    except (OperationalError, ProgrammingError):
        db.rollback()
        if not _ensure_provider_table(db):
            raise
        existing = db.execute(stmt).scalar_one_or_none()

    if not api_key:
        if existing is not None:
            db.delete(existing)
            db.flush()
        changed = runtime_settings.set(normalized, None)
        if changed:
            _clear_metadata_cache()
        logger.info("provider %s API key cleared", normalized)
        return runtime_settings.get(normalized)

    if existing is None:
        db.add(ProviderCredential(provider_slug=normalized, api_key=api_key))
    else:
        existing.api_key = api_key

    db.flush()

    changed = runtime_settings.set(normalized, api_key)
    if changed:
        _clear_metadata_cache()
    logger.info("provider %s API key updated", normalized)

    return runtime_settings.get(normalized)


def mask_api_key(api_key: str | None) -> str | None:
    """Return a masked representation suitable for API responses."""

    if not api_key:
        return None
    if len(api_key) <= 4:
        return "*" * len(api_key)
    return f"{'*' * (len(api_key) - 4)}{api_key[-4:]}"
