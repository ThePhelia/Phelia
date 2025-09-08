from __future__ import annotations
from typing import Dict, List, Optional
import httpx


class QbClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: float = 15.0):
        self.base_url = str(base_url).rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    def _c(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)
        return self._client
    async def login(self) -> None:
        r = await self._c().post(
            f"{self.base_url}/api/v2/auth/login",
            data={"username": self.username, "password": self.password},
        )
        r.raise_for_status()

    async def add_magnet(self, magnet: str, save_path: Optional[str] = None, category: Optional[str] = None) -> Dict:
        data = {"urls": magnet}
        if save_path:
            data["savepath"] = save_path
        if category:
            data["category"] = category
        r = await self._c().post(f"{self.base_url}/api/v2/torrents/add", data=data)
        r.raise_for_status()
        return {}

    async def list_torrents(self, filter: Optional[str] = None, category: Optional[str] = None) -> List[Dict]:
        params = {}
        if filter:
            params["filter"] = filter
        if category:
            params["category"] = category
        r = await self._c().get(f"{self.base_url}/api/v2/torrents/info", params=params)
        r.raise_for_status()
        return r.json()

<<<<<<< ours
    async def pause_torrent(self, torrent_hash: str) -> Dict:
        r = await self._c().post(
            f"{self.base_url}/api/v2/torrents/pause", data={"hashes": torrent_hash}
        )
        r.raise_for_status()
        return {}

    async def resume_torrent(self, torrent_hash: str) -> Dict:
        r = await self._c().post(
            f"{self.base_url}/api/v2/torrents/resume", data={"hashes": torrent_hash}
        )
        r.raise_for_status()
        return {}

    async def delete_torrent(self, torrent_hash: str, delete_files: bool = False) -> Dict:
        r = await self._c().post(
            f"{self.base_url}/api/v2/torrents/delete",
            data={"hashes": torrent_hash, "deleteFiles": "true" if delete_files else "false"},
        )
        r.raise_for_status()
        return {}
=======
    async def close(self) -> None:
        """Close the underlying HTTP client if it was created."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "QbClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
>>>>>>> theirs


QBitClient = QbClient

