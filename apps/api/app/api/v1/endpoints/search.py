"""Search endpoint returning classified + enriched torrent results."""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, Literal

from fastapi import APIRouter, Depends, Query

from app.schemas.discover import DiscoverItem, SearchResponse
from app.schemas.media import EnrichedCard
from app.services.search.registry import search_registry
from app.ext.interfaces import SearchProvider


router = APIRouter(prefix="/search", tags=["metadata-search"])


def get_provider() -> SearchProvider:
    return search_registry.primary()


def _ensure_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            return f"{value:.6g}"
        return str(value)
    return str(value)


def _ensure_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None
        try:
            return int(trimmed)
        except ValueError:
            try:
                as_float = float(trimmed)
            except ValueError:
                return None
            if as_float.is_integer():
                return int(as_float)
    return None


def _first_str(*values: Any) -> str | None:
    for value in values:
        text = _ensure_str(value)
        if text:
            return text
    return None


def _extract_genres(details: dict[str, Any]) -> list[str]:
    genres: list[str] = []
    tmdb = details.get("tmdb")
    if isinstance(tmdb, dict):
        extra = tmdb.get("extra")
        raw = None
        if isinstance(extra, dict):
            raw = extra.get("tmdb")
        if raw is None:
            raw = tmdb.get("genres")
        if isinstance(raw, dict):
            raw = raw.get("genres")
        if isinstance(raw, Iterable):
            for entry in raw:
                name = None
                if isinstance(entry, dict):
                    name = entry.get("name")
                elif isinstance(entry, str):
                    name = entry
                if isinstance(name, str) and name.strip():
                    genres.append(name.strip())
    tags = details.get("tags")
    if isinstance(tags, Iterable) and not isinstance(tags, (str, bytes)):
        for entry in tags:
            name = _ensure_str(entry)
            if name:
                genres.append(name)

    deduped: list[str] = []
    seen: set[str] = set()
    for genre in genres:
        key = genre.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(genre)
    return deduped


def _extract_rating(details: dict[str, Any]) -> float | None:
    omdb = details.get("omdb")
    if isinstance(omdb, dict):
        rating = omdb.get("imdbRating") or omdb.get("rating")
        if isinstance(rating, (int, float)):
            return float(rating)
        if isinstance(rating, str):
            try:
                return float(rating)
            except ValueError:
                pass
    return None


def _select_identifier(card: EnrichedCard, kind: str, details: dict[str, Any]) -> str:
    ids = card.ids or {}
    preferred_keys: list[str] = []
    if kind in {"movie", "tv"}:
        preferred_keys.extend(["tmdb_id", "imdb_id", "tvdb_id", "trakt_id"])
    elif kind == "album":
        preferred_keys.extend(
            [
                "mb_release_group_id",
                "mb_release_id",
                "discogs_id",
                "mb_album_id",
            ]
        )
    for key in preferred_keys:
        candidate = _ensure_str(ids.get(key))
        if candidate:
            return candidate
    for value in ids.values():
        candidate = _ensure_str(value)
        if candidate:
            return candidate

    tmdb = details.get("tmdb") if isinstance(details, dict) else None
    if isinstance(tmdb, dict):
        for key in ("tmdb_id", "imdb_id"):
            candidate = _ensure_str(tmdb.get(key))
            if candidate:
                return candidate

    musicbrainz = details.get("musicbrainz") if isinstance(details, dict) else None
    if isinstance(musicbrainz, dict):
        candidate = _ensure_str(musicbrainz.get("id") or musicbrainz.get("mbid"))
        if candidate:
            return candidate

    discogs = details.get("discogs") if isinstance(details, dict) else None
    if isinstance(discogs, dict):
        candidate = _ensure_str(discogs.get("id"))
        if candidate:
            return candidate

    fallback_source = "||".join(
        value for value in [kind, card.title] if value
    )
    if not fallback_source:
        fallback_source = f"{kind}:{card.title or 'unknown'}"
    digest = hashlib.sha1(fallback_source.encode("utf-8"), usedforsecurity=False)
    return digest.hexdigest()


