import datetime
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.routes import discovery as discovery_routes
from app.services import discovery_apple, discovery_mb


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:  # noqa: ARG002 - ttl unused
        self.store[key] = value


@pytest.mark.anyio
async def test_new_releases_by_genre_query_and_normalisation(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDt:
        class date:
            @staticmethod
            def today() -> datetime.date:
                return datetime.date(2024, 5, 20)

        timedelta = datetime.timedelta

    captured: dict[str, Any] = {}

    def fake_get(path: str, params: dict[str, str], timeout: int = 12) -> dict[str, Any]:  # noqa: ARG001
        captured["path"] = path
        captured["params"] = params
        return {
            "release-groups": [
                {
                    "id": "rg-1",
                    "title": "Sample Album",
                    "artist-credit": [{"name": "Test Artist"}],
                    "first-release-date": "2024-05-01",
                    "primary-type": "Album",
                    "secondary-types": ["Live"],
                }
            ]
        }

    monkeypatch.setattr(discovery_mb, "dt", FakeDt)
    monkeypatch.setattr(discovery_mb, "_get", fake_get)

    items = discovery_mb.new_releases_by_genre("techno", days=10, limit=5)

    assert captured["path"] == "release-group"
    query = captured["params"]["query"]
    assert "tag:\"techno\"" in query
    assert "firstreleasedate:[2024-05-10 TO 2024-05-20]" in query
    assert captured["params"]["limit"] == "5"

    assert items[0]["artist"] == "Test Artist"
    assert items[0]["firstReleaseDate"] == "2024-05-01"
    assert items[0]["secondaryTypes"] == ["Live"]


def test_new_releases_by_genre_handles_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("GET", "https://musicbrainz.org/ws/2/release-group")

    def failing_get(path: str, params: dict[str, str], timeout: int = 12) -> dict[str, object]:  # noqa: ARG001
        response = httpx.Response(status_code=503, request=request)
        raise httpx.HTTPStatusError("service unavailable", request=request, response=response)

    monkeypatch.setattr(discovery_mb, "_get", failing_get)

    items = discovery_mb.new_releases_by_genre("techno", days=10, limit=5)

    assert items == []


@pytest.mark.anyio
async def test_discovery_new_endpoint_uses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()

    calls: list[tuple[str, int, int]] = []

    def fake_service(genre: str, days: int, limit: int) -> list[dict[str, Any]]:
        calls.append((genre, days, limit))
        return [
            {
                "mbid": "rg-1",
                "title": "Cached Album",
                "artist": "Cache Band",
            }
        ]

    monkeypatch.setattr(discovery_routes, "new_releases_by_genre", fake_service, raising=False)
    monkeypatch.setattr(discovery_routes, "get_redis", lambda: fake_redis, raising=False)

    app = FastAPI()
    app.include_router(discovery_routes.router)
    app.dependency_overrides[discovery_routes.get_redis] = lambda: fake_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp1 = await client.get("/api/v1/discovery/new", params={"genre": "house", "days": 30, "limit": 20})
        resp2 = await client.get("/api/v1/discovery/new", params={"genre": "house", "days": 30, "limit": 20})

    assert resp1.status_code == 200
    assert resp1.json()["items"][0]["title"] == "Cached Album"
    assert resp2.json() == resp1.json()
    assert calls == [("house", 30, 20)]


@pytest.mark.anyio
async def test_discovery_new_endpoint_wraps_mb_results(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_mb_get_json(url: str, params: dict[str, str]) -> dict[str, Any]:  # noqa: ARG001
        return {
            "release-groups": [
                {
                    "id": "rg-1",
                    "title": "Fallback Album",
                    "artist-credit": [{"name": "Fallback Artist"}],
                    "first-release-date": "2024-05-01",
                }
            ]
        }

    monkeypatch.setattr(discovery_routes, "_mb_get_json", fake_mb_get_json)

    app = FastAPI()
    app.include_router(discovery_routes.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/discovery/new", params={"genre": "techno", "limit": 5})

    assert resp.status_code == 200
    payload = resp.json()
    assert "items" in payload
    assert isinstance(payload["items"], list)
    assert payload["items"][0]["title"] == "Fallback Album"


@pytest.mark.anyio
async def test_discovery_new_endpoint_wraps_provider_results(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDiscoveryService:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, int]] = []

        async def fetch_new_albums(self, tag: str, since: str, limit: int) -> list[dict[str, Any]]:
            self.calls.append((tag, since, limit))
            return [
                {
                    "id": "svc-1",
                    "title": "Service Album",
                }
            ]

    svc = FakeDiscoveryService()

    async def fail_mb_get_json(*args: Any, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG001
        raise AssertionError("MusicBrainz fallback should not be called")

    monkeypatch.setattr(discovery_routes, "discovery_service", svc, raising=False)
    monkeypatch.setattr(discovery_routes, "_mb_get_json", fail_mb_get_json)

    app = FastAPI()
    app.include_router(discovery_routes.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/discovery/new", params={"genre": "techno", "limit": 5})

    assert resp.status_code == 200
    payload = resp.json()
    assert "items" in payload
    assert isinstance(payload["items"], list)
    assert payload["items"][0]["title"] == "Service Album"
    assert svc.calls  # service was invoked


@pytest.mark.anyio
async def test_discovery_top_endpoint_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()

    def failing_service(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:  # noqa: ARG001 - we only raise
        raise RuntimeError("upstream failure")

    monkeypatch.setattr(discovery_routes, "apple_feed", failing_service, raising=False)
    monkeypatch.setattr(discovery_routes, "get_redis", lambda: fake_redis, raising=False)

    app = FastAPI()
    app.include_router(discovery_routes.router)
    app.dependency_overrides[discovery_routes.get_redis] = lambda: fake_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/discovery/top",
            params={"genre_id": 21, "feed": "most-recent", "kind": "albums", "limit": 10},
        )

    assert resp.status_code == 502
    assert "Apple RSS error" in resp.json()["detail"]


@pytest.mark.anyio
async def test_discovery_top_endpoint_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()
    calls: list[tuple[int, str, str, int, str]] = []

    def fake_service(storefront: str, genre_id: int, feed: str, kind: str, limit: int) -> list[dict[str, Any]]:
        calls.append((genre_id, feed, kind, limit, storefront))
        return [
            {
                "id": "apple-1",
                "title": "Fresh Album",
                "artist": "Apple Trio",
            }
        ]

    monkeypatch.setattr(discovery_routes, "apple_feed", fake_service, raising=False)
    monkeypatch.setattr(discovery_routes, "get_redis", lambda: fake_redis, raising=False)

    app = FastAPI()
    app.include_router(discovery_routes.router)
    app.dependency_overrides[discovery_routes.get_redis] = lambda: fake_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp1 = await client.get(
            "/api/v1/discovery/top",
            params={"genre_id": 21, "feed": "most-recent", "kind": "albums", "limit": 10},
        )
        resp2 = await client.get(
            "/api/v1/discovery/top",
            params={"genre_id": 21, "feed": "most-recent", "kind": "albums", "limit": 10},
        )

    assert resp1.status_code == 200
    assert resp1.json()["items"][0]["title"] == "Fresh Album"
    assert resp2.json() == resp1.json()
    assert calls == [(21, "most-recent", "albums", 10, "us")]


@pytest.mark.anyio
async def test_discovery_top_endpoint_wraps_mb_results(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_mb_get_json(url: str, params: dict[str, str]) -> dict[str, Any]:  # noqa: ARG001
        if url.endswith("/artist"):
            return {
                "artists": [
                    {
                        "id": "artist-1",
                        "name": "Fallback Artist",
                    }
                ]
            }
        return {
            "release-groups": [
                {
                    "id": "rg-1",
                    "title": "Fallback Album",
                    "first-release-date": "2023-09-01",
                }
            ]
        }

    monkeypatch.setattr(discovery_routes, "_mb_get_json", fake_mb_get_json)

    app = FastAPI()
    app.include_router(discovery_routes.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/discovery/top",
            params={"genre": "techno", "limit": 1},
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert "items" in payload
    assert isinstance(payload["items"], list)
    assert payload["items"][0]["artist"] == "Fallback Artist"


@pytest.mark.anyio
async def test_discovery_top_endpoint_wraps_provider_results(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDiscoveryService:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, str, int]] = []

        async def fetch_top(self, *, kind: str, tag: str, feed: str, limit: int) -> list[dict[str, Any]]:
            self.calls.append((kind, tag, feed, limit))
            return [
                {
                    "id": "svc-1",
                    "title": "Service Album",
                }
            ]

    svc = FakeDiscoveryService()

    async def fail_mb_get_json(*args: Any, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG001
        raise AssertionError("MusicBrainz fallback should not be called")

    monkeypatch.setattr(discovery_routes, "discovery_service", svc, raising=False)
    monkeypatch.setattr(discovery_routes, "_mb_get_json", fail_mb_get_json)

    app = FastAPI()
    app.include_router(discovery_routes.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/discovery/top",
            params={"genre": "techno", "limit": 5},
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert "items" in payload
    assert isinstance(payload["items"], list)
    assert payload["items"][0]["title"] == "Service Album"
    assert svc.calls


@pytest.mark.anyio
async def test_discovery_providers_status_with_service(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDiscoveryService:
        async def providers_status(self) -> dict[str, bool]:
            return {"lastfm": True, "spotify": True}

    monkeypatch.setattr(discovery_routes, "discovery_service", FakeDiscoveryService(), raising=False)

    app = FastAPI()
    app.include_router(discovery_routes.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/discovery/providers/status")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["lastfm"] is True
    assert payload["spotify"] is True
    assert payload["deezer"] is False


@pytest.mark.anyio
async def test_discovery_search_endpoint_uses_service(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDiscoveryService:
        async def search(self, query: str, limit: int) -> list[dict[str, str]]:  # noqa: ARG002
            return [
                {
                    "id": "svc-1",
                    "title": "Service Album",
                    "artist": "Mixer",
                    "source": "spotify",
                }
            ]

    async def fake_mb_get_json(url: str, params: dict[str, str]) -> dict[str, Any]:  # noqa: ARG001
        return {"release-groups": []}

    monkeypatch.setattr(discovery_routes, "discovery_service", FakeDiscoveryService(), raising=False)
    monkeypatch.setattr(discovery_routes, "_mb_get_json", fake_mb_get_json)

    app = FastAPI()
    app.include_router(discovery_routes.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/discovery/search", params={"q": "techno", "limit": 3})

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["items"]
    assert payload["items"][0]["title"] == "Service Album"
    assert payload["items"][0]["source"] == "spotify"


@pytest.mark.anyio
async def test_discovery_search_endpoint_falls_back_to_mb(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_mb_get_json(url: str, params: dict[str, str]) -> dict[str, Any]:  # noqa: ARG001
        return {
            "release-groups": [
                {
                    "id": "rg-123",
                    "title": "MB Album",
                    "artist-credit": [{"name": "MB Artist"}],
                    "first-release-date": "2024-05-01",
                }
            ]
        }

    monkeypatch.setattr(discovery_routes, "discovery_service", None, raising=False)
    monkeypatch.setattr(discovery_routes, "_mb_get_json", fake_mb_get_json)

    app = FastAPI()
    app.include_router(discovery_routes.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/discovery/search", params={"q": "ambient", "limit": 2})

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["items"]
    assert payload["items"][0]["artist"] == "MB Artist"


@pytest.mark.anyio
async def test_discovery_similar_artists_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()
    calls: list[tuple[str, int]] = []

    def fake_similar(artist_mbid: str, limit: int) -> list[dict[str, Any]]:
        calls.append((artist_mbid, limit))
        return [
            {"mbid": "artist-1", "name": "Example Artist", "score": 0.91},
        ]

    monkeypatch.setattr(discovery_routes, "similar_artists", fake_similar, raising=False)
    monkeypatch.setattr(discovery_routes, "get_redis", lambda: fake_redis, raising=False)

    app = FastAPI()
    app.include_router(discovery_routes.router)
    app.dependency_overrides[discovery_routes.get_redis] = lambda: fake_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp1 = await client.get(
            "/api/v1/discovery/similar-artists",
            params={"artist_mbid": "artist-main", "limit": 5},
        )
        resp2 = await client.get(
            "/api/v1/discovery/similar-artists",
            params={"artist_mbid": "artist-main", "limit": 5},
        )

    assert resp1.status_code == 200
    assert resp1.json()["items"][0]["name"] == "Example Artist"
    assert resp2.json() == resp1.json()
    assert calls == [("artist-main", 5)]


def test_apple_feed_normalises(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyResponse:
        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload
            self.status_code = 200
            self.ok = True

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return self._payload

    def fake_get(url: str, timeout: int = 10):  # noqa: ARG001 - signature compatibility
        return DummyResponse(
            {
                "feed": {
                    "results": [
                        {
                            "id": "123",
                            "name": "Test Album",
                            "artistName": "Test Artist",
                            "url": "https://example.com/album",
                            "artworkUrl100": "https://example.com/art.jpg",
                            "releaseDate": "2024-03-01",
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr(discovery_apple.httpx, "get", fake_get)

    items = discovery_apple.apple_feed("us", 21)
    assert items == [
        {
            "id": "123",
            "title": "Test Album",
            "artist": "Test Artist",
            "url": "https://example.com/album",
            "artwork": "https://example.com/art.jpg",
            "releaseDate": "2024-03-01",
        }
    ]
