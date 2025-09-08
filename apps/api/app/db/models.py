from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean
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

    magnet = Column(Text, nullable=True)
    save_path = Column(String(1024), nullable=True)

    status = Column(String(32), nullable=True)
    progress = Column(Float, nullable=True)
    dlspeed = Column(Integer, nullable=True)
    upspeed = Column(Integer, nullable=True)
    eta = Column(Integer, nullable=True)


class Tracker(Base):
    __tablename__ = "trackers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(16))
    base_url: Mapped[str | None] = mapped_column(String(255))
    creds_enc: Mapped[str | None] = mapped_column(String(512))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
