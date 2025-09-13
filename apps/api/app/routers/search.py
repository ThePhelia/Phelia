from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
import json
import logging

from app.db.session import SessionLocal
from app.db import models
from app.services.search.torznab import TorznabClient
import base64

router = APIRouter(prefix="/search", tags=["search"])
logger = logging.getLogger(__name__)

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
        raise HTTPException(400, "No torznab trackers configured")

    tc = TorznabClient()
    out: list[dict] = []
    for tr in trackers:
        creds = json.loads(tr.creds_enc or "{}")
        api_key = creds.get("api_key")
        username = tr.username
        password = base64.b64decode(tr.password_enc).decode() if tr.password_enc else None
        if not api_key and not (username and password):
            logger.warning("Tracker %s missing credentials", tr.name)
            continue
        try:
            out.extend(tc.search(tr.base_url, api_key, query, username, password))
        except Exception as e:
            logger.warning("Error searching tracker %s: %s", tr.name, e)
            continue

    return {"total": len(out), "items": out[:200]}

