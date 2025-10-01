"""Pydantic models shared by metadata search endpoints."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

MetaItemType = Literal["movie", "tv", "album"]


class MetaSearchItem(BaseModel):
    type: MetaItemType
    provider: str
    id: str
    title: str
    subtitle: str | None = None
    year: int | None = None
    poster: str | None = None
    extra: dict[str, Any] | None = None


class MetaSearchResponse(BaseModel):
    items: list[MetaSearchItem] = Field(default_factory=list)


class MetaCastMember(BaseModel):
    name: str
    character: str | None = None


class MetaTVInfo(BaseModel):
    seasons: int | None = Field(default=None, ge=0)
    episodes: int | None = Field(default=None, ge=0)


class MetaTrack(BaseModel):
    position: str | None = None
    title: str
    duration: str | None = None


class MetaAlbumInfo(BaseModel):
    artist: str
    album: str
    year: int | None = None
    styles: list[str] = Field(default_factory=list)
    tracklist: list[MetaTrack] = Field(default_factory=list)


class CanonicalMovie(BaseModel):
    title: str
    year: int | None = None


class CanonicalTV(BaseModel):
    title: str
    season: int | None = Field(default=None, ge=0)
    episode: int | None = Field(default=None, ge=0)


class CanonicalAlbum(BaseModel):
    artist: str
    album: str
    year: int | None = None


class CanonicalPayload(BaseModel):
    query: str
    movie: CanonicalMovie | None = None
    tv: CanonicalTV | None = None
    album: CanonicalAlbum | None = None


class MetaDetail(BaseModel):
    type: MetaItemType
    title: str
    year: int | None = None
    poster: str | None = None
    backdrop: str | None = None
    synopsis: str | None = None
    genres: list[str] = Field(default_factory=list)
    runtime: int | None = Field(default=None, ge=0)
    rating: float | None = Field(default=None, ge=0.0)
    cast: list[MetaCastMember] = Field(default_factory=list)
    tv: MetaTVInfo | None = None
    album: MetaAlbumInfo | None = None
    canonical: CanonicalPayload


class StartIndexingPayload(BaseModel):
    type: MetaItemType
    canonicalTitle: str
    movie: CanonicalMovie | None = None
    tv: CanonicalTV | None = None
    album: CanonicalAlbum | None = None


__all__ = [
    "MetaItemType",
    "MetaSearchItem",
    "MetaSearchResponse",
    "MetaDetail",
    "MetaCastMember",
    "MetaTVInfo",
    "MetaAlbumInfo",
    "MetaTrack",
    "CanonicalMovie",
    "CanonicalTV",
    "CanonicalAlbum",
    "CanonicalPayload",
    "StartIndexingPayload",
]
