from __future__ import annotations

import json
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models
from app.services.jackett_adapter import JackettAdapter

router = APIRouter(prefix="/trackers", tags=["trackers"])


class ProviderInfo(BaseModel):
    slug: str
    name: str
    type: str = Field(default="public", pattern="^(public|private)$")
    configured: bool = False
    needs: List[str] = []


class TrackerOut(BaseModel):
    id: int
    slug: str
    name: str
    enabled: bool
    torznab_url: str
    requires_auth: bool = False


class ToggleIn(BaseModel):
    enabled: bool


class ToggleOut(BaseModel):
    enabled: bool


class TestOut(BaseModel):
    ok: bool
    latency_ms: Optional[float] = None


def get_adapter() -> JackettAdapter:
    return JackettAdapter()


def _tracker_to_dto(tr: "models.Tracker") -> TrackerOut:
    return TrackerOut(
        id=tr.id,
        slug=getattr(tr, "provider_slug"),
        name=getattr(tr, "display_name"),
        enabled=getattr(tr, "enabled"),
        torznab_url=getattr(tr, "torznab_url"),
        requires_auth=bool(getattr(tr, "requires_auth", False)),
    )


@router.get("/providers", response_model=List[ProviderInfo])
def list_providers(adapter: JackettAdapter = Depends(get_adapter)):
    items = adapter.list_available()
    configured = set(adapter.list_configured())
    out: List[ProviderInfo] = []
    for it in items:
        slug = it["slug"]
        out.append(
            ProviderInfo(
                slug=slug,
                name=it.get("name", slug),
                type=it.get("type", "public"),
                configured=slug in configured or bool(it.get("configured")),
                needs=it.get("needs", []),
            )
        )
    seen, uniq = set(), []
    for p in out:
        if p.slug in seen:
            continue
        seen.add(p.slug)
        uniq.append(p)
    return uniq


@router.get("", response_model=List[TrackerOut])
def list_trackers(db: Session = Depends(get_db)):
    q = db.query(models.Tracker).order_by(models.Tracker.id.asc()).all()
    return [_tracker_to_dto(x) for x in q]


@router.post("/providers/{slug}/connect")
def connect_provider(
    slug: str,
    body: Optional[dict[str, Any]] = Body(default=None),
    db: Session = Depends(get_db),
    adapter: JackettAdapter = Depends(get_adapter),
):
    try:
        adapter.ensure_installed(slug, body if body else None)
    except ValueError as ve:
        msg = str(ve)
        if msg.startswith("missing_credentials"):
            needs: List[str] = []
            if ":" in msg:
                needs_str = msg.split(":", 1)[1]
                try:
                    needs = json.loads(needs_str) if needs_str.strip().startswith("[") else []
                except Exception:
                    needs = []
            raise HTTPException(status_code=400, detail={"error": "missing_credentials", "needs": needs})
        raise
    except PermissionError:
        raise HTTPException(status_code=400, detail={"error": "auth_failed"})
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"jackett_error:{e}")

    torznab_url = adapter.get_torznab_url(slug)
    try:
        _ = adapter.fetch_caps(slug)
    except Exception:
        pass

    tr = (
        db.query(models.Tracker)
        .filter(models.Tracker.provider_slug == slug)
        .one_or_none()
    )
    if tr is None:
        tr = models.Tracker(
            provider_slug=slug,
            display_name=slug,
            type="private" if body else "public",
            enabled=True,
            torznab_url=torznab_url,
            jackett_indexer_id=None,
            requires_auth=bool(body),
        )
        db.add(tr)
        db.commit()
        db.refresh(tr)
    else:
        tr.enabled = True
        tr.torznab_url = torznab_url
        db.commit()
        db.refresh(tr)

    return {"ok": True, "tracker": _tracker_to_dto(tr).model_dump()}


@router.post("/{tracker_id}/toggle", response_model=ToggleOut)
def toggle_tracker(
    tracker_id: int,
    payload: ToggleIn,
    db: Session = Depends(get_db),
):
    tr = db.query(models.Tracker).filter(models.Tracker.id == tracker_id).one_or_none()
    if tr is None:
        raise HTTPException(status_code=404, detail="not_found")
    tr.enabled = bool(payload.enabled)
    db.commit()
    return ToggleOut(enabled=tr.enabled)


@router.post("/{tracker_id}/test", response_model=TestOut)
def test_tracker(
    tracker_id: int,
    db: Session = Depends(get_db),
    adapter: JackettAdapter = Depends(get_adapter),
):
    tr = db.query(models.Tracker).filter(models.Tracker.id == tracker_id).one_or_none()
    if tr is None:
        raise HTTPException(status_code=404, detail="not_found")
    if not tr.torznab_url:
        raise HTTPException(status_code=400, detail="no_torznab_url")
    ok, latency = adapter.test_search(tr.torznab_url, q="test")
    return TestOut(ok=ok, latency_ms=latency)


@router.delete("/{tracker_id}")
def delete_tracker(
    tracker_id: int,
    db: Session = Depends(get_db),
):
    tr = db.query(models.Tracker).filter(models.Tracker.id == tracker_id).one_or_none()
    if tr is None:
        raise HTTPException(status_code=404, detail="not_found")
    db.delete(tr)
    db.commit()
    return {"ok": True}

