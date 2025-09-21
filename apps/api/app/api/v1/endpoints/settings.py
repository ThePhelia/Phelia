"""Settings management endpoints for provider credentials."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.settings import (
    ProviderCredentialPayload,
    ProviderCredentialStatus,
    ProviderCredentialsResponse,
)
from app.services import settings as settings_service
from app.services.settings import UnsupportedProviderError

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/providers", response_model=ProviderCredentialsResponse)
def list_providers(db: Session = Depends(get_db)) -> ProviderCredentialsResponse:
    stored = settings_service.list_provider_credentials(db)
    statuses: list[ProviderCredentialStatus] = []
    for provider in settings_service.supported_providers():
        record = stored.get(provider)
        api_key = record.api_key if record else None
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
        record = settings_service.upsert_provider_credential(db, provider, api_key)
    except UnsupportedProviderError:
        raise HTTPException(status_code=404, detail={"error": "unknown_provider"})

    return ProviderCredentialStatus(
        provider=record.provider,
        configured=bool(record.api_key),
        masked_api_key=settings_service.mask_api_key(record.api_key),
    )
