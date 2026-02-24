"""Runtime settings for service integrations that can be updated via the UI."""

from __future__ import annotations

from collections.abc import Iterable
import secrets
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Optional
import xml.etree.ElementTree as ET

from app.core.config import settings
from app.core.secure_store import SecretsStore, get_secrets_store
from app.services.search.prowlarr.settings import ProwlarrSettings


def _normalize_url(value: str) -> str:
    return value.rstrip("/")


_PROWLARR_CONFIG_XML_PATHS: tuple[Path, ...] = (
    Path("/mnt/prowlarr_config/config.xml"),
    Path("/config/config.xml"),
)


def _read_prowlarr_api_key_from_volume() -> str | None:
    """Best-effort read of Prowlarr ApiKey from a shared config.xml volume.

    Intended for docker-compose setups where the API/worker container can mount
    Prowlarr's /config volume read-only. Never logs the key.
    """
    for path in _PROWLARR_CONFIG_XML_PATHS:
        try:
            root = ET.parse(path).getroot()
            key = root.findtext("ApiKey")
            if isinstance(key, str) and key.strip():
                return key.strip()
        except FileNotFoundError:
            continue
        except Exception:
            # Corrupt/partial file, permission issues, etc. Treat as not found.
            continue
    return None


def _parse_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value]
    else:
        items = str(value).replace(",", "\n").splitlines()
    return [item.strip() for item in items if str(item).strip()]


