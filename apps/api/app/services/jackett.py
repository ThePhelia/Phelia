import httpx
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

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
        self._c = httpx.AsyncClient(timeout=15, headers={"Accept": "application/json"}, follow_redirects=False)

    
    
    async def list_indexers(self) -> List[Dict[str, Any]]:
        headers = {"X-Api-Key": self.api_key, "Accept": "application/json"}
        params = {"configured": "true", "apikey": self.api_key}
        urls = [
            f"{self.base_url}/api/v2.0/indexers",
            f"{self.base_url}/api/v2.0/indexers/all",
        ]
        last_exc = None
        for url in urls:
            r = await self._c.get(url, headers=headers, params=params)
            if r.status_code == 302:
                loc = r.headers.get("Location")
                ct = r.headers.get("Content-Type", "")
                logger.warning("Jackett 302 on %s -> %s (CT=%s)", url, loc, ct)
                # Explicitly raise helpful message
                raise httpx.HTTPStatusError(
                    f"Jackett returned 302 (redirect to {loc}). Check API key and Authentication settings in Jackett UI.",
                    request=r.request,
                    response=r
                )
            if r.status_code >= 400:
                logger.warning("Jackett %s %s -> %s CT=%s", r.request.method, r.request.url, r.status_code, r.headers.get("Content-Type", ""))
                last_exc = httpx.HTTPStatusError(
                    f"Jackett error {r.status_code} on {url}.",
                    request=r.request,
                    response=r
                )
                continue
            try:
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
            except Exception as e:
                last_exc = e
                logger.exception("Failed to parse Jackett response from %s", url)
                continue
        if last_exc:
            raise last_exc
        return []

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

