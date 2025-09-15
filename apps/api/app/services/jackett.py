import httpx
from typing import List, Dict, Any

class JackettClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._c = httpx.AsyncClient(timeout=15)

    async def list_indexers(self) -> List[Dict[str, Any]]:
        r = await self._c.get(f"{self.base_url}/api/v2.0/indexers/all/results", params={"apikey": self.api_key})
        r.raise_for_status()
        data = r.json()
        out = []
        for it in data:
            out.append({
                "id": it["id"],
                "name": it.get("name", it["id"]),
                "is_private": it.get("privacy") == "private",
                "configured": bool(it.get("configured")),
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
        return r.json()

