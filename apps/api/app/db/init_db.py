# app/db/init_db.py

from app.core.config import settings
from app.db.session import SessionLocal, Base, engine  # noqa: F401
# Keep Base/engine for rare dev scripts
from app.db import models


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

    from passlib.context import CryptContext

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    with SessionLocal() as db:
        # ---- Seed admin user (idempotent by email) ----
        dev_email = "dev@example.com"
        user = db.query(models.User).filter(models.User.email == dev_email).one_or_none()
        if user is None:
            user = models.User(
                email=dev_email,
                hashed_password=pwd.hash("dev"),
                role="admin",
            )
            db.add(user)

        # ---- Seed example tracker (idempotent by name+type) ----
        tracker_name = "Example"
        tracker_type = "torznab"
        tracker = (
            db.query(models.Tracker)
            .filter(
                models.Tracker.name == tracker_name,
                models.Tracker.type == tracker_type,
            )
            .one_or_none()
        )
        if tracker is None:
            tracker = models.Tracker(
                name=tracker_name,
                type=tracker_type,
                base_url="https://example.com",
                creds_enc="",
                enabled=False,
            )
            db.add(tracker)

        db.commit()

