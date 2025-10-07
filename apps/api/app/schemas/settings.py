"""Schemas for provider settings management endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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
