from typing import Any
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import models
from app.schemas.trackers import TrackerCreate, TrackerOut, TrackerUpdate
import json
import httpx
import base64
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from app.services.search.jackett_bootstrap import (
    read_jackett_apikey,
    JACKETT_BASE,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trackers", tags=["trackers"])


def _enc(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def _dec(text: str) -> str:
    return base64.b64decode(text.encode()).decode()


@router.get("/jackett/default")
def jackett_default() -> dict[str, str]:
    """Return the API key and base URL for the bundled Jackett service, if present."""
    key = read_jackett_apikey()
    if not key:
        raise HTTPException(404, "jackett apikey not found")
    return {"api_key": key, "base_url": JACKETT_BASE}


@router.get("/jackett/indexers")
async def jackett_indexers() -> list[dict[str, str]]:
    """Return the catalog of Jackett indexers available for configuration."""
    key = read_jackett_apikey()
    if not key:
        raise HTTPException(404, "jackett apikey not found")
    base = JACKETT_BASE.rsplit("/all/results/torznab/", 1)[0]
    url = f"{base}?configured=false&apikey={key}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
        r.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("jackett indexers url=%s error=%s", url, e)
        raise HTTPException(502, str(e))
    data = r.json()
    return [
        {
            "id": it.get("id"),
            "name": it.get("name"),
            "description": it.get("description"),
        }
        for it in data
    ]

@router.get("", response_model=list[TrackerOut])
def list_trackers(db: Session = Depends(get_db)):
    return db.query(models.Tracker).order_by(models.Tracker.id.asc()).all()

@router.post("", response_model=TrackerOut, status_code=201)
def create_tracker(body: TrackerCreate, db: Session = Depends(get_db)):
    if db.query(models.Tracker).filter(models.Tracker.name == body.name).first():
        raise HTTPException(400, "Tracker with this name already exists")

    # If a Jackett indexer is specified, create it via Jackett's API first
    if body.jackett_id:
        jackett_key = read_jackett_apikey()
        if not jackett_key:
            raise HTTPException(500, "jackett apikey not found")
        jackett_root = JACKETT_BASE.split("/api/")[0]
        jackett_url = f"{jackett_root}/api/v2.0/indexers/{body.jackett_id}"
        payload: dict[str, Any] = {"name": body.name}
        cfg: dict[str, str] = {}
        if body.api_key:
            cfg["api_key"] = body.api_key
        if body.username:
            cfg["username"] = body.username
        if body.password:
            cfg["password"] = body.password
        if cfg:
            payload["config"] = cfg
        try:
            r = httpx.post(
                jackett_url,
                params={"apikey": jackett_key},
                json=payload,
                timeout=10,
            )
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            msg = e.response.text if e.response is not None else str(e)
            logger.error("create_tracker jackett status error id=%s body=%s", body.jackett_id, msg)
            raise HTTPException(e.response.status_code if e.response else 400, msg)
        except httpx.HTTPError as e:
            logger.error("create_tracker jackett error id=%s error=%s", body.jackett_id, e)
            raise HTTPException(400, str(e))
        data = r.json()
        slug = data.get("id") or data.get("slug") or body.jackett_id
        api_key = data.get("apiKey") or data.get("api_key") or jackett_key
        base_url = data.get("baseUrl") or data.get("base_url")
        if not base_url:
            base_url = f"{jackett_root}/api/v2.0/indexers/{slug}/results/torznab/"
        creds_enc = json.dumps({"api_key": api_key} if api_key else {})
        tr = models.Tracker(
            name=body.name,
            type="torznab",
            base_url=base_url,
            creds_enc=creds_enc,
            username=None,
            password_enc=None,
            enabled=body.enabled,
        )
        db.add(tr)
        db.commit()
        db.refresh(tr)
        return tr

    if not body.base_url:
        raise HTTPException(400, "base_url or jackett_id required")

    raw_base = str(body.base_url)
    split = urlsplit(raw_base)
    path = split.path.rstrip("/")
    qs = parse_qsl(split.query, keep_blank_values=True)
    filtered = [(k, v) for k, v in qs if k.lower() != "apikey"]
    if len(filtered) != len(qs):
        logger.warning("create_tracker stripping apikey from base_url")
    base_url = urlunsplit((split.scheme, split.netloc, path, urlencode(filtered), split.fragment))
    creds_enc = json.dumps({"api_key": body.api_key} if body.api_key else {})
    tr = models.Tracker(
        name=body.name,
        type="torznab",
        base_url=base_url,
        creds_enc=creds_enc,
        username=body.username,
        password_enc=_enc(body.password) if body.password else None,
        enabled=body.enabled,
    )
    db.add(tr)
    db.commit()
    db.refresh(tr)
    if body.api_key:
        test_url = base_url + ("&" if "?" in base_url else "?") + f"t=caps&apikey={body.api_key}"
        try:
            r = httpx.get(test_url, timeout=10)
            logger.info("create_tracker test url=%s status=%s body=%s", test_url, r.status_code, r.text)
        except httpx.HTTPError as e:
            logger.error("create_tracker test url=%s error=%s", test_url, e)
    elif body.username and body.password:
        test_url = base_url + ("&" if "?" in base_url else "?") + "t=caps"
        try:
            r = httpx.get(test_url, timeout=10, auth=(body.username, body.password))
            logger.info("create_tracker test url=%s status=%s body=%s", test_url, r.status_code, r.text)
        except httpx.HTTPError as e:
            logger.error("create_tracker test url=%s error=%s", test_url, e)
    return tr

@router.patch("/{tracker_id}", response_model=TrackerOut)
def update_tracker(tracker_id: int, body: TrackerUpdate, db: Session = Depends(get_db)):
    tr = db.get(models.Tracker, tracker_id)
    if not tr:
        raise HTTPException(404, "Not found")
    if body.name is not None:
        tr.name = body.name
    if body.base_url is not None:
        tr.base_url = str(body.base_url).rstrip("/")
    if body.enabled is not None:
        tr.enabled = body.enabled
    if body.api_key is not None:
        data = json.loads(tr.creds_enc or "{}")
        data["api_key"] = body.api_key
        tr.creds_enc = json.dumps(data)
    if body.username is not None:
        tr.username = body.username
    if body.password is not None:
        tr.password_enc = _enc(body.password)
    db.commit(); db.refresh(tr)
    return tr

@router.delete("/{tracker_id}", status_code=204)
def delete_tracker(tracker_id: int, db: Session = Depends(get_db)):
    tr = db.get(models.Tracker, tracker_id)
    if not tr:
        raise HTTPException(404, "Not found")
    db.delete(tr); db.commit()
    return

@router.post("/{tracker_id}/test")
async def test_tracker(tracker_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    tr = db.get(models.Tracker, tracker_id)
    if not tr:
        raise HTTPException(404, "Not found")
    data = json.loads(tr.creds_enc or "{}")
    api_key = data.get("api_key")
    username = tr.username
    password = _dec(tr.password_enc) if tr.password_enc else None
    if api_key:
        url = tr.base_url + ("&" if "?" in tr.base_url else "?") + f"t=caps&apikey={api_key}"
        auth = None
    elif username and password:
        url = tr.base_url + ("&" if "?" in tr.base_url else "?") + "t=caps"
        auth = (username, password)
    else:
        raise HTTPException(400, "api_key or username/password missing")
    logger.info("test_tracker url=%s", url)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, auth=auth)
        logger.info("test_tracker status=%s body=%s", r.status_code, r.text)
    except httpx.HTTPError as e:
        logger.error("test_tracker error url=%s error=%s", url, e)
        raise HTTPException(400, str(e))
    ok = r.status_code == 200 and b"<caps" in r.content
    return {"ok": ok, "status": r.status_code}

