"""Helpers for translating Torznab responses into Phelia-friendly records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, Iterable
import xml.etree.ElementTree as ET


TORZNAB_NS = {"torznab": "http://torznab.com/schemas/2015/feed"}


def _parse_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _parse_datetime(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        return parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None


@dataclass(slots=True)
class NormalizedResult:
    """Normalized representation of a Torznab search result."""

    title: str
    guid: str | None
    link: str | None
    magnet: str | None
    torrent_url: str | None
    enclosure_length: int | None
    categories: list[str] = field(default_factory=list)
    indexer: str | None = None
    size: int = 0
    seeders: int = 0
    peers: int = 0
    pub_date: datetime | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    description: str | None = None

    @property
    def tracker(self) -> str | None:
        return self.indexer or self.attributes.get("tracker") or None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "guid": self.guid,
            "link": self.link,
            "magnet": self.magnet,
            "torrent_url": self.torrent_url,
            "enclosure_length": self.enclosure_length,
            "categories": list(self.categories),
            "indexer": self.indexer,
            "size": self.size,
            "seeders": self.seeders,
            "peers": self.peers,
            "pub_date": self.pub_date.isoformat() if self.pub_date else None,
            "attributes": dict(self.attributes),
            "description": self.description,
        }


class TorznabNormalizerError(RuntimeError):
    """Raised when a Torznab payload cannot be parsed."""


def parse_torznab(xml_payload: str | bytes) -> list[NormalizedResult]:
    """Parse Torznab XML into normalized results."""

    if not xml_payload:
        return []

    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError as exc:  # pragma: no cover - defensive guard
        raise TorznabNormalizerError("Failed to parse Torznab XML") from exc

    channel = root.find("channel")
    if channel is None:
        return []

    results: list[NormalizedResult] = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        guid_text = item.findtext("guid") or None
        link_text = item.findtext("link") or None
        description = item.findtext("description") or None

        magnet = None
        if guid_text and guid_text.startswith("magnet:"):
            magnet = guid_text.strip()
        elif link_text and link_text.startswith("magnet:"):
            magnet = link_text.strip()

        attr_map: dict[str, Any] = {}
        for attr in item.findall("torznab:attr", TORZNAB_NS):
            name = attr.attrib.get("name")
            value = attr.attrib.get("value")
            if not name:
                continue
            attr_map[name.lower()] = value
            if name.lower() == "magneturl" and isinstance(value, str):
                magnet = value.strip()

        enclosure = item.find("enclosure")
        torrent_url = None
        enclosure_length = None
        if enclosure is not None:
            torrent_url = enclosure.attrib.get("url") or None
            enclosure_length = (
                _parse_int(enclosure.attrib.get("length"), default=0) or None
            )

        size = _parse_int(attr_map.get("size") or item.findtext("size"), 0)
        seeders = _parse_int(attr_map.get("seeders"), 0)
        peers = _parse_int(attr_map.get("peers"), 0)

        categories = [
            (cat.text or "").strip()
            for cat in item.findall("category")
            if (cat.text or "").strip()
        ]
        indexer_candidates: Iterable[str] = [
            attr_map.get("indexer"),
            attr_map.get("jackettindexer"),
            attr_map.get("site"),
            attr_map.get("tracker"),
            attr_map.get("indexername"),
        ]
        indexer = next(
            (str(candidate).strip() for candidate in indexer_candidates if candidate),
            None,
        )

        pub_date = _parse_datetime(item.findtext("pubDate"))

        result = NormalizedResult(
            title=title or "Untitled",
            guid=guid_text,
            link=link_text,
            magnet=magnet,
            torrent_url=torrent_url,
            enclosure_length=enclosure_length,
            categories=categories,
            indexer=indexer,
            size=size,
            seeders=seeders,
            peers=peers,
            pub_date=pub_date,
            attributes=attr_map,
            description=description,
        )

        if not result.magnet and torrent_url and "magnet" in (torrent_url or ""):
            result.magnet = torrent_url

        results.append(result)

    return results


__all__ = ["NormalizedResult", "parse_torznab", "TorznabNormalizerError"]
