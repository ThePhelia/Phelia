from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import json
import logging

from app.db.session import get_db
from app.db import models
from app.services.search.torznab import TorznabClient

router = APIRouter(prefix="/search", tags=["search"])
logger = logging.getLogger(__name__)


@router.get("")
def search(query: str = Query(min_length=2), db: Session = Depends(get_db)) -> dict[str, Any]:
    trackers = (
        db.query(models.Tracker)
          .filter(models.Tracker.enabled, models.Tracker.type == "torznab")
          .all()
    )
    if not trackers:
        return {"total": 0, "items": []}

    tc = TorznabClient()
    out: list[dict] = []
    for tr in trackers:
        creds = json.loads(tr.creds_enc or "{}")
        api_key = creds.get("api_key")
        if not api_key:
            logger.warning("Tracker %s missing api_key, skipping", tr.base_url or tr.name)
            continue
        try:
            out.extend(tc.search(tr.base_url, api_key, query))
        except Exception as e:
            logger.warning("Error searching tracker %s: %s", tr.base_url or tr.name, e)
            continue

    # simple normalization: keep only items with magnet
    items = [i for i in out if i.get("magnet")]
    return {"total": len(items), "items": items[:100]}

