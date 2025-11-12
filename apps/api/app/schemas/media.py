"""Pydantic schemas for metadata classification and enrichment."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Classification(BaseModel):
    """Result of applying metadata heuristics to a torrent title."""

    type: Literal["music", "movie", "tv", "other"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)


class EnrichedProvider(BaseModel):
    """Details about a metadata provider participating in enrichment."""

    name: str
    used: bool = False
    extra: dict | None = None


class EnrichedCard(BaseModel):
    """Unified representation of a classified + enriched media item."""

    media_type: Literal["music", "movie", "tv", "other"]
    confidence: float = Field(ge=0.0, le=1.0)
    title: str
    parsed: dict | None = None
    ids: dict = Field(default_factory=dict)
    details: dict = Field(default_factory=dict)
    providers: list[EnrichedProvider] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    needs_confirmation: bool = False
