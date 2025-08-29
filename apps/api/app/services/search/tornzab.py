import httpx
import feedparser
from typing import List, Dict

class TorznabClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key

    async def search(self, query: str) -> List[Dict]:
        params = {"t": "search", "q": query, "apikey": self.api_key}
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{self.base_url}/api", params=params)
            r.raise_for_status()
            feed = feedparser.parse(r.text)

        results = []
        for e in feed.entries:
            magnet = None
            torrent_url = None
            for link in e.links:
                if link.get("type") == "application/x-bittorrent":
                    torrent_url = link["href"]
                elif link.get("type") == "application/x-bittorrent; magnet":
                    magnet = link["href"]

            results.append({
                "title": e.title,
                "size": int(getattr(e, "torrent_contentlength", 0) or 0),
                "seeds": int(getattr(e, "torrent_seeds", 0) or 0),
                "leeches": int(getattr(e, "torrent_peers", 0) or 0),
                "magnet": magnet,
                "torrentUrl": torrent_url,
                "tracker": self.base_url,
                "quality": [],
            })
        return results
