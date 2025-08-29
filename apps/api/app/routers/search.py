from fastapi import APIRouter, HTTPException, Depends
from app.db.session import session_scope
from app.db.models import Tracker
from app.core.security import get_current_user
from app.services.search.torznab import TorznabClient

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("/search")
async def search(query: str):
    if not query or len(query) < 2:
        raise HTTPException(status_code=400, detail="Query too short")

    results = []

    with session_scope() as db:
        trackers = db.query(Tracker).filter_by(enabled=True).all()

    for tr in trackers:
        if tr.type == "torznab" and tr.base_url:
            client = TorznabClient(tr.base_url, tr.creds_enc)
            try:
                res = await client.search(query)
                results.extend(res)
            except Exception as e:
                print(f"[WARN] Tracker {tr.name} failed: {e}")
                continue

    results.sort(key=lambda x: (x["seeds"], x["size"]), reverse=True)

    return {
        "items": results,
        "total": len(results),
        "query": query,
    }
