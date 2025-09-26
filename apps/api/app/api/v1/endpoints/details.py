"""Detailed media lookup endpoint."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.media import Classification
from app.schemas.ui import DetailLinks, DetailResponse, DiscoverItem, MusicBrainzInfo
from app.services import library as library_service
from app.services.metadata import get_metadata_router
from app.services.metadata.providers.tmdb import TMDB_IMAGE_BASE


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/details", tags=["details"])


def _normalise_kind(kind: str) -> tuple[str, str]:
    mapping = {
        "movie": "movie",
        "tv": "tv",
        "album": "music",
        "music": "music",
    }
    if kind not in mapping:
        raise HTTPException(status_code=404, detail="unsupported_kind")
    return ("album" if mapping[kind] == "music" else kind, mapping[kind])


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, str):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
    except (TypeError, ValueError):
        return None
    return None


def _ensure_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _parse_genres(extra: dict | None) -> list[str] | None:
    if not extra:
        return None
    genres = extra.get("genres")
    if isinstance(genres, list):
        names: list[str] = []
        for item in genres:
            if isinstance(item, dict) and item.get("name"):
                names.append(str(item["name"]))
            elif isinstance(item, str):
                names.append(item)
        return names or None
    return None


def _collect_people(credits: dict | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not credits:
        return [], []
    cast_items = []
    crew_items = []
    cast = credits.get("cast") if isinstance(credits, dict) else None
    if isinstance(cast, list):
        for person in cast[:12]:
            if not isinstance(person, dict):
                continue
            cast_items.append(
                {
                    "name": person.get("name") or person.get("original_name") or "",
                    "role": person.get("character"),
                    "photo": f"{TMDB_IMAGE_BASE}{person['profile_path']}"
                    if person.get("profile_path")
                    else None,
                }
            )
    crew = credits.get("crew") if isinstance(credits, dict) else None
    if isinstance(crew, list):
        for person in crew[:12]:
            if not isinstance(person, dict):
                continue
            crew_items.append(
                {
                    "name": person.get("name") or person.get("original_name") or "",
                    "job": person.get("job"),
                }
            )
    return cast_items, crew_items


def _map_tmdb_item(result: dict[str, Any], kind: str) -> DiscoverItem:
    title = result.get("title") or result.get("name") or "Untitled"
    poster = result.get("poster_path")
    backdrop = result.get("backdrop_path")
    year = None
    date_key = "release_date" if kind == "movie" else "first_air_date"
    date_value = result.get(date_key)
    if isinstance(date_value, str) and len(date_value) >= 4:
        try:
            year = int(date_value[:4])
        except ValueError:
            year = None
    return DiscoverItem(
        kind="album" if kind == "music" else kind,
        id=str(result.get("id")),
        title=title,
        year=year,
        poster=f"{TMDB_IMAGE_BASE}{poster}" if poster else None,
        backdrop=f"{TMDB_IMAGE_BASE}{backdrop}" if backdrop else None,
        rating=_safe_float(result.get("vote_average")),
        meta={"source": "tmdb"},
    )


def _extract_similar(payload: dict | None, kind: str) -> list[DiscoverItem] | None:
    if not payload:
        return None
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return None
    items = []
    for result in results[:12]:
        if not isinstance(result, dict):
            continue
        items.append(_map_tmdb_item(result, kind))
    return items or None


def _extract_tracks(discogs: dict | None) -> list[dict[str, Any]] | None:
    discogs_data = _ensure_dict(discogs)
    if not discogs_data:
        return None
    tracklist = _ensure_dict(discogs_data.get("extra")).get("tracklist")
    if not isinstance(tracklist, list):
        return None
    tracks = []
    for idx, track in enumerate(tracklist, start=1):
        if not isinstance(track, dict):
            continue
        title = track.get("title")
        if not title:
            continue
        length = track.get("duration")
        duration_seconds = None
        if isinstance(length, str) and ":" in length:
            try:
                minutes, seconds = length.split(":", 1)
                duration_seconds = int(minutes) * 60 + int(seconds)
            except Exception:  # pragma: no cover - defensive
                duration_seconds = None
        tracks.append({"index": idx, "title": title, "length": duration_seconds})
    return tracks or None


def _build_detail(card, response_kind: str, item_id: str, snapshot: dict | None) -> DetailResponse:
    parsed = card.parsed if isinstance(card.parsed, dict) else {}
    snapshot_data = snapshot if isinstance(snapshot, dict) else {}
    details = card.details if isinstance(card.details, dict) else {}

    tmdb_data = _ensure_dict(details.get("tmdb"))
    omdb_data = _ensure_dict(details.get("omdb"))
    discogs_data = _ensure_dict(details.get("discogs"))
    lastfm_data = _ensure_dict(details.get("lastfm"))
    musicbrainz_data = _ensure_dict(details.get("musicbrainz"))

    tmdb_extra_container = _ensure_dict(tmdb_data.get("extra"))
    tmdb_extra = _ensure_dict(tmdb_extra_container.get("tmdb"))

    cast_items, crew_items = _collect_people(_ensure_dict(tmdb_extra.get("credits")))

    artist_info = _ensure_dict(musicbrainz_data.get("artist"))
    release_group_info = _ensure_dict(musicbrainz_data.get("release_group"))

    detail = DetailResponse(
        id=item_id,
        kind=response_kind,
        title=tmdb_data.get("title") or card.title,
        year=tmdb_data.get("year")
        or parsed.get("year")
        or snapshot_data.get("year"),
        tagline=tmdb_extra.get("tagline"),
        overview=tmdb_data.get("overview")
        or lastfm_data.get("summary")
        or snapshot_data.get("overview"),
        poster=tmdb_data.get("poster")
        or discogs_data.get("cover_image")
        or snapshot_data.get("poster"),
        backdrop=tmdb_data.get("backdrop") or snapshot_data.get("backdrop"),
        rating=_safe_float(omdb_data.get("imdbRating")),
        genres=_parse_genres(tmdb_extra) or snapshot_data.get("genres"),
        cast=[
            {"name": item["name"], "role": item.get("role"), "photo": item.get("photo")}
            for item in cast_items
            if item.get("name")
        ]
        or None,
        crew=[
            {"name": item["name"], "job": item.get("job")}
            for item in crew_items
            if item.get("name")
        ]
        or None,
        tracks=[
            {"index": track["index"], "title": track["title"], "length": track.get("length")}
            for track in (_extract_tracks(discogs_data) or [])
        ]
        or None,
        similar=_extract_similar(tmdb_extra.get("similar"), card.media_type),
        recommended=_extract_similar(
            tmdb_extra.get("recommendations"), card.media_type
        ),
        musicbrainz=MusicBrainzInfo(
            artist_id=artist_info.get("id"),
            artist_name=artist_info.get("name"),
            release_group_id=release_group_info.get("id"),
        ),
    )

    if response_kind == "tv" and isinstance(tmdb_extra, dict):
        seasons = tmdb_extra.get("seasons")
        if isinstance(seasons, list):
            parsed_seasons = []
            for season in seasons:
                if not isinstance(season, dict):
                    continue
                season_number = season.get("season_number")
                if season_number is None:
                    continue
                parsed_seasons.append(
                    {
                        "season_number": season_number,
                        "name": season.get("name"),
                        "episodes": [],
                    }
                )
            if parsed_seasons:
                detail.seasons = parsed_seasons

    availability = {}
    jackett = _ensure_dict(details.get("jackett"))
    if jackett:
        torrents = []
        if any(jackett.get(field) for field in ("magnet", "seeders", "tracker")):
            torrents.append(
                {
                    "provider": jackett.get("tracker") or jackett.get("indexer"),
                    "seeders": jackett.get("seeders"),
                    "size": jackett.get("size"),
                }
            )
        if torrents:
            availability["torrents"] = torrents
    if availability:
        detail.availability = availability

    links = []
    ids = card.ids if isinstance(card.ids, dict) else {}
    imdb_id = ids.get("imdb_id")
    if imdb_id:
        links.append({"label": "IMDb", "url": f"https://www.imdb.com/title/{imdb_id}"})
    if links:
        detail.links = DetailLinks(external=links)

    return detail


@router.get("/{kind}/{item_id}", response_model=DetailResponse)
async def read_detail(kind: str, item_id: str, db: Session = Depends(get_db)) -> DetailResponse:
    response_kind, classification_kind = _normalise_kind(kind)

    entry = library_service.get_entry(db, response_kind, item_id)
    snapshot = entry.snapshot if entry else None
    title = None
    if snapshot:
        title = snapshot.get("title") or snapshot.get("name")
    if not title:
        title = snapshot.get("id") if isinstance(snapshot, dict) else None
    if not title:
        title = item_id.replace("-", " ")

    classification = Classification(
        type=classification_kind,
        confidence=1.0,
        reasons=["details"],
    )

    router = get_metadata_router()
    try:
        card = await router.enrich(classification, title)
    except Exception as exc:  # pragma: no cover - logged for visibility
        logger.exception("metadata enrichment failed for %s:%s", kind, item_id)
        raise HTTPException(status_code=502, detail="metadata_error") from exc

    if card is None:
        raise HTTPException(status_code=404, detail="not_found")

    return _build_detail(card, response_kind, item_id, snapshot)
