# apps/api/app/services/jackett.py
import httpx
from typing import List, Dict, Any, Optional

class JackettClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._c = httpx.AsyncClient(
            timeout=15,
            headers={"Accept": "application/json"},
            follow_redirects=False,
        )

    def _ensure_json(self, r: httpx.Response):
        ct = (r.headers.get("content-type") or "").lower()
        if "application/json" not in ct:
            raise httpx.HTTPStatusError(
                f"Expected JSON from Jackett, got {ct}",
                request=r.request,
                response=r,
            )
        return r.json()

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        headers = {"X-Api-Key": self.api_key}
        q = {"apikey": self.api_key}
        if params:
            q.update(params)
        r = await self._c.get(f"{self.base_url}{path}", headers=headers, params=q)
        r.raise_for_status()
        return r

    async def list_indexers(self) -> List[Dict[str, Any]]:
        for path in [
            "/api/v2.0/indexers/all/results",
            "/api/v2.0/indexers/all",
            "/api/v2.0/indexers",
        ]:
            r = await self._get(path, {"configured": "true"})
            if r.status_code == 200:
                data = self._ensure_json(r)
                out: List[Dict[str, Any]] = []
                for it in data:
                    out.append({
                        "id": it.get("id") or it.get("name"),
                        "name": it.get("name"),
                        "configured": bool(it.get("configured", False)),
                        "public": bool(it.get("type") == "public" or it.get("privacy") == "public"),
                        "caps": it.get("caps", {}),
                    })
                return out
        r.raise_for_status()
        return []

    async def set_indexer_credentials(self, idx_id: str, payload: Dict[str, Any]) -> None:
        headers = {"X-Api-Key": self.api_key}
        r = await self._c.post(
            f"{self.base_url}/api/v2.0/indexers/{idx_id}/config",
            headers=headers,
            params={"apikey": self.api_key},
            json=payload,
        )
        r.raise_for_status()

    async def test_indexer(self, idx_id: str) -> Dict[str, Any]:
        headers = {"X-Api-Key": self.api_key}
        r = await self._c.post(
            f"{self.base_url}/api/v2.0/indexers/{idx_id}/test",
            headers=headers,
            params={"apikey": self.api_key},
        )
        r.raise_for_status()
        return self._ensure_json(r)

