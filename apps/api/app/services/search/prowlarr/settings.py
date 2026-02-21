"""Utilities for configuring Prowlarr-backed search providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings


DEFAULTS: dict[str, Any] = {
    "PROWLARR_URL": "http://prowlarr:9696",
    "PROWLARR_API_KEY": None,
    "ALLOWLIST": [],
    "BLOCKLIST": [],
    "CATEGORY_FILTERS": [],
    "MINIMUM_SEEDERS": 0,
}


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        items: list[str] = []
        for chunk in value.replace(",", "\n").splitlines():
            chunk = chunk.strip()
            if chunk:
                items.append(chunk)
        return items
    return [str(value).strip()]


def _ensure_non_negative_int(value: Any, fallback: int = 0) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return number if number >= 0 else fallback


@dataclass(slots=True)
class ProwlarrSettings:
    prowlarr_url: str = field(default_factory=lambda: str(DEFAULTS["PROWLARR_URL"]))
    prowlarr_api_key: str | None = None
    qbittorrent_url: str = ""
    qbittorrent_username: str = ""
    qbittorrent_password: str = ""
    allowlist: list[str] = field(default_factory=list)
    blocklist: list[str] = field(default_factory=list)
    category_filters: list[str] = field(default_factory=list)
    minimum_seeders: int = 0

    @classmethod
    def from_config(cls, config: Settings) -> "ProwlarrSettings":
        prowlarr_url = str(getattr(config, "PROWLARR_URL", None) or DEFAULTS["PROWLARR_URL"]).rstrip(
            "/"
        )
        qb_url = str(config.QB_URL).rstrip("/")
        return cls(
            prowlarr_url=prowlarr_url,
            prowlarr_api_key=(getattr(config, "PROWLARR_API_KEY", None) or None),
            qbittorrent_url=qb_url,
            qbittorrent_username=config.QB_USER or "",
            qbittorrent_password=config.QB_PASS or "",
            allowlist=_as_list(getattr(config, "PROWLARR_ALLOWLIST", None)),
            blocklist=_as_list(getattr(config, "PROWLARR_BLOCKLIST", None)),
            category_filters=_as_list(getattr(config, "PROWLARR_CATEGORY_FILTERS", None)),
            minimum_seeders=_ensure_non_negative_int(
                getattr(config, "PROWLARR_MINIMUM_SEEDERS", DEFAULTS["MINIMUM_SEEDERS"]),
                DEFAULTS["MINIMUM_SEEDERS"],
            ),
        )

    def is_configured(self) -> bool:
        return bool(self.prowlarr_api_key)


__all__ = ["ProwlarrSettings"]
