from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError


class RegistryUnavailableError(Exception):
    """Raised when the plugin registry cannot be reached or returns an error."""

    def __init__(self, status_code: int | None, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


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
    registry_version: int | None = None
    repo: str | None = None
    generated_at: str | None = None
    plugins: list[PluginIndexItem]


REGISTRY_URL = (
    "https://phelia-plugins.github.io/plugins-index/index.json"
)


async def fetch_registry() -> RegistryIndex:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(REGISTRY_URL, timeout=30.0)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        detail = (
            f"Registry request failed with status {status_code}"
            if status_code is not None
            else "Registry request failed with an unknown status"
        )
        raise RegistryUnavailableError(status_code=status_code, detail=detail) from exc
    except httpx.RequestError as exc:
        raise RegistryUnavailableError(
            status_code=None,
            detail=f"Error while requesting registry: {exc}",
        ) from exc
    data = response.json()
    try:
        return RegistryIndex.model_validate(data)
    except ValidationError as exc:
        raise ValueError("Invalid registry response") from exc
