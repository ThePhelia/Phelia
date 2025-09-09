from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import json

from app.db.session import SessionLocal
from app.db import models
from app.services.search.torznab import TorznabClient

router = APIRouter(prefix="/search", tags=["search"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("")
def search(query: str = Query(min_length=2), db: Session = Depends(get_db)) -> dict[str, Any]:
    trackers = (
        db.query(models.Tracker)
          .filter(models.Tracker.enabled == True, models.Tracker.type == "torznab")
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
            continue
        try:
            out.extend(tc.search(tr.base_url, api_key, query))
        except Exception:
            continue

    return {"total": len(out), "items": out[:200]}

