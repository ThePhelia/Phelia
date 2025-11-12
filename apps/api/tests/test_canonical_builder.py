from app.schemas.meta import (
    CanonicalAlbum,
    CanonicalMovie,
    CanonicalTV,
    StartIndexingPayload,
)
from app.services.meta import canonical


def test_build_movie_canonical():
    payload = StartIndexingPayload(
        type="movie",
        canonicalTitle="Blade Runner",
        movie=CanonicalMovie(title="Blade Runner", year=1982),
    )
    result = canonical.build_from_payload(payload)
    assert result.query == "Blade Runner 1982"
    assert result.movie is not None
    assert result.movie.title == "Blade Runner"
    assert result.movie.year == 1982


def test_build_tv_canonical():
    payload = StartIndexingPayload(
        type="tv",
        canonicalTitle="The Wire",
        tv=CanonicalTV(title="The Wire", season=1, episode=1),
    )
    result = canonical.build_from_payload(payload)
    assert result.query == "The Wire S01E01"
    assert result.tv is not None
    assert result.tv.season == 1
    assert result.tv.episode == 1


def test_build_album_canonical():
    payload = StartIndexingPayload(
        type="album",
        canonicalTitle="Discovery",
        album=CanonicalAlbum(artist="Daft Punk", album="Discovery", year=2001),
    )
    result = canonical.build_from_payload(payload)
    assert result.query == "Daft Punk - Discovery 2001"
    assert result.album is not None
    assert result.album.artist == "Daft Punk"
    assert result.album.year == 2001
