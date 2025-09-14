from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models
from app.schemas.trackers import ProviderInfo, ProviderConnectIn, TrackerOut
from app.services.jackett_adapter import JackettAdapter

router = APIRouter(prefix="/trackers", tags=["trackers"])


def get_adapter() -> JackettAdapter:
    return JackettAdapter()


@router.get("/providers", response_model=list[ProviderInfo])
def list_providers(adapter: JackettAdapter = Depends(get_adapter)):
    configured = {p.get("slug") for p in adapter.list_configured()}
    providers = []
    for p in adapter.list_available():
        providers.append(
            ProviderInfo(
                slug=p.get("slug"),
                name=p.get("name", p.get("slug")),
                type=p.get("type", "public"),
                configured=p.get("slug") in configured,
                needs=p.get("needs", []),
            )
        )
    return providers


@router.post("/providers/{slug}/connect")
def connect_provider(
    slug: str,
    body: ProviderConnectIn | None = None,
    db: Session = Depends(get_db),
    adapter: JackettAdapter = Depends(get_adapter),
):
    providers = {p.slug: p for p in list_providers(adapter)}
    prov = providers.get(slug)
    if not prov:
        raise HTTPException(404, {"error": "provider_not_found"})

    body_dict = body.model_dump(exclude_none=True) if body else {}
    missing = [f for f in prov.needs if f not in body_dict]
    if missing:
        raise HTTPException(400, {"error": "missing_credentials", "needs": prov.needs})

    try:
        adapter.ensure_installed(slug, body_dict)
    except ValueError:
        raise HTTPException(404, {"error": "provider_not_found"})

    torznab_url = adapter.get_torznab_url(slug)
    caps = adapter.fetch_caps(torznab_url)
    tr = models.Tracker(
        provider_slug=slug,
        display_name=prov.name,
        type=prov.type,
        enabled=True,
        torznab_url=torznab_url,
        jackett_indexer_id=None,
        requires_auth=len(prov.needs) > 0,
    )
    db.add(tr)
    db.commit()
    db.refresh(tr)
    tracker_out = TrackerOut(
        id=tr.id,
        slug=tr.provider_slug,
        name=tr.display_name,
        enabled=tr.enabled,
        torznab_url=tr.torznab_url,
        requires_auth=tr.requires_auth,
        caps=caps,
    )
    return {"ok": True, "tracker": tracker_out.model_dump()}


@router.get("", response_model=list[TrackerOut])
def list_trackers(db: Session = Depends(get_db)):
    trs = db.query(models.Tracker).order_by(models.Tracker.id.asc()).all()
    return [
        TrackerOut(
            id=t.id,
            slug=t.provider_slug,
            name=t.display_name,
            enabled=t.enabled,
            torznab_url=t.torznab_url,
            requires_auth=t.requires_auth,
        )
        for t in trs
    ]


@router.post("/{tracker_id}/toggle")
def toggle_tracker(
    tracker_id: int,
    db: Session = Depends(get_db),
    adapter: JackettAdapter = Depends(get_adapter),
):
    tr = db.get(models.Tracker, tracker_id)
    if not tr:
        raise HTTPException(404, "Not found")
    tr.enabled = not tr.enabled
    db.commit()
    db.refresh(tr)
    try:
        adapter.enable(tr.provider_slug, tr.enabled)
    except Exception:
        pass
    return {"enabled": tr.enabled}


@router.post("/{tracker_id}/test")
def test_tracker(
    tracker_id: int,
    db: Session = Depends(get_db),
    adapter: JackettAdapter = Depends(get_adapter),
) -> dict[str, Any]:
    tr = db.get(models.Tracker, tracker_id)
    if not tr:
        raise HTTPException(404, "Not found")
    ok, latency = adapter.test_search(tr.torznab_url)
    return {"ok": ok, "latency_ms": latency}


@router.delete("/{tracker_id}")
def delete_tracker(
    tracker_id: int,
    db: Session = Depends(get_db),
    adapter: JackettAdapter = Depends(get_adapter),
):
    tr = db.get(models.Tracker, tracker_id)
    if not tr:
        raise HTTPException(404, "Not found")
    try:
        adapter.remove(tr.provider_slug)
    except Exception:
        pass
    db.delete(tr)
    db.commit()
    return {"ok": True}
