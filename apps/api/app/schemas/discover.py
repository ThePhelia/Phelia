"""Pydantic models describing discovery responses consumed by the web UI."""

from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field


MediaKind = Literal["movie", "tv", "album"]


class DiscoverItem(BaseModel):
    """Compact representation of a media card returned by discovery APIs."""

    kind: MediaKind
    id: str
    title: str
    subtitle: str | None = None
    year: int | None = None
    poster: str | None = None
    backdrop: str | None = None
    rating: float | None = Field(default=None, ge=0.0)
    genres: list[str] = Field(default_factory=list)
    badges: list[str] = Field(default_factory=list)
    progress: float | None = Field(default=None, ge=0.0, le=1.0)
    meta: dict[str, Any] | None = None


T = TypeVar("T", bound=BaseModel)


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated payload shape used across discovery endpoints."""

    page: int = Field(ge=1)
    total_pages: int = Field(ge=1)
    items: list[T] = Field(default_factory=list)


class SearchResponse(PaginatedResponse[DiscoverItem]):
    """Paginated response with optional metadata for search results."""

    message: str | None = None
    error: str | None = None

    model_config = {
        "extra": "allow",
    }
