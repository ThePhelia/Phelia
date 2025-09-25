from __future__ import annotations
from typing import Dict, List, Optional
import httpx
import logging

from app.core.config import settings


class QbClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: float = 15.0):
        self.base_url = str(base_url).rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._headers = {"Referer": f"{self.base_url}/"}

    def _c(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client
    def _is_success(self, response: httpx.Response) -> bool:
        """Return ``True`` if the response body indicates success."""

        body = response.text.strip().lower()
        return body in {"", "ok", "ok."}

    async def login(self) -> None:
        r = await self._c().post(
            f"{self.base_url}/api/v2/auth/login", data={"username": self.username, "password": self.password},
            headers=self._headers,
        )
        r.raise_for_status()
        if not self._is_success(r):
            raise httpx.HTTPStatusError("Login failed", request=r.request, response=r)

    async def add_magnet(self, magnet: str, save_path: Optional[str] = None, category: Optional[str] = None) -> Dict:
        data = {"urls": magnet}
        if save_path:
            data["savepath"] = save_path
        if category:
            data["category"] = category
        r = await self._c().post(
            f"{self.base_url}/api/v2/torrents/add", data=data,
            headers=self._headers,
        )
        r.raise_for_status()
        if not self._is_success(r):
            raise httpx.HTTPStatusError("Login failed", request=r.request, response=r)
        return {}

    async def add_torrent_file(
        self,
        torrent: bytes,
        save_path: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict:
        data = {}
        if save_path:
            data["savepath"] = save_path
        if category:
            data["category"] = category
        files = {"torrents": ("torrent.torrent", torrent, "application/x-bittorrent")}
        r = await self._c().post(
            f"{self.base_url}/api/v2/torrents/add",
            data=data,
            files=files,
            headers=self._headers,
        )
        r.raise_for_status()
        return {}

    async def list_torrents(self, filter: Optional[str] = None, category: Optional[str] = None) -> List[Dict]:
        params = {}
        if filter:
            params["filter"] = filter
        if category:
            params["category"] = category
        r = await self._c().get(
            f"{self.base_url}/api/v2/torrents/info", params=params, headers=self._headers
        )
        r.raise_for_status()
        return r.json()

    async def pause_torrent(self, torrent_hash: str) -> Dict:
        r = await self._c().post(
            f"{self.base_url}/api/v2/torrents/pause", data={"hashes": torrent_hash},
            headers=self._headers,
        )
        r.raise_for_status()
        if not self._is_success(r):
            raise httpx.HTTPStatusError("Login failed", request=r.request, response=r)
        return {}

    async def resume_torrent(self, torrent_hash: str) -> Dict:
        r = await self._c().post(
            f"{self.base_url}/api/v2/torrents/resume", data={"hashes": torrent_hash},
            headers=self._headers,
        )
        r.raise_for_status()
        if not self._is_success(r):
            raise httpx.HTTPStatusError("Login failed", request=r.request, response=r)
        return {}

    async def delete_torrent(self, torrent_hash: str, delete_files: bool = False) -> Dict:
        r = await self._c().post(
            f"{self.base_url}/api/v2/torrents/delete", data={"hashes": torrent_hash, "deleteFiles": "true" if delete_files else "false"},
            headers=self._headers,
        )
        r.raise_for_status()
        if not self._is_success(r):
            raise httpx.HTTPStatusError("Login failed", request=r.request, response=r)
        return {}

    async def close(self) -> None:
        """Close the underlying HTTP client if it was created."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "QbClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()


QBitClient = QbClient

logger = logging.getLogger(__name__)


async def health_check() -> None:
    client = QbClient(
        settings.QB_URL, settings.QB_USER, settings.QB_PASS, timeout=5.0
    )
    try:
        async with client:
            await client.login()
            await client.list_torrents()
        logger.info("qBittorrent reachable at %s", settings.QB_URL)
    except Exception as e:
        logger.error("qBittorrent health check failed: %s", e)

