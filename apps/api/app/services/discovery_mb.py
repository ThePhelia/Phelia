import datetime as dt
import time
from typing import Dict, List

import httpx

UA = "Phelia/1.0 (contact: admin@example.com)"
BASE = "https://musicbrainz.org/ws/2"


def _get(path: str, params: Dict[str, str], timeout: int = 12) -> dict:
    for attempt in range(3):
        response = httpx.get(
            f"{BASE}/{path}",
            params=params,
            headers={"User-Agent": UA},
            timeout=timeout,
        )
        if response.status_code in (503, 429):
            time.sleep(1.5 * (attempt + 1))
            continue
        response.raise_for_status()
        return response.json()
    response.raise_for_status()


def new_releases_by_genre(genre: str, days: int = 30, limit: int = 50) -> List[Dict[str, object]]:
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    query = (
        "primarytype:album AND status:official "
        f"AND firstreleasedate:[{start.isoformat()} TO {end.isoformat()}] "
        f'AND tag:"{genre}"'
    )
    data = _get("release-group", {"query": query, "fmt": "json", "limit": str(limit)})
    items: List[Dict[str, object]] = []
    for release_group in data.get("release-groups", []):
        credits = release_group.get("artist-credit", [])
        artists: List[str] = []
        for credit in credits:
            if isinstance(credit, dict):
                name = credit.get("name")
                if name:
                    artists.append(str(name))
        items.append(
            {
                "mbid": release_group.get("id"),
                "title": release_group.get("title"),
                "artist": " & ".join(artists),
                "firstReleaseDate": release_group.get("first-release-date"),
                "primaryType": release_group.get("primary-type"),
                "secondaryTypes": release_group.get("secondary-types") or [],
            }
        )
    return items


__all__ = ["new_releases_by_genre"]
