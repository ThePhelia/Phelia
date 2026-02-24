from __future__ import annotations
import logging
import os
from pathlib import Path
import re
import subprocess
from typing import Dict, List, Optional

import httpx

from app.core.runtime_service_settings import runtime_service_settings

logger = logging.getLogger(__name__)


_QBITTORRENT_LOG_PATHS: tuple[Path, ...] = (
    Path("/mnt/qbittorrent_config/qBittorrent/logs/qbittorrent.log"),
    Path("/config/qBittorrent/logs/qbittorrent.log"),
)
_QBITTORRENT_TEMP_PASSWORD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"temporary password is provided for this session:\s*(\S+)", re.IGNORECASE),
    re.compile(r"temporary password:\s*(\S+)", re.IGNORECASE),
)


def _extract_temporary_password(log_text: str) -> str | None:
    matches: list[str] = []
    for pattern in _QBITTORRENT_TEMP_PASSWORD_PATTERNS:
        matches.extend(match.group(1) for match in pattern.finditer(log_text))
    if not matches:
        return None
    return matches[-1]


def _read_temporary_password_from_logs() -> str | None:
    for path in _QBITTORRENT_LOG_PATHS:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except FileNotFoundError:
            continue
        except Exception:
            continue

        temporary_password = _extract_temporary_password(content)
        if temporary_password:
            return temporary_password
    return None


def _read_temporary_password_from_container_logs() -> str | None:
    names_csv = os.getenv("QBIT_CONTAINER_NAMES", "qbittorrent,qbittorrent-1")
    container_names = [name.strip() for name in names_csv.split(",") if name.strip()]
    if not container_names:
        return None

    for container_name in container_names:
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", "200", container_name],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return None
        except Exception:
            continue
        if result.returncode != 0:
            continue

        combined_logs = "\n".join(
            text for text in (result.stdout, result.stderr) if text
        )
        temporary_password = _extract_temporary_password(combined_logs)
        if temporary_password:
            return temporary_password
    return None


def _read_temporary_password() -> str | None:
    return _read_temporary_password_from_logs() or _read_temporary_password_from_container_logs()


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
        headers = {**self._headers, "Content-Type": "application/x-www-form-urlencoded"}
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                r = await self._do_login_request(self.password, headers=headers)
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
        if r.status_code == 403:
            if await self._try_temporary_password_fallback(headers=headers):
                return
            raise QbittorrentLoginError(
                "AUTH_FAILED",
                "qBittorrent auth rejected",
                status_code=r.status_code,
            )
        if r.status_code != 200:
            raise QbittorrentLoginError(
                "HTTP_STATUS",
                f"qBittorrent auth returned status {r.status_code}",
                status_code=r.status_code,
            )
        if r.text.strip().lower().startswith("fails"):
            if await self._try_temporary_password_fallback(headers=headers):
                return
            raise QbittorrentLoginError("AUTH_FAILED", "qBittorrent auth rejected")
        if not (self._has_auth_cookie(r) or self._client_has_auth_cookie()):
            raise QbittorrentLoginError("NO_SID_COOKIE", "qBittorrent auth missing SID")
        if not self._is_success(r):
            raise QbittorrentLoginError("AUTH_FAILED", "qBittorrent auth rejected")

    async def _do_login_request(
        self, password: str, *, headers: dict[str, str]
    ) -> httpx.Response:
        payload = {"username": self.username, "password": password}
        return await self._c().post(
            f"{self.base_url}/api/v2/auth/login",
            data=payload,
            headers=headers,
        )

    async def _try_temporary_password_fallback(self, *, headers: dict[str, str]) -> bool:
        temporary_password = _read_temporary_password()
        if not temporary_password or temporary_password == self.password:
            return False

        logger.warning("qBittorrent auth rejected; retrying with temporary password from logs")
        response = await self._do_login_request(temporary_password, headers=headers)
        if response.status_code != 200:
            return False
        if response.text.strip().lower().startswith("fails"):
            return False
        if not (self._has_auth_cookie(response) or self._client_has_auth_cookie()):
            return False
        if not self._is_success(response):
            return False

        self.password = temporary_password
        runtime_service_settings.update_qbittorrent(password=temporary_password)
        logger.info("qBittorrent temporary password accepted; runtime credentials refreshed")
        return True

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
