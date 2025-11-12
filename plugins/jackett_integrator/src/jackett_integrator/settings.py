"""Utilities for working with Jackett Integrator settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


DEFAULTS: dict[str, Any] = {
    "JACKETT_URL": "http://jackett:9117",
    "JACKETT_API_KEY": None,
    "QBITTORRENT_URL": "http://qbittorrent:8080",
    "QBITTORRENT_USERNAME": "",
    "QBITTORRENT_PASSWORD": "",
    "ALLOWLIST": [],
    "BLOCKLIST": [],
    "CATEGORY_FILTERS": [],
    "MINIMUM_SEEDERS": 0,
}


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        result = [str(item).strip() for item in value if str(item).strip()]
        return result
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
class PluginSettings:
    jackett_url: str = field(default_factory=lambda: str(DEFAULTS["JACKETT_URL"]))
    jackett_api_key: str | None = None
    qbittorrent_url: str = field(
        default_factory=lambda: str(DEFAULTS["QBITTORRENT_URL"])
    )
    qbittorrent_username: str = ""
    qbittorrent_password: str = ""
    allowlist: list[str] = field(default_factory=list)
    blocklist: list[str] = field(default_factory=list)
    category_filters: list[str] = field(default_factory=list)
    minimum_seeders: int = 0

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any] | None) -> "PluginSettings":
        values = dict(values or {})

        def _get(key: str) -> Any:
            if key in values:
                return values[key]
            if key in DEFAULTS:
                return DEFAULTS[key]
            return None

        jackett_url = str(_get("JACKETT_URL") or DEFAULTS["JACKETT_URL"]).rstrip("/")
        qb_url = str(_get("QBITTORRENT_URL") or DEFAULTS["QBITTORRENT_URL"]).rstrip("/")

        settings = cls(
            jackett_url=jackett_url,
            jackett_api_key=_get("JACKETT_API_KEY") or None,
            qbittorrent_url=qb_url,
            qbittorrent_username=str(_get("QBITTORRENT_USERNAME") or "").strip(),
            qbittorrent_password=str(_get("QBITTORRENT_PASSWORD") or "").strip(),
            allowlist=_as_list(_get("ALLOWLIST")),
            blocklist=_as_list(_get("BLOCKLIST")),
            category_filters=_as_list(_get("CATEGORY_FILTERS")),
            minimum_seeders=_ensure_non_negative_int(_get("MINIMUM_SEEDERS"), 0),
        )
        return settings

    def validate(self) -> None:
        if not self.jackett_url:
            raise ValueError("JACKETT_URL must be provided")
        if not self.qbittorrent_url:
            raise ValueError("QBITTORRENT_URL must be provided")
        if not self.qbittorrent_username:
            raise ValueError("QBITTORRENT_USERNAME must be provided")
        if not self.qbittorrent_password:
            raise ValueError("QBITTORRENT_PASSWORD must be provided")

    def apply_overrides(self, overrides: Mapping[str, Any]) -> None:
        for key, value in overrides.items():
            normalized = key.upper()
            if normalized == "JACKETT_URL":
                self.jackett_url = str(value).strip().rstrip("/") or self.jackett_url
            elif normalized == "JACKETT_API_KEY":
                self.jackett_api_key = str(value).strip() or None
            elif normalized == "QBITTORRENT_URL":
                self.qbittorrent_url = (
                    str(value).strip().rstrip("/") or self.qbittorrent_url
                )
            elif normalized == "QBITTORRENT_USERNAME":
                self.qbittorrent_username = str(value).strip()
            elif normalized == "QBITTORRENT_PASSWORD":
                self.qbittorrent_password = str(value).strip()
            elif normalized == "ALLOWLIST":
                self.allowlist = _as_list(value)
            elif normalized == "BLOCKLIST":
                self.blocklist = _as_list(value)
            elif normalized == "CATEGORY_FILTERS":
                self.category_filters = _as_list(value)
            elif normalized == "MINIMUM_SEEDERS":
                self.minimum_seeders = _ensure_non_negative_int(
                    value, self.minimum_seeders
                )

    def to_store_mapping(self) -> dict[str, Any]:
        return {
            "JACKETT_URL": self.jackett_url,
            "JACKETT_API_KEY": self.jackett_api_key,
            "QBITTORRENT_URL": self.qbittorrent_url,
            "QBITTORRENT_USERNAME": self.qbittorrent_username,
            "QBITTORRENT_PASSWORD": self.qbittorrent_password,
            "ALLOWLIST": list(self.allowlist),
            "BLOCKLIST": list(self.blocklist),
            "CATEGORY_FILTERS": list(self.category_filters),
            "MINIMUM_SEEDERS": self.minimum_seeders,
        }


def load_settings(
    store: Any, overrides: Mapping[str, Any] | None = None
) -> PluginSettings:
    values: dict[str, Any] = {}
    if store is not None:
        try:
            fetched = store.all()
        except AttributeError as exc:  # pragma: no cover - defensive
            raise TypeError("Settings store does not expose 'all'") from exc
        if isinstance(fetched, Mapping):
            values.update(fetched)
    if overrides:
        values.update(overrides)
    settings = PluginSettings.from_mapping(values)
    return settings


def persist_settings(
    store: Any, settings: PluginSettings, *, validate: bool = True
) -> None:
    if validate:
        settings.validate()
    payload = settings.to_store_mapping()
    setter = getattr(store, "set_many", None)
    if callable(setter):
        setter(payload)
        return
    set_single = getattr(store, "set", None)
    if not callable(set_single):  # pragma: no cover - defensive
        raise TypeError("Settings store does not expose 'set_many' or 'set'")
    for key, value in payload.items():
        set_single(key, value)


def schema_definition() -> dict[str, Any]:
    """Return the settings schema for registration purposes."""

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "JACKETT_URL": {
                "type": "string",
                "title": "Jackett URL",
                "default": DEFAULTS["JACKETT_URL"],
            },
            "JACKETT_API_KEY": {
                "type": "string",
                "title": "Jackett API key",
                "description": "Automatically detected on first enable.",
            },
            "QBITTORRENT_URL": {
                "type": "string",
                "title": "qBittorrent URL",
                "default": DEFAULTS["QBITTORRENT_URL"],
            },
            "QBITTORRENT_USERNAME": {
                "type": "string",
                "title": "qBittorrent username",
            },
            "QBITTORRENT_PASSWORD": {
                "type": "string",
                "title": "qBittorrent password",
            },
            "ALLOWLIST": {
                "type": "array",
                "title": "Indexer allowlist",
                "items": {"type": "string"},
            },
            "BLOCKLIST": {
                "type": "array",
                "title": "Indexer blocklist",
                "items": {"type": "string"},
            },
            "CATEGORY_FILTERS": {
                "type": "array",
                "title": "Category filters",
                "items": {"type": "string"},
            },
            "MINIMUM_SEEDERS": {
                "type": "integer",
                "title": "Minimum seeders",
                "default": DEFAULTS["MINIMUM_SEEDERS"],
                "minimum": 0,
            },
        },
        "required": ["QBITTORRENT_USERNAME", "QBITTORRENT_PASSWORD"],
    }


__all__ = ["PluginSettings", "load_settings", "persist_settings", "schema_definition"]
