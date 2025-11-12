from typing import Dict, List
import logging

import httpx

logger = logging.getLogger(__name__)

# iTunes RSS API endpoints
ITUNES_RSS_BASE = "https://rss.applemarketingtools.com/api/v2"
ITUNES_RSS_FALLBACK = "https://rss.itunes.apple.com/api/v1"


def apple_feed(
    storefront: str,
    genre_id: int,
    feed: str = "most-recent",
    kind: str = "albums",
    limit: int = 50,
) -> List[Dict[str, object]]:
    """Fetch Apple Music RSS feed data with fallback support."""
    
    # Try the new Apple Marketing Tools API first
    try:
        return _fetch_from_marketing_tools(storefront, genre_id, feed, kind, limit)
    except Exception as e:
        logger.warning(f"Apple Marketing Tools API failed: {e}")
    
    # Fallback to iTunes RSS API
    try:
        return _fetch_from_itunes_rss(storefront, genre_id, feed, kind, limit)
    except Exception as e:
        logger.warning(f"iTunes RSS API failed: {e}")
    
    # Return empty list if both fail
    logger.error("All Apple RSS APIs failed")
    return []


def _fetch_from_marketing_tools(
    storefront: str, genre_id: int, feed: str, kind: str, limit: int
) -> List[Dict[str, object]]:
    """Fetch from Apple Marketing Tools API."""
    # Try different URL formats
    urls_to_try = [
        f"{ITUNES_RSS_BASE}/{storefront}/music/{feed}/{kind}/{limit}/explicit.json",
        f"{ITUNES_RSS_BASE}/{storefront}/music/{feed}/{kind}/{limit}.json",
    ]
    
    if genre_id:
        urls_to_try.insert(0, f"{ITUNES_RSS_BASE}/{storefront}/music/{feed}/{kind}/{limit}/genre={genre_id}/explicit.json")
        urls_to_try.insert(1, f"{ITUNES_RSS_BASE}/{storefront}/music/{feed}/{kind}/{limit}/genre={genre_id}.json")
    
    for url in urls_to_try:
        try:
            response = httpx.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            results = data.get("feed", {}).get("results", [])
            if results:
                return _normalize_marketing_tools_results(results)
        except Exception:
            continue
    
    raise Exception("No valid Marketing Tools API endpoint found")


def _fetch_from_itunes_rss(
    storefront: str, genre_id: int, feed: str, kind: str, limit: int
) -> List[Dict[str, object]]:
    """Fetch from iTunes RSS API."""
    # Map feed types to iTunes RSS endpoints - use working endpoints
    feed_map = {
        "most-recent": "topalbums",  # newreleases doesn't work, use topalbums
        "weekly": "topalbums", 
        "monthly": "topalbums"
    }
    
    itunes_feed = feed_map.get(feed, "topalbums")
    
    # Try different working iTunes RSS endpoints
    urls_to_try = [
        f"https://itunes.apple.com/{storefront}/rss/{itunes_feed}/limit={limit}/json",
        f"https://itunes.apple.com/{storefront}/rss/{itunes_feed}/limit={limit}/explicit/json",
    ]
    
    for url in urls_to_try:
        try:
            response = httpx.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            entries = data.get("feed", {}).get("entry", [])
            if entries:
                return _normalize_itunes_results(entries)
        except Exception:
            continue
    
    raise Exception("No working iTunes RSS endpoint found")


def _normalize_marketing_tools_results(results: List[Dict]) -> List[Dict[str, object]]:
    """Normalize Apple Marketing Tools API results."""
    items: List[Dict[str, object]] = []
    for entry in results:
        items.append({
            "id": entry.get("id"),
            "title": entry.get("name"),
            "artist": entry.get("artistName"),
            "url": entry.get("url"),
            "artwork": entry.get("artworkUrl100"),
            "releaseDate": entry.get("releaseDate"),
            "source": "apple_marketing_tools"
        })
    return items


def _normalize_itunes_results(entries: List[Dict]) -> List[Dict[str, object]]:
    """Normalize iTunes RSS API results."""
    items: List[Dict[str, object]] = []
    for entry in entries:
        # Extract data from iTunes RSS format
        title = entry.get("im:name", {}).get("label", "")
        artist = entry.get("im:artist", {}).get("label", "")
        
        # Get the largest image
        images = entry.get("im:image", [])
        artwork = ""
        if images:
            artwork = images[-1].get("label", "")  # Last image is usually largest
        
        # Extract ID from the id field
        id_data = entry.get("id", {})
        item_id = ""
        if isinstance(id_data, dict):
            attrs = id_data.get("attributes", {})
            item_id = attrs.get("im:id", "")
        
        # Extract release date
        release_date = ""
        release_data = entry.get("im:releaseDate", {})
        if release_data:
            release_date = release_data.get("label", "")
        
        # Extract URL
        link_data = entry.get("link", {})
        url = ""
        if isinstance(link_data, dict):
            attrs = link_data.get("attributes", {})
            url = attrs.get("href", "")
        
        items.append({
            "id": item_id,
            "title": title,
            "artist": artist,
            "url": url,
            "artwork": artwork,
            "releaseDate": release_date,
            "source": "itunes_rss"
        })
    return items


__all__ = ["apple_feed"]
