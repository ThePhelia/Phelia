from typing import Any, Dict

import pytest

from app.schemas.media import EnrichedCard
from app.services.metadata.classifier import Classifier
from app.services import jackett_adapter


class DummyResponse:
    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:  # pragma: no cover - nothing to do
        return None

    def json(self) -> Any:  # pragma: no cover - nothing to do
        return self._payload


def test_fetch_indexers_uses_api_key(monkeypatch):
    captured: Dict[str, Any] = {}

    def fake_get(url, timeout, headers=None, **kwargs):
        captured.update({"url": url, "timeout": timeout, "headers": headers, "extra": kwargs})
        return DummyResponse([])

    monkeypatch.setattr(jackett_adapter, "JACKETT_API_KEY", "secret")
    monkeypatch.setattr(jackett_adapter.httpx, "get", fake_get)

    adapter = jackett_adapter.JackettAdapter()
    assert adapter._fetch_indexers() == []
    assert captured["headers"] == {"X-Api-Key": "secret"}


def test_get_schema_uses_api_key(monkeypatch):
    captured: Dict[str, Any] = {}

    def fake_get(url, timeout, headers=None, **kwargs):
        captured.update({"url": url, "timeout": timeout, "headers": headers, "extra": kwargs})
        return DummyResponse({"fields": []})

    monkeypatch.setattr(jackett_adapter, "JACKETT_API_KEY", "another-secret")
    monkeypatch.setattr(jackett_adapter.httpx, "get", fake_get)

    adapter = jackett_adapter.JackettAdapter()
    assert adapter._get_schema("slug") == {"fields": []}
    assert captured["headers"] == {"X-Api-Key": "another-secret"}


def test_ensure_installed_uses_api_key(monkeypatch):
    captured: Dict[str, Any] = {}

    def fake_post(url, json=None, timeout=None, headers=None, **kwargs):
        captured.update({"url": url, "json": json, "timeout": timeout, "headers": headers, "extra": kwargs})
        return DummyResponse({})

    def fake_get_schema(self, slug):
        return {"fields": []}

    monkeypatch.setattr(jackett_adapter, "JACKETT_API_KEY", "post-secret")
    monkeypatch.setattr(jackett_adapter.httpx, "post", fake_post)
    monkeypatch.setattr(jackett_adapter.JackettAdapter, "_get_schema", fake_get_schema)

    adapter = jackett_adapter.JackettAdapter()
    assert adapter.ensure_installed("slug") == {"slug": "slug", "configured": True}
    assert captured["headers"] == {"X-Api-Key": "post-secret"}


class DummyRouter:
    threshold_low = 0.55

    async def enrich(self, classification, title):
        return EnrichedCard(
            media_type=classification.type,
            confidence=classification.confidence,
            title=title,
            ids={},
            details={"enriched": True},
            providers=[],
            reasons=list(classification.reasons),
            needs_confirmation=classification.confidence < self.threshold_low,
        )


class DummyTorznab:
    def search(self, base_url: str, query: str):
        return [
            {
                "title": "Example Show Season 1 S01E01 1080p WEB-DL",
                "category": "TV",
                "indexer": {"name": "IndexerA"},
                "magnet": "magnet:?xt=urn:btih:abc",
                "url": "https://example.com/tv",
                "size": 123,
                "seeders": 50,
                "leechers": 2,
                "tracker": "tracker-a",
            },
            {
                "title": "Unknown Release",
                "category": "Misc",
                "indexer": "IndexerB",
                "magnet": None,
                "url": None,
                "size": None,
                "seeders": None,
                "leechers": None,
                "tracker": "tracker-b",
            },
        ]


@pytest.mark.anyio
async def test_search_with_metadata_returns_cards(monkeypatch):
    adapter = jackett_adapter.JackettAdapter(
        classifier=Classifier(),
        router=DummyRouter(),
    )
    adapter._torznab = DummyTorznab()

    cards, meta = await adapter.search_with_metadata("example query", limit=2)

    assert len(cards) == 2
    assert all(isinstance(card, EnrichedCard) for card in cards)
    assert cards[0].media_type == "tv"
    assert cards[0].details["jackett"]["title"] == "Example Show Season 1 S01E01 1080p WEB-DL"
    assert cards[1].media_type == "other"
    assert cards[1].needs_confirmation is True
    assert "jackett_ui_url" in meta
