"""Pydantic schemas shared with the web frontend.

These mirror the TypeScript interfaces defined in
``apps/web/src/app/lib/types.ts`` so that the API contract stays in
lock-step with the UI expectations.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


MediaKind = Literal["movie", "tv", "album"]


class DiscoverItem(BaseModel):
    """Short-form representation of a media item for UI grids/rails."""

    model_config = ConfigDict(extra="allow")

    kind: MediaKind
    id: str
    title: str
    subtitle: str | None = None
    year: int | None = None
    poster: str | None = None
    backdrop: str | None = None
    rating: float | None = None
    genres: list[str] | None = None
    badges: list[str] | None = None
    progress: float | None = None
    meta: dict[str, Any] | None = None


class LibraryPlaylist(BaseModel):
    """Playlist grouping inside the user's library."""

    id: str
    title: str
    items: list[DiscoverItem] = Field(default_factory=list)


class LibrarySummary(BaseModel):
    """Aggregated lists rendered on the Library route."""

    watchlist: list[DiscoverItem] = Field(default_factory=list)
    favorites: list[DiscoverItem] = Field(default_factory=list)
    playlists: list[LibraryPlaylist] = Field(default_factory=list)


class ListMutationItem(BaseModel):
    """Payload describing a media item being added/removed."""

    model_config = ConfigDict(extra="allow")

    kind: MediaKind
    id: str
    title: str | None = None
    subtitle: str | None = None
    year: int | None = None
    poster: str | None = None
    backdrop: str | None = None
    rating: float | None = None
    genres: list[str] | None = None
    badges: list[str] | None = None
    progress: float | None = None
    meta: dict[str, Any] | None = None


class ListMutationInput(BaseModel):
    """Mutation request for library lists (watchlist/favorites/playlists)."""

    action: Literal["add", "remove"]
    list: Literal["watchlist", "favorites", "playlist"]
    item: ListMutationItem
    playlist_id: str | None = Field(
        default=None, description="Target playlist identifier"
    )
    playlist_title: str | None = Field(
        default=None, description="Optional title when creating a new playlist"
    )


class CastMember(BaseModel):
    name: str
    role: str | None = None
    photo: str | None = None


class CrewMember(BaseModel):
    name: str
    job: str | None = None


class TrackInfo(BaseModel):
    index: int
    title: str
    length: int | None = None


class EpisodeInfo(BaseModel):
    episode_number: int
    title: str
    watched: bool | None = None
    runtime: int | None = None


class SeasonInfo(BaseModel):
    season_number: int
    name: str | None = None
    episodes: list[EpisodeInfo] = Field(default_factory=list)


class AvailabilityInfo(BaseModel):
    streams: list[dict[str, str | None]] | None = None
    torrents: list[dict[str, str | int | None]] | None = None


class ExternalLink(BaseModel):
    label: str
    url: str


class DetailLinks(BaseModel):
    play: str | None = None
    jellyfin: str | None = None
    external: list[ExternalLink] | None = None


class MusicBrainzInfo(BaseModel):
    artist_id: str | None = None
    artist_name: str | None = None
    release_group_id: str | None = None


class DetailResponse(BaseModel):
    """Comprehensive media details rendered on the detail page."""

    id: str
    kind: MediaKind
    title: str
    year: int | None = None
    tagline: str | None = None
    overview: str | None = None
    poster: str | None = None
    backdrop: str | None = None
    rating: float | None = None
    genres: list[str] | None = None
    cast: list[CastMember] | None = None
    crew: list[CrewMember] | None = None
    tracks: list[TrackInfo] | None = None
    seasons: list[SeasonInfo] | None = None
    similar: list[DiscoverItem] | None = None
    recommended: list[DiscoverItem] | None = None
    links: DetailLinks | None = None
    availability: AvailabilityInfo | None = None
    musicbrainz: MusicBrainzInfo | None = None


class CapabilitiesResponse(BaseModel):
    """Service capability information for the settings page."""

    services: dict[str, bool]
    version: str
    links: dict[str, str | None] | None = None
