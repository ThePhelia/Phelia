from app.db.session import Base, engine, SessionLocal
from app.db import models
from app.core.config import settings


def init_db() -> None:
    """Create tables and seed initial data."""
    Base.metadata.create_all(bind=engine)

    if settings.APP_ENV == "dev":
        from passlib.context import CryptContext

        with SessionLocal() as db:
            if not db.query(models.User).first():
                pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
                dev_user = models.User(
                    email="dev@example.com",
                    hashed_password=pwd.hash("dev"),
                    role="admin",
                )
                db.add(dev_user)
            if not db.query(models.Tracker).first():
                sample = [
                    models.Tracker(
                        name="Example",
                        type="torznab",
                        base_url="https://example.com",
                        creds_enc="",
                        enabled=False,
                    )
                ]
                db.add_all(sample)
            db.commit()
