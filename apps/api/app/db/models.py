from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, Text, Boolean
from datetime import datetime
from app.db.session import Base, engine, SessionLocal
from app.core.config import settings

class Download(Base):
    __tablename__ = "downloads"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client: Mapped[str] = mapped_column(String(8), default="qb")
    client_torrent_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    save_path: Mapped[str] = mapped_column(Text, default="/downloads")
    rate_down: Mapped[int] = mapped_column(Integer, default=0)
    rate_up: Mapped[int] = mapped_column(Integer, default=0)
    eta_sec: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class Tracker(Base):
    __tablename__ = "trackers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(16))
    base_url: Mapped[str | None] = mapped_column(String(255))
    creds_enc: Mapped[str | None] = mapped_column(String(512))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

# bootstrap (MVP): создаём таблицы при старте
Base.metadata.create_all(bind=engine)


if settings.APP_ENV == "dev":
    with SessionLocal() as db:
        if not db.query(Tracker).first():
            sample = [
                Tracker(
                    name="Example",
                    type="torznab",
                    base_url="https://example.com",
                    creds_enc="",
                    enabled=False,
                )
            ]
            db.add_all(sample)
            db.commit()
