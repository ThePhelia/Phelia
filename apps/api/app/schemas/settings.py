"""Schemas for provider settings management endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProviderCredentialPayload(BaseModel):
    """Input payload when updating a provider API key."""

    model_config = ConfigDict(extra="forbid")

    api_key: str | None = Field(
        default=None,
        description="API key/token to store for the provider.",
    )


class ProviderCredentialStatus(BaseModel):
    """Status information returned for configured providers."""

    provider: str
    configured: bool
    masked_api_key: str | None = Field(
        default=None,
        description="Masked representation of the stored key.",
    )


class ProviderCredentialsResponse(BaseModel):
    """Envelope listing provider credential configuration."""

    providers: list[ProviderCredentialStatus] = Field(default_factory=list)
