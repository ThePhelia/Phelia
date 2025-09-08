from __future__ import annotations
import asyncio
import json
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
import feedparser
from sqlalchemy.orm import Session

from app.db import models


def _parse_torznab_feed(xml_bytes: bytes) -> List[Dict[str, Any]]:
    feed = feedparser.parse(xml_bytes)
    items: List[Dict[str, Any]] = []
    for e in feed.entries:
        magnet = None
        link = None
        if e.get("links"):
            for l in e.links:
                if l.get("type") == "application/x-bittorrent" and l.get("href"):
                    link = l["href"]
                if l.get("href", "").startswith("magnet:"):
                    magnet = l["href"]
        size = None
        seeders = None
        peers = None
        attrs = e.get("torznab_attr", []) or e.get("attrs", [])
        for a in attrs:
            name = a.get("name") if isinstance(a, dict) else a[0]
            value = a.get("value") if isinstance(a, dict) else a[1]
            if name in ("size", "contentlength"):
                try:
                    size = int(value)
                except Exception:
                    pass
            elif name == "seeders":
                try:
                    seeders = int(value)
                except Exception:
                    pass
            elif name == "peers":
                try:
                    peers = int(value)
                except Exception:
                    pass
        items.append(
            {
                "title": e.get("title"),
                "link": link,
                "magnet": magnet or link,
                "size": size,
                "seeders": seeders,
                "peers": peers,
                "guid": e.get("id"),
                "pubDate": e.get("published"),
            }
        )
    return items


async def torznab_search_one(base_url: str, api_key: str, query: str, *, timeout: float = 15.0) -> List[Dict[str, Any]]:
    params = {"t": "search", "q": query, "apikey": api_key}
    sep = "&" if "?" in base_url else "?"
    url = f"{base_url}{sep}{urlencode(params)}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url)
        r.raise_for_status()
        return _parse_torznab_feed(r.content)


async def torznab_search_all(db: Session, query: str, *, timeout: float = 15.0) -> List[Dict[str, Any]]:
    trackers: list[models.Tracker] = (
        db.query(models.Tracker).filter_by(enabled=True, type="torznab").all()
    )
    tasks = []
    for tr in trackers:
        creds = json.loads(tr.creds_enc or "{}")
        api_key: Optional[str] = creds.get("api_key")
        if not api_key:
            continue
        tasks.append(torznab_search_one(tr.base_url, api_key, query, timeout=timeout))
    if not tasks:
        return []
    results = await asyncio.gather(*tasks, return_exceptions=True)
    items: List[Dict[str, Any]] = []
    for res in results:
        if isinstance(res, Exception):
            continue
        items.extend(res)
    items.sort(key=lambda x: (x.get("seeders") or 0, x.get("size") or 0), reverse=True)
    return items

