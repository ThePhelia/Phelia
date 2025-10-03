from __future__ import annotations

import hashlib
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError


class PhexArtifact(BaseModel):
    """Location of a `.phex` archive in a registry."""

    url: str
    sha256: str


class PluginIndexItem(BaseModel):
    id: str
    name: str
    version: str
    description: str | None = None
    artifact: PhexArtifact
    permissions: list[str] = Field(default_factory=list)
    min_phelia: str | None = None
    author: dict[str, Any] | None = None


class RegistryIndex(BaseModel):
    registry_version: int
    plugins: list[PluginIndexItem]


REGISTRY_URL = (
    "https://phelia-plugins.github.io/plugins-index/index.json"
)


async def fetch_registry() -> RegistryIndex:
    async with httpx.AsyncClient() as client:
        response = await client.get(REGISTRY_URL, timeout=30.0)
        response.raise_for_status()
        data = response.json()
    try:
        return RegistryIndex.model_validate(data)
    except ValidationError as exc:
        raise ValueError("Invalid registry response") from exc
