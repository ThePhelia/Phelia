import asyncio

from app.schemas.media import Classification
from app.services.metadata.router import MetadataRouter


class DummyTMDB:
    api_key = "key"

    async def movie_lookup(self, title: str, year: int | None = None):
        return {
            "tmdb_id": 101,
            "title": "Blade Runner 2049",
            "year": 2017,
            "overview": "Replicants and more.",
            "poster": "http://example/poster.jpg",
            "backdrop": "http://example/backdrop.jpg",
            "imdb_id": "tt1856101",
            "extra": {"source": "tmdb"},
        }


class DummyTMDBNoImdb(DummyTMDB):
    async def movie_lookup(self, title: str, year: int | None = None):
        data = await super().movie_lookup(title, year)
        data.pop("imdb_id", None)
        return data


class DummyTMDBNoKey:
    api_key = None

    async def movie_lookup(self, title: str, year: int | None = None):
        raise AssertionError("TMDb lookup should not be called when not configured")


class DummyOMDb:
    async def fetch_by_imdb(self, imdb_id: str):
        return {"imdbID": imdb_id, "imdbRating": "8.0"}


class DummyMusicBrainz:
    async def lookup_release_group(self, artist: str | None, album: str, year: int | None = None):
        return {
            "artist": {"id": "artist-1", "name": artist},
            "release_group": {
                "id": "rg-1",
                "title": album,
                "first_release_date": "2007-10-10",
            },
        }


class DummyDiscogs:
    token = "token"

    async def lookup_release(self, artist: str | None, album: str, year: int | None, mb_release_group_id: str | None):
        return {
            "id": 55,
            "title": album,
            "year": year,
            "label": "XL Recordings",
            "catalog_number": "XLCD 324",
            "cover_image": "http://example/discogs.jpg",
            "formats": ["CD", "FLAC"],
        }


class DummyLastFM:
    api_key = "key"

    async def get_album_info(self, artist: str | None, album: str):
        return {
            "tags": ["alternative", "rock"],
            "listeners": 1000,
            "playcount": 5000,
            "summary": "A seminal record.",
            "url": "http://last.fm/album",
        }


def test_movie_enrichment_merges_providers():
    router = MetadataRouter(
        tmdb_client=DummyTMDB(),
        omdb_client=DummyOMDb(),
        musicbrainz_client=None,
        discogs_client=None,
        lastfm_client=None,
    )
    classification = Classification(type="movie", confidence=0.8, reasons=["category:movies"])
    card = asyncio.run(router.enrich(classification, "Blade Runner 2049 2160p"))

    assert card.ids["tmdb_id"] == 101
    assert card.ids["imdb_id"] == "tt1856101"
    assert card.details["omdb"]["imdbRating"] == "8.0"
    assert any(p.name == "TMDb" and p.used for p in card.providers)


def test_music_pipeline_collects_multiple_sources():
    router = MetadataRouter(
        tmdb_client=None,
        omdb_client=None,
        musicbrainz_client=DummyMusicBrainz(),
        discogs_client=DummyDiscogs(),
        lastfm_client=DummyLastFM(),
    )
    classification = Classification(type="music", confidence=0.75, reasons=["title:Artist - Album pattern"])
    card = asyncio.run(router.enrich(classification, "Radiohead - In Rainbows (2007)"))

    assert card.ids["mb_release_group_id"] == "rg-1"
    assert card.details["discogs"]["label"] == "XL Recordings"
    assert "tags" in card.details and "alternative" in card.details["tags"]
    provider_status = {p.name: p.used for p in card.providers}
    assert provider_status["MusicBrainz"] is True
    assert provider_status["Discogs"] is True
    assert provider_status["Last.fm"] is True


def test_omdb_reports_missing_imdb_id_when_available():
    router = MetadataRouter(
        tmdb_client=DummyTMDBNoImdb(),
        omdb_client=DummyOMDb(),
        musicbrainz_client=None,
        discogs_client=None,
        lastfm_client=None,
    )
    classification = Classification(type="movie", confidence=0.8, reasons=["category:movies"])
    card = asyncio.run(router.enrich(classification, "Blade Runner 2049 2160p"))

    provider_errors = {p.name: (p.extra or {}).get("error") for p in card.providers}
    assert provider_errors.get("OMDb") == "no_imdb_id"
    assert provider_errors.get("OMDb") != "not_configured"


def test_tmdb_without_credentials_reports_not_configured():
    router = MetadataRouter(
        tmdb_client=DummyTMDBNoKey(),
        omdb_client=None,
        musicbrainz_client=None,
        discogs_client=None,
        lastfm_client=None,
    )
    classification = Classification(type="movie", confidence=0.8, reasons=["category:movies"])
    card = asyncio.run(router.enrich(classification, "Some Movie"))

    providers = {p.name: p for p in card.providers}
    assert providers["TMDb"].used is False
    assert providers["TMDb"].extra == {"error": "not_configured"}
