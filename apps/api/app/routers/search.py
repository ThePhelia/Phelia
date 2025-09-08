from __future__ import annotations
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.search.torznab import torznab_search_all

router = APIRouter(prefix="/search", tags=["search"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("")
async def search(query: str = Query(..., min_length=1, max_length=200), db: Session = Depends(get_db)) -> Dict[str, Any]:
    items = await torznab_search_all(db, query)
    return {"query": query, "total": len(items), "items": items}

