from __future__ import annotations

from typing import Dict, List, Tuple

import httpx
import pytest

from app.core.runtime_settings import runtime_settings

from phelia.discovery import cache, service


class DummyRedis:
    def __init__(self) -> None:
        self.store: Dict[str, str] = {}

    async def get(self, key: str):  # type: ignore[override]
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):  # type: ignore[override]
        self.store[key] = value


@pytest.fixture(autouse=True)
async def reset_cache(monkeypatch):
    dummy = DummyRedis()
    monkeypatch.setattr(cache, "_redis_client", dummy, raising=False)
    monkeypatch.setattr(cache, "_ensure_client", lambda: dummy, raising=False)
    runtime_settings.reset_to_env()
    runtime_settings.update_many(
        {
            "lastfm": None,
            "listenbrainz": None,
            "spotify_client_id": None,
            "spotify_client_secret": None,
        }
    )
    service._PROVIDER_CACHE.clear()
    yield
    service._PROVIDER_CACHE.clear()
    runtime_settings.reset_to_env()


class MockAsyncClient:
    def __init__(self, responses: List[Tuple[int, dict]], calls: List[Tuple[str, dict | None]]):
        self._responses = responses
        self._calls = calls

    async def __aenter__(self) -> "MockAsyncClient":
        return self

    async def __aexit__(self, _exc_type, _exc, _tb) -> None:  # noqa: ANN001
        return None

    async def get(self, url: str, params: dict | None = None, **_kwargs) -> httpx.Response:  # type: ignore[override]
        self._calls.append((url, params))
        if not self._responses:
            raise AssertionError(f"Unexpected HTTP GET to {url}")
        status, payload = self._responses.pop(0)
        request = httpx.Request("GET", url, params=params)
        return httpx.Response(status, json=payload, request=request)

    async def post(self, url: str, data=None, headers=None, **_kwargs):  # type: ignore[override]
        raise AssertionError("POST not expected in tests")


@pytest.mark.anyio
async def test_get_charts_uses_cache(monkeypatch):
    monkeypatch.setenv("DEEZER_ENABLED", "true")
    responses = [
        (
            200,
            {
                "data": [
                    {
                        "id": 1,
                        "title": "Test Album",
                        "artist": {"name": "Example"},
                        "release_date": "2024-01-01",
                        "cover": "https://example.com/cover.jpg",
                        "link": "https://deezer.com/album/1",
                    }
                ]
            },
        )
    ]
    calls: List[Tuple[str, dict | None]] = []
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *_args, **_kwargs: MockAsyncClient(responses, calls),
    )

    first = await service.get_charts(market="US", limit=5)
    assert len(first) == 1
    assert calls and calls[0][0].startswith("https://api.deezer.com/chart/2/albums")

    second = await service.get_charts(market="US", limit=5)
    assert len(second) == 1
    assert len(calls) == 1


@pytest.mark.anyio
async def test_get_tag_enriches_from_itunes(monkeypatch):
    runtime_settings.set("lastfm", "key")
    monkeypatch.setenv("ITUNES_ENABLED", "true")
    monkeypatch.delenv("DEEZER_ENABLED", raising=False)
    responses = [
        (
            200,
            {
                "albums": {
                    "album": [
                        {
                            "name": "Shoegaze Album",
                            "artist": {"name": "Dream Artist"},
                            "url": "https://last.fm/album",
                            "image": [],
                        }
                    ]
                }
            },
        ),
        (
            200,
            {
                "results": [
                    {
                        "collectionId": 10,
                        "collectionName": "Shoegaze Album",
                        "artistName": "Dream Artist",
                        "artworkUrl100": "https://example.com/art.jpg",
                        "releaseDate": "2024-02-02T00:00:00Z",
                        "collectionViewUrl": "https://itunes.com/album",
                    }
                ]
            },
        ),
    ]
    calls: List[Tuple[str, dict | None]] = []
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *_args, **_kwargs: MockAsyncClient(responses, calls),
    )

    items = await service.get_tag(tag="shoegaze", limit=5)
    assert len(items) == 1
    item = items[0]
    assert str(item.cover_url) == "https://example.com/art.jpg"
    assert item.release_date == "2024-02-02"


@pytest.mark.anyio
async def test_providers_status_flags(monkeypatch):
    runtime_settings.set("lastfm", "key")
    runtime_settings.set("spotify_client_id", None)
    runtime_settings.set("spotify_client_secret", None)
    runtime_settings.set("listenbrainz", None)
    monkeypatch.setenv("DEEZER_ENABLED", "true")
    monkeypatch.setenv("ITUNES_ENABLED", "true")
    monkeypatch.setenv("MUSICBRAINZ_ENABLED", "true")

    status = await service.providers_status()
    assert status.lastfm is True
    assert status.deezer is True
    assert status.spotify is False
