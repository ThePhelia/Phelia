from __future__ import annotations

import hashlib
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError


class Artifact(BaseModel):
    url: str
    sha256: str


class PluginIndexItem(BaseModel):
    id: str
    name: str
    version: str
    description: str | None = None
    entry_point: str
    artifact: Artifact
    permissions: list[str] = Field(default_factory=list)
    settings_schema: dict[str, Any] | None = None
    routes: bool | None = None
    contributes_settings: bool | None = None


class RegistryIndex(BaseModel):
    registry_version: int
    plugins: list[PluginIndexItem]


REGISTRY_URL = (
    "https://raw.githubusercontent.com/yourorg/phelia-plugin-registry/main/index.json"
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


def verify_sha256(file_bytes: bytes, expected: str) -> None:
    digest = hashlib.sha256(file_bytes).hexdigest()
    if digest.lower() != expected.lower():
        raise ValueError("SHA256 mismatch for downloaded artifact")

