"""Schemas for provider settings management endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ProviderCredentialPayload(BaseModel):
    """Input payload when updating a provider API key."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    api_key: str | None = Field(
        default=None,
        description="API key/token to store for the provider.",
        validation_alias=AliasChoices("api_key", "apiKey"),
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


class PluginSettingsSummary(BaseModel):
    id: str
    name: str
    contributes_settings: bool = False
    settings_schema: dict[str, Any] | None = None


class PluginSettingsListResponse(BaseModel):
    plugins: list[PluginSettingsSummary] = Field(default_factory=list)


class PluginSettingsValuesResponse(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


class PluginSettingsUpdatePayload(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
