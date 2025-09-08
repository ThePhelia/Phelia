from __future__ import annotations
import urllib.parse
import feedparser

class TorznabClient:
    def _build_url(self, base_url: str, api_key: str, q: str) -> str:
        base = base_url.rstrip("/")
        sep = "&" if "?" in base else "?"
        qs = urllib.parse.urlencode({"t": "search", "q": q, "apikey": api_key})
        return f"{base}{sep}{qs}"

    def search(self, base_url: str, api_key: str, query: str) -> list[dict]:
        url = self._build_url(base_url, api_key, query)
        feed = feedparser.parse(url)
        items: list[dict] = []
        for e in getattr(feed, "entries", []):
            magnet = None
            for l in getattr(e, "links", []) or []:
                href = l.get("href")
                if href and href.startswith("magnet:"):
                    magnet = href
                    break
            if not magnet:
                m2 = getattr(e, "torrent_magneturi", None)
                if m2:
                    magnet = m2

            items.append({
                "title": getattr(e, "title", None),
                "magnet": magnet,
                "link": getattr(e, "link", None),
                "size": getattr(e, "torrent_contentlength", None),
                "seeders": getattr(e, "torrent_seeders", None),
                "leechers": getattr(e, "torrent_leechers", None),
                "tracker": urllib.parse.urlparse(base_url).netloc,
            })
        return items

