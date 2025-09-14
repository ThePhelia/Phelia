from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
import logging

from app.db.session import SessionLocal
from app.db import models
from app.services.search.torznab import TorznabClient

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
    trackers = db.query(models.Tracker).filter(models.Tracker.enabled == True).all()
    if not trackers:
        raise HTTPException(400, "No torznab trackers configured")

    tc = TorznabClient()
    out: list[dict] = []
    for tr in trackers:
        try:
            out.extend(tc.search(tr.torznab_url, query))
        except Exception as e:
            logger.warning("Error searching tracker %s: %s", tr.display_name, e)
            continue

    return {"total": len(out), "items": out[:200]}

