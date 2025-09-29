from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl

Source = Literal[
    "lastfm",
    "deezer",
    "itunes",
    "musicbrainz",
    "listenbrainz",
    "spotify",
]


class AlbumItem(BaseModel):
    id: str
    canonical_key: str
    source: Source
    title: str
    artist: str
    release_date: Optional[str] = None
    cover_url: Optional[HttpUrl] = None
    source_url: Optional[HttpUrl] = None
    tags: List[str] = Field(default_factory=list)
    market: Optional[str] = None
    score: Optional[float] = None
    preview_url: Optional[HttpUrl] = None
    extra: Dict[str, str] = Field(default_factory=dict)


class DiscoveryResponse(BaseModel):
    provider: Source
    items: List[AlbumItem] = Field(default_factory=list)


class ProvidersStatus(BaseModel):
    lastfm: bool
    deezer: bool
    itunes: bool
    musicbrainz: bool
    listenbrainz: bool
    spotify: bool
