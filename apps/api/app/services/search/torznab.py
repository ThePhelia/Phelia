from __future__ import annotations
import urllib.parse
import feedparser
import httpx

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
    def _build_url(self, base_url: str, api_key: str | None, q: str) -> str:
        base = base_url.rstrip("/")
        sep = "&" if "?" in base else "?"
        params = {"t": "search", "q": q}
        if api_key:
            params["apikey"] = api_key
        qs = urllib.parse.urlencode(params)
        return f"{base}{sep}{qs}"

    def search(
        self,
        base_url: str,
        api_key: str | None,
        query: str,
        username: str | None = None,
        password: str | None = None,
    ) -> list[dict]:
        url = self._build_url(base_url, api_key, query)
        if username and password:
            r = httpx.get(url, auth=(username, password))
            feed = feedparser.parse(r.content)
        else:
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
            items.append({
                "title": title,
                "magnet": magnet,
                "url": url_http,
                "size": size,
                "seeders": seeders,
                "leechers": leechers,
                "tracker": host,
            })
        return items

