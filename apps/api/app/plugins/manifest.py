from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PluginManifest(BaseModel):
    id: str
    name: str
    version: str
    description: str | None = None
    entry_point: str
    permissions: list[str] = Field(default_factory=list)
    settings_schema: dict[str, Any] | None = None
    routes: bool | None = None
    contributes_settings: bool | None = None

