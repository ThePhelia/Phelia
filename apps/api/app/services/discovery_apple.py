from typing import Dict, List

import httpx

BASE = "https://rss.applemarketingtools.com/api/v2"


def apple_feed(
    storefront: str,
    genre_id: int,
    feed: str = "most-recent",
    kind: str = "albums",
    limit: int = 50,
) -> List[Dict[str, object]]:
    genre_segment = f"genre={genre_id}" if genre_id else "genre=all"
    url = f"{BASE}/{storefront}/music/{feed}/{kind}/{limit}/{genre_segment}/json"
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    results = response.json().get("feed", {}).get("results", [])
    items: List[Dict[str, object]] = []
    for entry in results:
        items.append(
            {
                "id": entry.get("id"),
                "title": entry.get("name"),
                "artist": entry.get("artistName"),
                "url": entry.get("url"),
                "artwork": entry.get("artworkUrl100"),
                "releaseDate": entry.get("releaseDate"),
            }
        )
    return items


__all__ = ["apple_feed"]
