from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
import httpx
#
# If your module previously imported/defined `discovery_service` and `GENRES_BY_ID`,
# keep them present. This file is resilient: it will use them when available,
# and gracefully fall back to MusicBrainz/CAA when not.
#

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])

# Slug -> MusicBrainz tag normalization for common genres.
# Extend freely; keys are slugs you use in the UI.
GENRE_SLUG_TO_MB_TAG: Dict[str, str] = {
    "techno": "techno",
    "house": "house",
    "ambient": "ambient",
    "drum-and-bass": "drum and bass",
    "dnb": "drum and bass",
    "metal": "metal",
    "rock": "rock",
    "hip-hop": "hip hop",
    "hiphop": "hip hop",
    "electronic": "electronic",
    "indie": "indie",
    "pop": "pop",
    "jazz": "jazz",
    "classical": "classical",
}

def _safe_get_mb_tag_from_id(genre_id: Optional[int]) -> Optional[str]:
    """Resolve a MusicBrainz tag from internal GENRES_BY_ID mapping if it exists."""
    if genre_id is None:
        return None
    mapping = globals().get("GENRES_BY_ID")
    if not mapping:
        return None
    # mapping may be a dict with int or str keys. Values can be objects or dicts.
    rec = mapping.get(genre_id) or mapping.get(str(genre_id))
    if not rec:
        return None
    # Try object attribute first, then dict.
    mb_tag = getattr(rec, "musicbrainz_tag", None)
    if not mb_tag and isinstance(rec, dict):
        mb_tag = rec.get("musicbrainz_tag")
    return mb_tag

def _normalize_genre(tag: Optional[str], genre_id: Optional[int]) -> str:
    """Normalize input (?genre=slug OR ?genre_id=INT) into a MusicBrainz tag."""
    mb_tag = _safe_get_mb_tag_from_id(genre_id)
    if mb_tag:
        return mb_tag
    if tag:
        t = GENRE_SLUG_TO_MB_TAG.get(tag.strip().lower())
        if t:
            return t
    raise HTTPException(status_code=400, detail="Unknown genre/genre_id")

async def _mb_get_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    headers = {"User-Agent": "Phelia/1.0 (self-hosted)"}
    async with httpx.AsyncClient(timeout=15.0, headers=headers) as cx:
        r = await cx.get(url, params=params)
        r.raise_for_status()
        return r.json()

@router.get("/genres")
async def list_genres():
    """Return your curated/static genres list (kept as-is if previously implemented)."""
    # If your project has a function like discovery_service.list_genres(), use it.
    svc = globals().get("discovery_service")
    if svc and hasattr(svc, "list_genres"):
        try:
            items = await svc.list_genres()  # type: ignore[func-returns-value]
            if items is not None:
                return items
        except Exception:
            pass
    # Minimal fallback. Replace with your actual static list if you have one.
    return [{"slug": k, "name": k.replace('-', ' ').title()} for k in sorted(GENRE_SLUG_TO_MB_TAG)]

@router.get("/new")
async def new_albums(
    genre_id: Optional[int] = Query(None, description="Internal genre id"),
    genre: Optional[str] = Query(None, description="Genre slug, e.g., 'techno'"),
    days: int = Query(30, ge=1, le=120),
    limit: int = Query(24, ge=1, le=100),
):
    """Newly released albums for a given genre (keyless fallback supported)."""
    mb_tag = _normalize_genre(genre, genre_id)
    since = (datetime.utcnow() - timedelta(days=days)).date().isoformat()

    # Try existing provider first if discovery_service is available.
    svc = globals().get("discovery_service")
    if svc and hasattr(svc, "fetch_new_albums"):
        try:
            releases = await svc.fetch_new_albums(mb_tag, since, limit)  # type: ignore[arg-type]
            if releases:
                if isinstance(releases, dict):
                    return releases
                return {"items": releases}
        except Exception:
            # fall through to MB fallback if provider errors out
            pass

    # MusicBrainz fallback (no keys required)
    query = f'tag:"{mb_tag}" AND primarytype:Album AND firstreleasedate:[{since} TO *]'
    data = await _mb_get_json(
        "https://musicbrainz.org/ws/2/release-group",
        {"query": query, "fmt": "json", "limit": str(limit), "offset": "0"},
    )
    out = []
    for rg in data.get("release-groups", []):
        out.append({
            "id": rg.get("id"),
            "title": rg.get("title"),
            "artist": (rg.get("artist-credit") or [{}])[0].get("name"),
            "year": (rg.get("first-release-date") or "")[:4],
            "cover": f"https://coverartarchive.org/release-group/{rg.get('id')}/front-250",
            "source": "musicbrainz",
        })
    return {"items": out}

@router.get("/top")
async def top_albums(
    genre_id: Optional[int] = Query(None),
    genre: Optional[str] = Query(None),
    kind: str = Query("albums", pattern="^(albums|artists)$"),
    feed: str = Query("most-recent", pattern="^(most-recent|weekly|monthly)$"),
    limit: int = Query(24, ge=1, le=100),
):
    """Top albums (or artists) for a given genre; provider first, MB fallback next."""
    mb_tag = _normalize_genre(genre, genre_id)

    # Try existing provider first
    svc = globals().get("discovery_service")
    if svc and hasattr(svc, "fetch_top"):
        try:
            items = await svc.fetch_top(kind=kind, tag=mb_tag, feed=feed, limit=limit)  # type: ignore[arg-type]
            if items:
                if isinstance(items, dict):
                    return items
                return {"items": items}
        except Exception:
            # fall back to MB on any provider error
            pass

    # MusicBrainz fallback: get artists by tag, then latest album for each
    ar = await _mb_get_json(
        "https://musicbrainz.org/ws/2/artist",
        {"query": f'tag:"{mb_tag}"', "fmt": "json", "limit": str(min(50, max(10, limit * 2)))},
    )
    results = []
    for a in ar.get("artists", []):
        rg = await _mb_get_json(
            "https://musicbrainz.org/ws/2/release-group",
            {"query": f'artist:{a.get("id")} AND primarytype:Album', "fmt": "json", "limit": "1"},
        )
        rj = rg.get("release-groups", [])
        if not rj:
            continue
        rg0 = rj[0]
        results.append({
            "id": rg0.get("id"),
            "title": rg0.get("title"),
            "artist": a.get("name"),
            "year": (rg0.get("first-release-date") or "")[:4],
            "cover": f'https://coverartarchive.org/release-group/{rg0.get("id")}/front-250',
            "source": "musicbrainz",
        })
        if len(results) >= limit:
            break
    return {"items": results}
