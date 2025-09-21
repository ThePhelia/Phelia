"""Library endpoints backing the Library route in the web UI."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ui import LibrarySummary, ListMutationInput
from app.services import library as library_service


router = APIRouter(prefix="/library", tags=["library"])


@router.get("", response_model=LibrarySummary)
def read_library(db: Session = Depends(get_db)) -> LibrarySummary:
    return library_service.build_summary(db)


@router.post("/list")
def mutate_list(payload: ListMutationInput, db: Session = Depends(get_db)) -> dict[str, bool]:
    try:
        library_service.apply_mutation(db, payload)
    except library_service.PlaylistRequiredError as exc:
        raise HTTPException(status_code=400, detail="playlist_id_required") from exc
    except library_service.UnknownListError as exc:
        raise HTTPException(status_code=400, detail="invalid_list") from exc
    return {"success": True}