def _ensure_qb_password(store: SecretsStore) -> str:
    existing = store.get("qbittorrent_password")
    if isinstance(existing, str) and existing:
        return existing
    generated = secrets.token_urlsafe(24)
    store.set_many({"qbittorrent_password": generated}, allow_empty_keys={"qbittorrent_password"})
    return generated


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
class ProwlarrRuntimeSnapshot:
    url: str
    api_key: str | None
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
    """A small in-process runtime snapshot of external service settings.

    Values can come from:
    - ENV / settings module defaults
    - secure store (persisted secrets)
    - UI updates (persisted via secure store)
    """

    def __init__(self, store: SecretsStore) -> None:
        self._store = store
        self._lock = RLock()

        self._prowlarr = ProwlarrRuntimeSnapshot(
            url="",
            api_key=None,
            allowlist=[],
            blocklist=[],
            category_filters=[],
            minimum_seeders=0,
        )
        self._qbittorrent = QbittorrentRuntimeSnapshot(url="", username="", password="")
        self._downloads = DownloadRuntimeSnapshot(allowed_dirs=[], default_dir="/downloads")

        self.reset_to_env()

    def reset_to_env(self) -> None:
        with self._lock:
            prowlarr_url = _normalize_url(str(settings.PROWLARR_URL))
            qb_url = _normalize_url(str(settings.QB_URL))
            qb_username = getattr(settings, "QB_USER", "") or ""
            allowlist = _parse_list(getattr(settings, "PROWLARR_ALLOWLIST", None))
            blocklist = _parse_list(getattr(settings, "PROWLARR_BLOCKLIST", None))
            category_filters = _parse_list(
                getattr(settings, "PROWLARR_CATEGORY_FILTERS", None)
            )
            minimum_seeders = max(0, int(getattr(settings, "PROWLARR_MINIMUM_SEEDERS", 0)))
            prowlarr_key = self._store.get("prowlarr_api_key")
            qb_url_store = self._store.get("qbittorrent_url")
            qb_username_store = self._store.get("qbittorrent_username")
            qb_password = self._store.get("qbittorrent_password")

            if not isinstance(prowlarr_key, str) or not prowlarr_key.strip():
                prowlarr_key = getattr(settings, "PROWLARR_API_KEY", None) or None
                if not prowlarr_key:
                    prowlarr_key = _read_prowlarr_api_key_from_volume()
                if prowlarr_key:
                    self._store.set("prowlarr_api_key", prowlarr_key)
            elif self._store.get("prowlarr_api_key") != prowlarr_key:
                self._store.set("prowlarr_api_key", prowlarr_key)

            if isinstance(qb_url_store, str) and qb_url_store.strip():
                qb_url = _normalize_url(qb_url_store)

            if isinstance(qb_username_store, str) and qb_username_store.strip():
                qb_username = qb_username_store.strip()

            if not isinstance(qb_password, str):
                env_password = getattr(settings, "QB_PASS", "") or ""
                qb_password = env_password if env_password else _ensure_qb_password(self._store)
            elif not qb_password:
                qb_password = _ensure_qb_password(self._store)

            if qb_url:
                self._store.set("qbittorrent_url", qb_url)
            if qb_username:
                self._store.set("qbittorrent_username", qb_username)

            self._store.set_many(
                {"qbittorrent_password": qb_password},
                allow_empty_keys={"qbittorrent_password"},
            )

            self._prowlarr = ProwlarrRuntimeSnapshot(
                url=prowlarr_url,
                api_key=prowlarr_key,
                allowlist=allowlist,
                blocklist=blocklist,
                category_filters=category_filters,
                minimum_seeders=minimum_seeders,
            )
            self._qbittorrent = QbittorrentRuntimeSnapshot(
                url=qb_url,
                username=qb_username,
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

    def prowlarr_settings(self) -> ProwlarrSettings:
        with self._lock:
            snapshot = self._prowlarr
            self._refresh_qbittorrent_from_store()
            qb = self._qbittorrent
        return ProwlarrSettings(
            prowlarr_url=snapshot.url,
            prowlarr_api_key=snapshot.api_key,
            qbittorrent_url=qb.url,
            qbittorrent_username=qb.username,
            qbittorrent_password=qb.password,
            allowlist=list(snapshot.allowlist),
            blocklist=list(snapshot.blocklist),
            category_filters=list(snapshot.category_filters),
            minimum_seeders=snapshot.minimum_seeders,
        )

    def prowlarr_snapshot(self) -> ProwlarrRuntimeSnapshot:
        with self._lock:
            return self._prowlarr

    def qbittorrent_snapshot(self) -> QbittorrentRuntimeSnapshot:
        with self._lock:
            self._refresh_qbittorrent_from_store()
            return self._qbittorrent

    def download_snapshot(self) -> DownloadRuntimeSnapshot:
        with self._lock:
            return self._downloads

    def update_prowlarr(self, *, url: Optional[str] = None, api_key: Optional[str] = None) -> bool:
        with self._lock:
            snapshot = self._prowlarr
            updated = ProwlarrRuntimeSnapshot(
                url=_normalize_url(url) if isinstance(url, str) and url.strip() else snapshot.url,
                api_key=api_key if isinstance(api_key, str) and api_key.strip() else snapshot.api_key,
                allowlist=snapshot.allowlist,
                blocklist=snapshot.blocklist,
                category_filters=snapshot.category_filters,
                minimum_seeders=snapshot.minimum_seeders,
            )
            changed = updated != snapshot
            self._prowlarr = updated

            if changed:
                if updated.url:
                    self._store.set("prowlarr_url", updated.url)
                if updated.api_key:
                    self._store.set("prowlarr_api_key", updated.api_key)

            return changed

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
                url=_normalize_url(url) if isinstance(url, str) and url.strip() else snapshot.url,
                username=username.strip() if isinstance(username, str) and username.strip() else snapshot.username,
                password=password if isinstance(password, str) else snapshot.password,
            )
            changed = updated != snapshot
            self._qbittorrent = updated

            if changed:
                if updated.url:
                    self._store.set("qbittorrent_url", updated.url)
                if updated.username:
                    self._store.set("qbittorrent_username", updated.username)
                if isinstance(password, str):
                    self._store.set_many(
                        {"qbittorrent_password": password},
                        allow_empty_keys={"qbittorrent_password"},
                    )
            return changed

    def update_downloads(self, *, allowed_dirs: list[str], default_dir: str) -> bool:
        with self._lock:
            snapshot = self._downloads
            allowed_dirs = _normalize_dirs(allowed_dirs)
            default_dir = default_dir.strip() or "/downloads"
            if default_dir not in allowed_dirs:
                allowed_dirs = [default_dir, *allowed_dirs]
            updated = DownloadRuntimeSnapshot(allowed_dirs=allowed_dirs, default_dir=default_dir)
            changed = updated != snapshot
            self._downloads = updated
            return changed

    def snapshot_for_api(self) -> dict[str, object]:
        with self._lock:
            self._refresh_qbittorrent_from_store()
            return {
                "prowlarr_url": self._prowlarr.url,
                "prowlarr_api_key_configured": bool(self._prowlarr.api_key),
                "qbittorrent_url": self._qbittorrent.url,
                "qbittorrent_username": self._qbittorrent.username,
                "downloads_allowed_dirs": list(self._downloads.allowed_dirs),
                "downloads_default_dir": self._downloads.default_dir,
            }

    def _refresh_qbittorrent_from_store(self) -> None:
        qb_url_store = self._store.get("qbittorrent_url")
        qb_username_store = self._store.get("qbittorrent_username")
        qb_password = self._store.get("qbittorrent_password")

        snapshot = self._qbittorrent
        url = snapshot.url
        username = snapshot.username
        password = snapshot.password

        if isinstance(qb_url_store, str) and qb_url_store.strip():
            url = _normalize_url(qb_url_store)
        if isinstance(qb_username_store, str) and qb_username_store.strip():
            username = qb_username_store.strip()
        if isinstance(qb_password, str):
            password = qb_password

        self._qbittorrent = QbittorrentRuntimeSnapshot(url=url, username=username, password=password)


runtime_service_settings = RuntimeServiceSettings(get_secrets_store())
