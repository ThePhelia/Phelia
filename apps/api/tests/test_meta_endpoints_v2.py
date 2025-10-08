import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints import meta as meta_endpoints


class DummyTMDB:
    api_key = "test_token"

    async def search_movies(self, query: str, limit: int = 20):
        return [
            {
                "id": 101,
                "title": "Blade Runner",
                "release_date": "1982-06-25",
                "poster_path": "/movie.jpg",
                "popularity": 88.0,
            }
        ]

    async def search_tv(self, query: str, limit: int = 20):
        return [
            {
                "id": 202,
                "name": "Blade Runner 2099",
                "first_air_date": "2025-01-01",
                "poster_path": "/tv.jpg",
                "popularity": 91.0,
            }
        ]

    async def movie_details(self, tmdb_id: int):
        return {
            "id": tmdb_id,
            "title": "Blade Runner",
            "release_date": "1982-06-25",
            "overview": "A replicant hunter faces his past.",
            "poster_path": "/movie.jpg",
            "backdrop_path": "/movie-bg.jpg",
            "genres": [{"name": "Sci-Fi"}],
            "runtime": 117,
            "vote_average": 8.4,
            "credits": {"cast": [{"name": "Harrison Ford", "character": "Deckard"}]},
        }

    async def tv_details(self, tmdb_id: int):
        return {
            "id": tmdb_id,
            "name": "Blade Runner 2099",
            "first_air_date": "2025-01-01",
            "overview": "Series set in the Blade Runner universe.",
            "poster_path": "/tv.jpg",
            "backdrop_path": "/tv-bg.jpg",
            "genres": [{"name": "Sci-Fi"}],
            "episode_run_time": [55],
            "vote_average": 7.9,
            "number_of_seasons": 1,
            "number_of_episodes": 8,
            "credits": {"cast": [{"name": "Actor", "character": "Lead"}]},
        }


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


class DummyLastFM:
    api_key = "test_lastfm"

    async def search_albums(self, query: str, limit: int = 20):
        return []

    async def get_album_info(self, artist: str | None, album: str):
        return {
            "summary": "Award winning score.",
            "tags": ["Ambient"],
            "extra": {},
        }


@pytest.mark.anyio
async def test_meta_search_returns_mixed_items(monkeypatch):
    monkeypatch.setattr(meta_endpoints, "_tmdb_client", lambda: DummyTMDB())
    monkeypatch.setattr(meta_endpoints, "_discogs_client", lambda: DummyDiscogs())
    monkeypatch.setattr(meta_endpoints, "_lastfm_client", lambda: DummyLastFM())

    app = FastAPI()
    app.include_router(meta_endpoints.router, prefix="/meta")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/meta/search", params={"q": "blade"})

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert {item["type"] for item in data["items"]} == {"movie", "tv", "album"}


@pytest.mark.anyio
async def test_meta_detail_movie_builds_canonical(monkeypatch):
    monkeypatch.setattr(meta_endpoints, "_tmdb_client", lambda: DummyTMDB())

    app = FastAPI()
    app.include_router(meta_endpoints.router, prefix="/meta")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/meta/detail", params={"type": "movie", "id": "101", "provider": "tmdb"})

    assert response.status_code == 200
    detail = response.json()
    assert detail["title"] == "Blade Runner"
    assert detail["canonical"]["query"] == "Blade Runner 1982"
    assert detail["runtime"] == 117
    assert detail["cast"][0]["name"] == "Harrison Ford"


@pytest.mark.anyio
async def test_meta_detail_album_includes_tracks(monkeypatch):
    monkeypatch.setattr(meta_endpoints, "_discogs_client", lambda: DummyDiscogs())
    monkeypatch.setattr(meta_endpoints, "_lastfm_client", lambda: DummyLastFM())

    app = FastAPI()
    app.include_router(meta_endpoints.router, prefix="/meta")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/meta/detail", params={"type": "album", "id": "master:303", "provider": "discogs"})

    assert response.status_code == 200
    detail = response.json()
    assert detail["album"]["artist"] == "Vangelis"
    assert len(detail["album"]["tracklist"]) == 2
    assert detail["canonical"]["query"].startswith("Vangelis - Blade Runner")
