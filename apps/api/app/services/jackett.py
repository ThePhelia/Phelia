import httpx
from typing import List, Dict, Any

class JackettClient:

    def _ensure_json(self, r: httpx.Response):
        ct = r.headers.get("content-type", "")
        if "application/json" not in ct.lower():
            raise httpx.HTTPStatusError(
                f"Expected JSON from Jackett, got {ct}. Likely invalid or missing API key (302 to UI/Login).",
                request=r.request,
                response=r
            )
        return self._ensure_json(r)

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._c = httpx.AsyncClient(timeout=15, headers={"Accept": "application/json"})

    async def list_indexers(self) -> List[Dict[str, Any]]:
        # Jackett returns 302 to /UI/Login if apikey is missing/invalid or wrong endpoint is used.
        # Use the documented /api/v2.0/indexers/all with ?apikey=... and optional configured=true
        url = f"{self.base_url}/api/v2.0/indexers/all"
        r = await self._c.get(url, params={"apikey": self.api_key, "configured": "true"})
        r.raise_for_status()
        data = self._ensure_json(r)
        out = []
        for it in data:
            out.append({
                "id": it.get("id") or it.get("name"),
                "name": it.get("name"),
                "configured": bool(it.get("configured", False)),
                "public": bool(it.get("type") == "public" or it.get("privacy") == "public"),
                "caps": it.get("caps", {}),
            })
        return out

    async def set_indexer_credentials(self, idx_id: str, payload: Dict[str, Any]) -> None:
        r = await self._c.post(
            f"{self.base_url}/api/v2.0/indexers/{idx_id}/config",
            params={"apikey": self.api_key},
            json=payload
        )
        r.raise_for_status()

    async def test_indexer(self, idx_id: str) -> Dict[str, Any]:
        r = await self._c.post(
            f"{self.base_url}/api/v2.0/indexers/{idx_id}/test",
            params={"apikey": self.api_key}
        )
        r.raise_for_status()
        return self._ensure_json(r)

