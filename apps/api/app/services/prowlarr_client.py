from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.runtime_service_settings import runtime_service_settings


class ProwlarrApiError(RuntimeError):
    def __init__(self, *, status_code: int, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.details = details


@dataclass(slots=True)
class ProwlarrClient:
    timeout: float = 15.0

    def _base_url(self) -> str:
        settings = runtime_service_settings.prowlarr_snapshot()
        return settings.url.rstrip("/")

    def _api_key(self) -> str:
        settings = runtime_service_settings.prowlarr_snapshot()
        if not settings.api_key:
            raise ProwlarrApiError(
                status_code=400,
                message="Prowlarr API key is not configured.",
                details={"error": "prowlarr_api_key_missing"},
            )
        return settings.api_key

    async def _request(self, method: str, path: str, *, json: Any | None = None) -> Any:
        url = f"{self._base_url()}{path}"
        headers = {"X-Api-Key": self._api_key()}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, headers=headers, json=json)
        except httpx.RequestError as exc:
            raise ProwlarrApiError(
                status_code=502,
                message="Unable to reach Prowlarr.",
                details={"error": "prowlarr_unreachable", "reason": str(exc)},
            ) from exc

        if response.status_code >= 400:
            payload: Any | None = None
            try:
                payload = response.json()
            except ValueError:
                payload = response.text or None

            message = "Prowlarr request failed."
            if isinstance(payload, dict):
                message = (
                    str(payload.get("message") or payload.get("errorMessage") or payload.get("error") or message)
                )
            elif isinstance(payload, str) and payload.strip():
                message = payload.strip()

            raise ProwlarrApiError(status_code=response.status_code, message=message, details=payload)

        if response.status_code == 204:
            return None

        if "application/json" in (response.headers.get("content-type") or ""):
            return response.json()
        return None

    async def list_indexers(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/api/v1/indexer")
        return payload if isinstance(payload, list) else []

    async def list_indexer_templates(self) -> list[dict[str, Any]]:
        for path in ("/api/v1/indexer/schema", "/api/v1/indexerSchema"):
            try:
                payload = await self._request("GET", path)
            except ProwlarrApiError as exc:
                if exc.status_code == 404:
                    continue
                raise
            return payload if isinstance(payload, list) else []
        return []

    async def create_indexer(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request("POST", "/api/v1/indexer", json=payload)
        return response if isinstance(response, dict) else {}

    async def update_indexer(self, indexer_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request("PUT", f"/api/v1/indexer/{indexer_id}", json=payload)
        return response if isinstance(response, dict) else {}

    async def delete_indexer(self, indexer_id: int) -> None:
        await self._request("DELETE", f"/api/v1/indexer/{indexer_id}")

    async def test_indexer(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request("POST", "/api/v1/indexer/test", json=payload)
        return response if isinstance(response, dict) else {}
