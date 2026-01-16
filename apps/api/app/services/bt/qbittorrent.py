from __future__ import annotations
import logging
from typing import Dict, List, Optional

import httpx

from app.core.runtime_service_settings import runtime_service_settings

logger = logging.getLogger(__name__)


class QbittorrentLoginError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int | None = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.status_code = status_code


class QbClient:
    def __init__(
        self, base_url: str, username: str, password: str, timeout: float = 15.0
    ):
        self.base_url = str(base_url).strip().rstrip("/")
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

    def _has_auth_cookie(self, response: httpx.Response) -> bool:
        return bool(response.cookies.get("SID") or response.cookies.get("sid"))

    def _client_has_auth_cookie(self) -> bool:
        client = self._client
        if client is None:
            return False
        return bool(client.cookies.get("SID") or client.cookies.get("sid"))

    async def login(self) -> None:
        if not self.base_url or not self.base_url.startswith(("http://", "https://")):
            raise QbittorrentLoginError(
                "BAD_BASE_URL", "qBittorrent base URL must include http(s) scheme"
            )
        logger.debug(
            "qBittorrent login url=%s user=%s password_set=%s",
            self.base_url,
            self.username,
            bool(self.password),
        )
        payload = {"username": self.username, "password": self.password}
        headers = {**self._headers, "Content-Type": "application/x-www-form-urlencoded"}
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                r = await self._c().post(
                    f"{self.base_url}/api/v2/auth/login",
                    data=payload,
                    headers=headers,
                )
                break
            except httpx.RequestError as exc:
                last_error = exc
                if attempt == 0:
                    logger.warning("qBittorrent login request error: %s", exc)
                    continue
                raise QbittorrentLoginError(
                    "UNREACHABLE", "qBittorrent login request failed"
                ) from exc
        else:  # pragma: no cover - defensive guard
            raise QbittorrentLoginError(
                "UNREACHABLE", "qBittorrent login request failed"
            ) from last_error

        body_snippet = r.text.strip()[:20]
        logger.debug(
            "qBittorrent auth response status=%s body=%r",
            r.status_code,
            body_snippet,
        )
        if r.status_code != 200:
            raise QbittorrentLoginError(
                "HTTP_STATUS",
                f"qBittorrent auth returned status {r.status_code}",
                status_code=r.status_code,
            )
        if r.text.strip().lower().startswith("fails"):
            raise QbittorrentLoginError("AUTH_FAILED", "qBittorrent auth rejected")
        if not (self._has_auth_cookie(r) or self._client_has_auth_cookie()):
            raise QbittorrentLoginError("NO_SID_COOKIE", "qBittorrent auth missing SID")
        if not self._is_success(r):
            raise QbittorrentLoginError("AUTH_FAILED", "qBittorrent auth rejected")

    async def add_magnet(
        self,
        magnet: str,
        save_path: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict:
        data = {"urls": magnet}
        if save_path:
            data["savepath"] = save_path
        if category:
            data["category"] = category
        r = await self._c().post(
            f"{self.base_url}/api/v2/torrents/add",
            data=data,
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

    async def list_torrents(
        self, filter: Optional[str] = None, category: Optional[str] = None
    ) -> List[Dict]:
        params = {}
        if filter:
            params["filter"] = filter
        if category:
            params["category"] = category
        r = await self._c().get(
            f"{self.base_url}/api/v2/torrents/info",
            params=params,
            headers=self._headers,
        )
        r.raise_for_status()
        return r.json()

    async def pause_torrent(self, torrent_hash: str) -> Dict:
        r = await self._c().post(
            f"{self.base_url}/api/v2/torrents/pause",
            data={"hashes": torrent_hash},
            headers=self._headers,
        )
        r.raise_for_status()
        if not self._is_success(r):
            raise httpx.HTTPStatusError("Login failed", request=r.request, response=r)
        return {}

    async def resume_torrent(self, torrent_hash: str) -> Dict:
        r = await self._c().post(
            f"{self.base_url}/api/v2/torrents/resume",
            data={"hashes": torrent_hash},
            headers=self._headers,
        )
        r.raise_for_status()
        if not self._is_success(r):
            raise httpx.HTTPStatusError("Login failed", request=r.request, response=r)
        return {}

    async def delete_torrent(
        self, torrent_hash: str, delete_files: bool = False
    ) -> Dict:
        r = await self._c().post(
            f"{self.base_url}/api/v2/torrents/delete",
            data={
                "hashes": torrent_hash,
                "deleteFiles": "true" if delete_files else "false",
            },
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

    async def __aexit__(self, _exc_type, _exc, _tb) -> None:
        await self.close()


QBitClient = QbClient


async def health_check() -> None:
    qb = runtime_service_settings.qbittorrent_snapshot()
    client = QbClient(qb.url, qb.username, qb.password, timeout=5.0)
    try:
        async with client:
            await client.login()
            await client.list_torrents()
        logger.info("qBittorrent reachable at %s", qb.url)
    except Exception as e:
        logger.error("qBittorrent health check failed: %s", e)
