from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Optional

from app.db import models
from app.db.session import SessionLocal

JACKETT_CONFIG = Path("/jackett_config/Jackett/ServerConfig.json")
JACKETT_BASE = "http://jackett:9117/api/v2.0/indexers/all/results/torznab/"

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
    """Ensure a default aggregate tracker exists.

    The tracker simply points at Jackett's `/all` endpoint.  This helper is
    retained for backwards compatibility with older deployments.
    """

    api_key = read_jackett_apikey()
    if not api_key:
        return False
    with SessionLocal() as db:
        tr = (
            db.query(models.Tracker)
            .filter(models.Tracker.provider_slug == name)
            .first()
        )
        if tr:
            tr.torznab_url = JACKETT_BASE
        else:
            tr = models.Tracker(
                provider_slug=name,
                display_name=name,
                type="public",
                enabled=True,
                torznab_url=JACKETT_BASE,
                jackett_indexer_id=None,
                requires_auth=False,
            )
            db.add(tr)
        db.commit()
    return True

