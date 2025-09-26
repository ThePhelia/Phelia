from typing import Dict, List

import httpx

LB_URL = "https://labs.api.listenbrainz.org/similar-artists/json"


def similar_artists(artist_mbid: str, limit: int = 20) -> List[Dict[str, object]]:
    response = httpx.get(
        LB_URL,
        params={
            "artist_mbid": artist_mbid,
            "algorithm": "session_based_days_7500_session_300_contribution_5_threshold_10_limit_100_filter_True_skip_30",
        },
        timeout=10,
    )
    response.raise_for_status()
    artists = response.json().get("similar_artists", [])
    items: List[Dict[str, object]] = []
    for entry in artists[:limit]:
        items.append(
            {
                "mbid": entry.get("artist_mbid"),
                "name": entry.get("artist_name"),
                "score": entry.get("score"),
            }
        )
    return items


__all__ = ["similar_artists"]
