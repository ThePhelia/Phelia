from __future__ import annotations

import json
import logging
import redis

from app.core.config import settings
from app.db.models import Download

logger = logging.getLogger(__name__)


CHANNEL_PREFIX = "downloads:"


def broadcast_download(dl: Download) -> None:
    """Publish download updates via Redis Pub/Sub.

    Errors are logged but otherwise ignored so that download processing
    continues even if the broadcaster is unavailable.
    """
    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        payload = {
            "id": dl.id,
            "name": dl.name,
            "magnet": dl.magnet,
            "hash": dl.hash,
            "progress": dl.progress,
            "dlspeed": dl.dlspeed,
            "upspeed": dl.upspeed,
            "status": dl.status,
            "eta": dl.eta,
            "save_path": dl.save_path,
        }
        r.publish(f"{CHANNEL_PREFIX}{dl.id}", json.dumps(payload))
    except Exception:
        logger.exception("Failed to broadcast download update")