def _card_to_discover_item(card: EnrichedCard) -> DiscoverItem | None:
    media_map = {"movie": "movie", "tv": "tv", "music": "album"}
    kind = media_map.get(card.media_type)
    if kind is None:
        return None

    details = card.details if isinstance(card.details, dict) else {}
    parsed = card.parsed if isinstance(card.parsed, dict) else {}
    images = details.get("images") if isinstance(details.get("images"), dict) else {}
    tmdb = details.get("tmdb") if isinstance(details.get("tmdb"), dict) else {}
    discogs = details.get("discogs") if isinstance(details.get("discogs"), dict) else {}
    musicbrainz = details.get("musicbrainz") if isinstance(details.get("musicbrainz"), dict) else {}
    title = _first_str(
        tmdb.get("title"),
        tmdb.get("name"),
        discogs.get("title"),
        musicbrainz.get("title"),
        parsed.get("album"),
        card.title,
    ) or "Untitled"

    subtitle: str | None = None
    if kind == "album":
        subtitle = _first_str(parsed.get("artist"), musicbrainz.get("artist"), details.get("artist"))
    elif kind == "tv":
        season = _ensure_int(parsed.get("season"))
        episode = _ensure_int(parsed.get("episode"))
        if season is not None and episode is not None:
            subtitle = f"S{season:02d}E{episode:02d}"
        elif season is not None:
            subtitle = f"Season {season}"

    year = _ensure_int(parsed.get("year"))
    if year is None:
        year = _ensure_int(tmdb.get("year"))
    if year is None and isinstance(musicbrainz.get("first_release_date"), str):
        year = _ensure_int(musicbrainz["first_release_date"][:4])
    if year is None:
        year = _ensure_int(discogs.get("year"))

    poster = _first_str(
        images.get("poster"),
        images.get("primary"),
        tmdb.get("poster"),
        discogs.get("cover_image"),
    )
    backdrop = _first_str(images.get("backdrop"), tmdb.get("backdrop"))

    rating = _extract_rating(details)
    genres = _extract_genres(details)

    badges: list[str] = []
    if card.needs_confirmation:
        badges.append("needs_confirmation")

    meta: dict[str, Any] = {
        "confidence": card.confidence,
        "needs_confirmation": card.needs_confirmation,
        "reasons": list(card.reasons),
        "providers": [provider.model_dump() for provider in card.providers],
        "ids": card.ids or None,
        "parsed": card.parsed,
        "source_title": card.title,
        "source_kind": card.media_type,
    }

    # Prune empty entries to keep payload compact.
    meta = {
        key: value
        for key, value in meta.items()
        if value not in (None, {}, []) or key == "providers"
    }

    identifier = _select_identifier(card, kind, details)

    return DiscoverItem(
        kind=kind,
        id=identifier,
        title=title,
        subtitle=subtitle,
        year=year,
        poster=poster,
        backdrop=backdrop,
        rating=rating,
        genres=genres,
        badges=badges,
        meta=meta or None,
    )


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=2, alias="q"),
    limit: int = Query(40, ge=1, le=100),
    kind: Literal["all", "movie", "tv", "music"] = Query("all"),
    page: int = Query(1, ge=1),
    provider: SearchProvider = Depends(get_provider),
) -> SearchResponse:
    fetch_limit = limit * page
    cards, meta = await provider.search(q, limit=fetch_limit, kind=kind)
    items: list[DiscoverItem] = []
    for card in cards:
        item = _card_to_discover_item(card)
        if item is not None:
            items.append(item)

    start = (page - 1) * limit
    end = start + limit
    page_items = items[start:end]

    response_kwargs = {"page": page, "total_pages": page, "items": page_items}
    response_kwargs.update(meta)
    return SearchResponse(**response_kwargs)

