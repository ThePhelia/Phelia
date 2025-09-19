from __future__ import annotations

import urllib.parse

import feedparser

from app.core.config import settings


JACKETT_API_KEY = settings.JACKETT_API_KEY or ""

def _pick_magnet(entry: dict) -> str | None:
    cand = entry.get("torrent_magneturi") or entry.get("magneturi") or entry.get("magneturl") or entry.get("magnet")
    if isinstance(cand, str) and cand.startswith("magnet:"):
        return cand
    links = entry.get("links") or []
    for l in links:
        href = l.get("href")
        if href and href.startswith("magnet:"):
            return href
    link = entry.get("link")
    if isinstance(link, str) and link.startswith("magnet:"):
        return link
    return None

def _pick_url(entry: dict) -> str | None:
    link = entry.get("link")
    if isinstance(link, str) and link.startswith(("http://", "https://")):
        return link
    links = entry.get("links") or []
    for l in links:
        href = l.get("href")
        if href and href.startswith(("http://", "https://")):
            return href
    return None

class TorznabClient:
    def _build_url(self, base_url: str, q: str) -> str:
        cleaned = base_url.rstrip("/")
        fragment = ""
        if "#" in cleaned:
            cleaned, fragment = cleaned.split("#", 1)

        query_string = ""
        base = cleaned
        if "?" in cleaned:
            base, query_string = cleaned.split("?", 1)

        params = urllib.parse.parse_qsl(query_string, keep_blank_values=True)

        api_key = JACKETT_API_KEY or settings.JACKETT_API_KEY
        if api_key and not any(k == "apikey" for k, _ in params):
            params.append(("apikey", api_key))

        params.append(("t", "search"))
        params.append(("q", q))

        qs = urllib.parse.urlencode(params)
        url = f"{base}?{qs}"
        if fragment:
            url = f"{url}#{fragment}"
        return url

    def search(self, base_url: str, query: str) -> list[dict]:
        url = self._build_url(base_url, query)
        feed = feedparser.parse(url)
        items: list[dict] = []
        host = urllib.parse.urlparse(base_url).netloc
        for e in getattr(feed, "entries", []):
            magnet = _pick_magnet(e)
            url_http = _pick_url(e)
            title = e.get("title")
            size = e.get("torrent_contentlength") or e.get("size")
            seeders = e.get("torrent_seeders") or e.get("seeders")
            leechers = e.get("torrent_leechers") or e.get("leechers")
            category = e.get("category") or e.get("categories")
            if isinstance(category, list):
                category = ", ".join(str(c) for c in category)
            indexer = e.get("jackettindexer") or e.get("indexer") or host
            items.append({
                "title": title,
                "magnet": magnet,
                "url": url_http,
                "size": size,
                "seeders": seeders,
                "leechers": leechers,
                "tracker": host,
                "indexer": indexer,
                "category": category,
            })
        return items

