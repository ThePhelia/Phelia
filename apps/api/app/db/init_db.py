# app/db/init_db.py

import os
import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal, Base, engine  # noqa: F401
# Keep Base/engine for rare dev scripts
from app.db import models

logger = logging.getLogger(__name__)


def init_db() -> None:
    """
    Dev-only seed. Do NOT create tables here — schema is managed by Alembic.
    In production this function is a no-op.
    """
    if settings.APP_ENV != "dev":
        return

    # In dev you can uncomment the next 2 lines to create the schema without Alembic.
    # Do NOT do this in production.
    # from sqlalchemy import inspect
    # if not inspect(engine).has_table("users"): Base.metadata.create_all(bind=engine)

    admin_email = os.getenv("ADMIN_EMAIL", "dev@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "dev")

    with SessionLocal() as db:
        # ---- Seed admin user (idempotent by email) ----
        stmt = insert(models.User).values(
            email=admin_email,
            hashed_password=hash_password(admin_password),
            role="admin",
        )
        # Ensure duplicate emails do not raise while keeping existing constraint naming intact.
        stmt = stmt.on_conflict_do_nothing(index_elements=[models.User.email])
        db.execute(stmt)

        # ---- Seed example tracker (idempotent by slug) ----
        tracker_slug = "example"
        tracker = (
            db.query(models.Tracker)
            .filter(models.Tracker.provider_slug == tracker_slug)
            .one_or_none()
        )
        if tracker is None:
            tracker = models.Tracker(
                provider_slug=tracker_slug,
                display_name="Example",
                type="public",
                enabled=False,
                torznab_url="https://example.com",
                requires_auth=False,
            )
            db.add(tracker)
        try:
            db.commit()
        except IntegrityError:
            # A concurrent seed may win the race; rollback so the session stays usable.
            db.rollback()
            logger.warning("Database seed skipped due to existing records")

