from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.schemas.indexers import Indexer, IndexerConnectIn, IndexerConnectOut, IndexerTestOut
from app.api.v1.deps import get_jackett
from app.services.jackett import JackettClient

router = APIRouter(prefix="/indexers", tags=["indexers"])

@router.get("", response_model=List[Indexer])
async def list_indexers(j: JackettClient = Depends(get_jackett)):
    items = await j.list_indexers()
    return [Indexer(**it) for it in items]

@router.post("/{idx_id}/connect", response_model=IndexerConnectOut)
async def connect_indexer(idx_id: str, body: IndexerConnectIn, j: JackettClient = Depends(get_jackett)):
    creds = {}
    if body.apikey:
        creds["apiKey"] = body.apikey
    if body.username:
        creds["username"] = body.username
    if body.password:
        creds["password"] = body.password
    try:
        if creds:
            await j.set_indexer_credentials(idx_id, creds)
        test = await j.test_indexer(idx_id)
        ok = bool(test.get("success", True))
        return IndexerConnectOut(id=idx_id, configured=ok, message="ok" if ok else "failed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{idx_id}/test", response_model=IndexerTestOut)
async def test_indexer(idx_id: str, j: JackettClient = Depends(get_jackett)):
    try:
        test = await j.test_indexer(idx_id)
        ok = bool(test.get("success", True))
        return IndexerTestOut(id=idx_id, ok=ok, message="ok" if ok else "failed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

