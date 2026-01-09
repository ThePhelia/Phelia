"""Runtime settings for service integrations that can be updated via the UI."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from threading import RLock
from typing import Optional

from app.core.config import settings
from app.core.secure_store import SecretsStore, get_secrets_store
from app.services.search.jackett.settings import JackettSettings


def _normalize_url(value: str) -> str:
    return value.rstrip("/")


def _parse_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value]
    else:
        items = str(value).replace(",", "\n").splitlines()
    return [item.strip() for item in items if str(item).strip()]


def _normalize_dirs(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        value = value.strip()
        if not value or value in seen:
            continue
        normalized.append(value)
        seen.add(value)
    return normalized


@dataclass(frozen=True)
class JackettRuntimeSnapshot:
    url: str
    api_key: Optional[str]
    allowlist: list[str]
    blocklist: list[str]
    category_filters: list[str]
    minimum_seeders: int


@dataclass(frozen=True)
class QbittorrentRuntimeSnapshot:
    url: str
    username: str
    password: str


@dataclass(frozen=True)
class DownloadRuntimeSnapshot:
    allowed_dirs: list[str]
    default_dir: str


class RuntimeServiceSettings:
    """Manage service configuration that can be updated at runtime."""

    def __init__(self, store: SecretsStore | None = None) -> None:
        self._lock = RLock()
        self._jackett: JackettRuntimeSnapshot
        self._qbittorrent: QbittorrentRuntimeSnapshot
        self._downloads: DownloadRuntimeSnapshot
        self._store = store or get_secrets_store()
        self.reset_to_env()

    def reset_to_env(self) -> None:
        with self._lock:
            jackett_url = _normalize_url(str(settings.JACKETT_URL))
            qb_url = _normalize_url(str(settings.QB_URL))
            allowlist = _parse_list(getattr(settings, "JACKETT_ALLOWLIST", None))
            blocklist = _parse_list(getattr(settings, "JACKETT_BLOCKLIST", None))
            category_filters = _parse_list(
                getattr(settings, "JACKETT_CATEGORY_FILTERS", None)
            )
            minimum_seeders = max(0, int(getattr(settings, "JACKETT_MINIMUM_SEEDERS", 0)))
            jackett_key = self._store.get("jackett_api_key")
            qb_password = self._store.get("qbittorrent_password")
            if not isinstance(jackett_key, str) or not jackett_key.strip():
                jackett_key = getattr(settings, "JACKETT_API_KEY", None) or None
                if jackett_key:
                    self._store.set("jackett_api_key", jackett_key)
            if not isinstance(qb_password, str) or not qb_password.strip():
                qb_password = getattr(settings, "QB_PASS", "") or ""
                if qb_password:
                    self._store.set("qbittorrent_password", qb_password)
            self._jackett = JackettRuntimeSnapshot(
                url=jackett_url,
                api_key=jackett_key,
                allowlist=allowlist,
                blocklist=blocklist,
                category_filters=category_filters,
                minimum_seeders=minimum_seeders,
            )
            self._qbittorrent = QbittorrentRuntimeSnapshot(
                url=qb_url,
                username=getattr(settings, "QB_USER", "") or "",
                password=qb_password,
            )
            allowed_dirs = _normalize_dirs(_parse_list(settings.ALLOWED_SAVE_DIRS))
            default_dir = str(settings.DEFAULT_SAVE_DIR).strip() or "/downloads"
            if default_dir not in allowed_dirs:
                allowed_dirs = [default_dir, *allowed_dirs]
            self._downloads = DownloadRuntimeSnapshot(
                allowed_dirs=allowed_dirs,
                default_dir=default_dir,
            )

    def jackett_settings(self) -> JackettSettings:
        with self._lock:
            snapshot = self._jackett
            qb = self._qbittorrent
        return JackettSettings(
            jackett_url=snapshot.url,
            jackett_api_key=snapshot.api_key,
            qbittorrent_url=qb.url,
            qbittorrent_username=qb.username,
            qbittorrent_password=qb.password,
            allowlist=list(snapshot.allowlist),
            blocklist=list(snapshot.blocklist),
            category_filters=list(snapshot.category_filters),
            minimum_seeders=snapshot.minimum_seeders,
        )

    def jackett_snapshot(self) -> JackettRuntimeSnapshot:
        with self._lock:
            return self._jackett

    def qbittorrent_snapshot(self) -> QbittorrentRuntimeSnapshot:
        with self._lock:
            return self._qbittorrent

    def download_snapshot(self) -> DownloadRuntimeSnapshot:
        with self._lock:
            return self._downloads

    def update_jackett(self, *, url: Optional[str] = None, api_key: Optional[str] = None) -> bool:
        with self._lock:
            snapshot = self._jackett
            new_url = snapshot.url if url is None else _normalize_url(url)
            new_api_key = snapshot.api_key if api_key is None else (api_key or None)
            updated = JackettRuntimeSnapshot(
                url=new_url,
                api_key=new_api_key,
                allowlist=list(snapshot.allowlist),
                blocklist=list(snapshot.blocklist),
                category_filters=list(snapshot.category_filters),
                minimum_seeders=snapshot.minimum_seeders,
            )
            if updated == snapshot:
                return False
            self._jackett = updated
            self._persist()
            return True

    def update_qbittorrent(
        self,
        *,
        url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> bool:
        with self._lock:
            snapshot = self._qbittorrent
            updated = QbittorrentRuntimeSnapshot(
                url=snapshot.url if url is None else _normalize_url(url),
                username=snapshot.username if username is None else (username or ""),
                password=snapshot.password if password is None else (password or ""),
            )
            if updated == snapshot:
                return False
            self._qbittorrent = updated
            self._persist()
            return True

    def update_downloads(
        self,
        *,
        allowed_dirs: Optional[list[str]] = None,
        default_dir: Optional[str] = None,
    ) -> bool:
        with self._lock:
            snapshot = self._downloads
            current_allowed = snapshot.allowed_dirs
            current_default = snapshot.default_dir
            if allowed_dirs is not None:
                current_allowed = _normalize_dirs(allowed_dirs)
            if default_dir is not None:
                default_dir = default_dir.strip()
                if default_dir:
                    current_default = default_dir
            if current_default not in current_allowed:
                current_allowed = [current_default, *current_allowed]
            updated = DownloadRuntimeSnapshot(
                allowed_dirs=current_allowed,
                default_dir=current_default,
            )
            if updated == snapshot:
                return False
            self._downloads = updated
            return True

    def _persist(self) -> None:
        payload = {
            "jackett_api_key": self._jackett.api_key,
            "qbittorrent_password": self._qbittorrent.password,
        }
        self._store.set_many(payload)

    def is_allowed_save_dir(self, save_dir: str) -> bool:
        with self._lock:
            return save_dir in self._downloads.allowed_dirs


runtime_service_settings = RuntimeServiceSettings()

__all__ = [
    "runtime_service_settings",
    "RuntimeServiceSettings",
    "JackettRuntimeSnapshot",
    "QbittorrentRuntimeSnapshot",
    "DownloadRuntimeSnapshot",
]
