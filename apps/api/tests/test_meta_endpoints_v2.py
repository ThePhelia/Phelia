import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints import meta as meta_endpoints


class DummyMetadataClient:
    async def tmdb(
        self, path: str, params: dict | None = None, request_id: str | None = None
    ):
        if path == "search/movie":
            return {
                "results": [
                    {
                        "id": 101,
                        "title": "Blade Runner",
                        "release_date": "1982-06-25",
                        "poster_path": "/movie.jpg",
                        "popularity": 88.0,
                    }
                ]
            }
        if path == "search/tv":
            return {
                "results": [
                    {
                        "id": 202,
                        "name": "Blade Runner 2099",
                        "first_air_date": "2025-01-01",
                        "poster_path": "/tv.jpg",
                        "popularity": 91.0,
                    }
                ]
            }
        if path == "movie/101":
            return {
                "id": 101,
                "title": "Blade Runner",
                "release_date": "1982-06-25",
                "overview": "A replicant hunter faces his past.",
                "poster_path": "/movie.jpg",
                "backdrop_path": "/movie-bg.jpg",
                "genres": [{"name": "Sci-Fi"}],
                "runtime": 117,
                "vote_average": 8.4,
                "credits": {
                    "cast": [{"name": "Harrison Ford", "character": "Deckard"}]
                },
            }
        return {"results": []}

    async def lastfm(
        self, path: str, params: dict | None = None, request_id: str | None = None
    ):
        return {
            "album": {
                "wiki": {"summary": "Award winning score."},
                "tags": {"tag": [{"name": "Ambient"}]},
            }
        }


class TmdbFailureMetadataClient(DummyMetadataClient):
    async def tmdb(
        self, path: str, params: dict | None = None, request_id: str | None = None
    ):
        if path in {"search/movie", "search/tv"}:
            raise meta_endpoints.MetadataProxyError(502, "tmdb_unavailable")
        return await super().tmdb(path, params=params, request_id=request_id)


class DummyDiscogs:
    token = "test_discogs_token"
    base_url = "https://api.discogs.com"

    async def search_albums(self, query: str, limit: int = 20):
        return [
            {
                "id": 303,
                "title": "Vangelis - Blade Runner",
                "type": "master",
                "year": 1982,
                "cover_image": "https://images.example/album.jpg",
                "score": 77.0,
            }
        ]

    async def fetch_resource(self, url: str):
        return {
            "title": "Blade Runner",
            "year": 1982,
            "images": [{"uri": "https://images.example/album-large.jpg"}],
            "genres": ["Soundtrack"],
            "styles": ["Electronic"],
            "tracklist": [
                {"position": "A1", "title": "Main Titles", "duration": "03:42"},
                {"position": "A2", "title": "Blush Response", "duration": "05:47"},
            ],
            "artists": [{"name": "Vangelis"}],
            "notes": "Original soundtrack",
        }


@pytest.mark.anyio
async def test_meta_search_returns_mixed_items(monkeypatch):
    monkeypatch.setattr(meta_endpoints, "_metadata_client", lambda: DummyMetadataClient())
    monkeypatch.setattr(meta_endpoints, "_discogs_client", lambda: DummyDiscogs())

    app = FastAPI()
    app.include_router(meta_endpoints.router, prefix="/meta")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/meta/search", params={"q": "blade"})

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert {item["type"] for item in data["items"]} == {"movie", "tv", "album"}


@pytest.mark.anyio
async def test_meta_search_tmdb_failure_still_returns_discogs_album(monkeypatch):
    monkeypatch.setattr(
        meta_endpoints, "_metadata_client", lambda: TmdbFailureMetadataClient()
    )
    monkeypatch.setattr(meta_endpoints, "_discogs_client", lambda: DummyDiscogs())

    app = FastAPI()
    app.include_router(meta_endpoints.router, prefix="/meta")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/meta/search", params={"q": "blade"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert {item["type"] for item in payload["items"]} == {"album"}
    album = payload["items"][0]
    assert album["provider"] == "discogs"
    assert album["id"] == "master:303"
    assert album["title"] == "Blade Runner"


@pytest.mark.anyio
async def test_meta_search_provider_failure_preserves_successful_item_schema(monkeypatch):
    monkeypatch.setattr(
        meta_endpoints, "_metadata_client", lambda: TmdbFailureMetadataClient()
    )
    monkeypatch.setattr(meta_endpoints, "_discogs_client", lambda: DummyDiscogs())

    app = FastAPI()
    app.include_router(meta_endpoints.router, prefix="/meta")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/meta/search", params={"q": "blade"})

    assert response.status_code == 200
    album = response.json()["items"][0]
    assert set(album.keys()) == {
        "type",
        "provider",
        "id",
        "title",
        "subtitle",
        "year",
        "poster",
        "extra",
    }


@pytest.mark.anyio
async def test_meta_detail_movie_builds_canonical(monkeypatch):
    monkeypatch.setattr(meta_endpoints, "_metadata_client", lambda: DummyMetadataClient())

    app = FastAPI()
    app.include_router(meta_endpoints.router, prefix="/meta")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/meta/detail", params={"type": "movie", "id": "101", "provider": "tmdb"}
        )

    assert response.status_code == 200
    detail = response.json()
    assert detail["title"] == "Blade Runner"
    assert detail["canonical"]["query"] == "Blade Runner 1982"
    assert detail["runtime"] == 117
    assert detail["cast"][0]["name"] == "Harrison Ford"


@pytest.mark.anyio
async def test_meta_detail_album_includes_tracks(monkeypatch):
    monkeypatch.setattr(meta_endpoints, "_discogs_client", lambda: DummyDiscogs())
    monkeypatch.setattr(meta_endpoints, "_metadata_client", lambda: DummyMetadataClient())

    app = FastAPI()
    app.include_router(meta_endpoints.router, prefix="/meta")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/meta/detail",
            params={"type": "album", "id": "master:303", "provider": "discogs"},
        )

    assert response.status_code == 200
    detail = response.json()
    assert detail["album"]["artist"] == "Vangelis"
    assert len(detail["album"]["tracklist"]) == 2
    assert detail["canonical"]["query"].startswith("Vangelis - Blade Runner")
