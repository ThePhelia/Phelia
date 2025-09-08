from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.session import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="user")


class Download(Base):
    __tablename__ = "downloads"

    id = Column(Integer, primary_key=True, index=True)
    hash = Column(String(64), nullable=True, index=True)
    name = Column(String(512), nullable=True)

    magnet = Column(Text, nullable=False)
    save_path = Column(String(1024), nullable=False)

    status = Column(String(32), nullable=False, default="queued")
    progress = Column(Float, nullable=False, default=0.0)
    dlspeed = Column(Integer, nullable=False, default=0)
    upspeed = Column(Integer, nullable=False, default=0)
    eta = Column(Integer, nullable=True, default=0)


class Tracker(Base):
    __tablename__ = "trackers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(16))
    base_url: Mapped[str | None] = mapped_column(String(255))
    creds_enc: Mapped[str | None] = mapped_column(String(512))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
