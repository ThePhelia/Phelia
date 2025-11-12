"""Helpers for building canonical search payloads."""

from __future__ import annotations

from typing import Tuple

from app.schemas.meta import (
    CanonicalAlbum,
    CanonicalMovie,
    CanonicalPayload,
    CanonicalTV,
    StartIndexingPayload,
)


def _clean(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split()).strip()


def build_movie(
    title: str | None, year: int | None, fallback: str
) -> Tuple[str, CanonicalMovie]:
    """Return the canonical query + payload for a movie."""

    base_title = _clean(title) or _clean(fallback)
    query = base_title
    if year:
        query = f"{query} {year}" if query else str(year)
    movie = CanonicalMovie(title=base_title or fallback.strip(), year=year)
    return query.strip(), movie


def build_tv(
    title: str | None,
    season: int | None,
    episode: int | None,
    fallback: str,
) -> Tuple[str, CanonicalTV]:
    """Return the canonical query + payload for a TV episode/series."""

    base_title = _clean(title) or _clean(fallback)
    parts: list[str] = [part for part in [base_title] if part]
    if season is not None:
        if episode is not None:
            parts.append(f"S{season:02d}E{episode:02d}")
        else:
            parts.append(f"S{season:02d}")
    elif episode is not None:
        parts.append(f"E{episode:02d}")
    query = " ".join(parts)
    tv_payload = CanonicalTV(
        title=base_title or fallback.strip(), season=season, episode=episode
    )
    return query.strip(), tv_payload


def build_album(
    artist: str | None,
    album: str | None,
    year: int | None,
    fallback: str,
) -> Tuple[str, CanonicalAlbum]:
    """Return the canonical query + payload for an album."""

    clean_artist = _clean(artist)
    clean_album = _clean(album) or _clean(fallback)
    pieces: list[str] = []
    if clean_artist and clean_album:
        pieces.append(f"{clean_artist} - {clean_album}")
    elif clean_artist:
        pieces.append(clean_artist)
    elif clean_album:
        pieces.append(clean_album)
    if year:
        pieces.append(str(year))
    query = " ".join(pieces)
    album_payload = CanonicalAlbum(
        artist=clean_artist or artist or "",
        album=clean_album or fallback.strip(),
        year=year,
    )
    return query.strip(), album_payload


def build_from_payload(payload: StartIndexingPayload) -> CanonicalPayload:
    """Construct a :class:`CanonicalPayload` ensuring the query follows naming rules."""

    base = _clean(payload.canonicalTitle)
    if payload.type == "movie":
        query, movie = build_movie(
            getattr(payload.movie, "title", None),
            getattr(payload.movie, "year", None),
            base,
        )
        query = query or base
        return CanonicalPayload(query=query or base, movie=movie)
    if payload.type == "tv":
        query, tv_payload = build_tv(
            getattr(payload.tv, "title", None),
            getattr(payload.tv, "season", None),
            getattr(payload.tv, "episode", None),
            base,
        )
        query = query or base
        return CanonicalPayload(query=query or base, tv=tv_payload)
    if payload.type == "album":
        query, album = build_album(
            getattr(payload.album, "artist", None),
            getattr(payload.album, "album", None),
            getattr(payload.album, "year", None),
            base,
        )
        query = query or base
        return CanonicalPayload(query=query or base, album=album)
    raise ValueError(f"Unsupported payload type: {payload.type}")


__all__ = [
    "build_movie",
    "build_tv",
    "build_album",
    "build_from_payload",
]
