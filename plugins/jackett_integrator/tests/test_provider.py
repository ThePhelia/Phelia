from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import pytest

from jackett_integrator.normalizer import parse_torznab
from jackett_integrator.provider import JackettProvider
from jackett_integrator.settings import PluginSettings


TORZNAB_SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<rss xmlns:torznab="http://torznab.com/schemas/2015/feed">
  <channel>
    <item>
      <title>Example.Movie.2024.1080p.WEB-DL</title>
      <guid isPermaLink="false">magnet:?xt=urn:btih:ABC123</guid>
      <link>magnet:?xt=urn:btih:ABC123</link>
      <pubDate>Mon, 27 Jan 2025 10:00:00 +0000</pubDate>
      <category>Movies</category>
      <torznab:attr name="seeders" value="42" />
      <torznab:attr name="peers" value="48" />
      <torznab:attr name="size" value="1073741824" />
      <torznab:attr name="indexer" value="ExampleIndexer" />
    </item>
    <item>
      <title>Example.Show.S01E01.720p</title>
      <guid isPermaLink="false">https://example.invalid/torrent/1</guid>
      <link>https://example.invalid/download/1.torrent</link>
      <category>TV</category>
      <torznab:attr name="seeders" value="0" />
      <torznab:attr name="peers" value="5" />
      <torznab:attr name="size" value="524288000" />
      <torznab:attr name="indexer" value="FilteredIndexer" />
    </item>
  </channel>
</rss>
"""


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeClient:
    def __init__(self, *, expected_text: str) -> None:
        self._text = expected_text
        self.captured: dict[str, object] = {}

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, url: str, params: dict[str, object]) -> _FakeResponse:
        self.captured = {"url": url, "params": params}
        return _FakeResponse(self._text)


@pytest.mark.anyio
async def test_jackett_search_returns_enriched_cards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeClient(expected_text=TORZNAB_SAMPLE)
    monkeypatch.setattr(
        "jackett_integrator.provider.httpx.AsyncClient", lambda **_: fake_client
    )

    settings = PluginSettings.from_mapping(
        {
            "JACKETT_URL": "http://jackett:9117",
            "JACKETT_API_KEY": "abc123",
            "QBITTORRENT_URL": "http://qbittorrent:8080",
            "QBITTORRENT_USERNAME": "qb",
            "QBITTORRENT_PASSWORD": "secret",
            "MINIMUM_SEEDERS": 1,
            "BLOCKLIST": ["FilteredIndexer"],
        }
    )
    provider = JackettProvider(settings=settings, logger=logging.getLogger("tests"))

    cards, meta = await provider.search("Example", limit=5, kind="movie")

    assert len(cards) == 1
    card = cards[0]
    assert card.title == "Example.Movie.2024.1080p.WEB-DL"
    assert card.details["jackett"]["seeders"] == 42
    assert meta["count"] == 1
    assert meta["jackett"]["filtered"] == 1
    descriptor = provider.descriptor()
    assert descriptor.configured is True
    assert descriptor.metadata["jackett_url"] == "http://jackett:9117"


@pytest.mark.anyio
async def test_send_to_qbittorrent_with_magnet(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = PluginSettings.from_mapping(
        {
            "JACKETT_URL": "http://jackett:9117",
            "JACKETT_API_KEY": "abc123",
            "QBITTORRENT_URL": "http://qbittorrent:8080",
            "QBITTORRENT_USERNAME": "qb",
            "QBITTORRENT_PASSWORD": "secret",
        }
    )
    provider = JackettProvider(settings=settings, logger=logging.getLogger("tests"))
    monkeypatch.setattr(
        "jackett_integrator.provider.httpx.AsyncClient",
        lambda **_: _FakeClient(expected_text=""),
    )

    added: list[str] = []

    @asynccontextmanager
    async def fake_session():
        class Dummy:
            async def add_magnet(self, magnet: str) -> None:
                added.append(magnet)

            async def add_torrent_file(
                self, data: bytes
            ) -> None:  # pragma: no cover - unused
                raise AssertionError("Should not fetch torrent file for magnet entries")

        yield Dummy()

    provider._torrent_client.session = fake_session  # type: ignore[assignment]

    results = parse_torznab(TORZNAB_SAMPLE)
    magnets = [result for result in results if result.magnet]
    created = await provider.send_to_qbittorrent(magnets)

    assert created == ["Example.Movie.2024.1080p.WEB-DL"]
    assert added == ["magnet:?xt=urn:btih:ABC123"]
