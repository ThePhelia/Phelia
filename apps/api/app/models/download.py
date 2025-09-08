from sqlalchemy import Column, Integer, String, Float, Text
from app.db.session import Base

class Download(Base):
    __tablename__ = "downloads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=True)
    magnet = Column(Text, nullable=False)
    save_path = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="queued")
    progress = Column(Float, nullable=False, default=0.0)
    dlspeed = Column(Integer, nullable=False, default=0)
    upspeed = Column(Integer, nullable=False, default=0)
    eta = Column(Integer, nullable=True, default=0)

