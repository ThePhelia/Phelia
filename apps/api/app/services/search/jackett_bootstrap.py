from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
import logging

from app.db.session import SessionLocal
from app.db import models

JACKETT_CONFIG = Path("/jackett_config/Jackett/ServerConfig.json")
JACKETT_BASE   = "http://jackett:9117/api/v2.0/indexers/all/results/torznab/"

logger = logging.getLogger(__name__)

def read_jackett_apikey() -> Optional[str]:
    try:
        data = json.loads(JACKETT_CONFIG.read_text(encoding="utf-8"))
        key = data.get("APIKey")
        return key or None
    except FileNotFoundError:
        return None
    except Exception:
        return None

def ensure_jackett_tracker(name: str = "jackett-all") -> bool:
    """Create or update the Jackett tracker in the DB. Return True if a valid key is present."""
    api_key = read_jackett_apikey()
    if not api_key:
        return False
    with SessionLocal() as db:
        qs = (
            db.query(models.Tracker)
              .filter(models.Tracker.name == name)
              .order_by(models.Tracker.id)
        )
        tr = qs.first()
        extras = qs.offset(1).all()
        if extras:
            for extra in extras:
                db.delete(extra)
            logger.warning("Removed %d duplicate tracker rows for %s", len(extras), name)

        creds_enc = json.dumps({"api_key": api_key})
        if tr:
            tr.type = "torznab"
            tr.base_url = JACKETT_BASE
            tr.creds_enc = creds_enc
            tr.username = None
            tr.password_enc = None
            tr.enabled = True
        else:
            tr = models.Tracker(
                name=name,
                type="torznab",
                base_url=JACKETT_BASE,
                creds_enc=creds_enc,
                username=None,
                password_enc=None,
                enabled=True,
            )
            db.add(tr)
        db.commit()
    return True

