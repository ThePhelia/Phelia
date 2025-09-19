"""Metadata lookup endpoints for the web UI."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import settings
from app.schemas.media import Classification
from app.services.metadata import get_classifier, get_metadata_router


router = APIRouter(prefix="/meta", tags=["metadata"])


class LookupRequest(BaseModel):
    title: str = Field(..., min_length=1)
    hint: Literal["music", "movie", "tv", "other", "auto"] = "auto"


@router.post("/lookup")
async def lookup(body: LookupRequest) -> dict[str, Any]:
    classifier = get_classifier()
    router_service = get_metadata_router()

    if body.hint == "auto":
        classification = classifier.classify_torrent(body.title)
    else:
        classification = Classification(
            type=body.hint if body.hint != "auto" else "other",
            confidence=0.99,
            reasons=[f"hint:{body.hint}"],
        )
    card = await router_service.enrich(classification, body.title)
    return card.model_dump()


@router.get("/providers/status")
def providers_status() -> dict[str, Any]:
    return {
        "tmdb": bool(settings.TMDB_API_KEY),
        "omdb": bool(settings.OMDB_API_KEY),
        "discogs": bool(settings.DISCOGS_TOKEN),
        "lastfm": bool(settings.LASTFM_API_KEY),
        "musicbrainz": bool(settings.MB_USER_AGENT),
    }

