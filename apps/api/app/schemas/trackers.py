from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Literal

TrackerType = Literal["torznab"]

class TrackerBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    type: TrackerType = "torznab"
    base_url: HttpUrl
    enabled: bool = True

class TrackerCreate(TrackerBase):
    api_key: Optional[str] = None

class TrackerUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[HttpUrl] = None
    enabled: Optional[bool] = None
    api_key: Optional[str] = None

class TrackerOut(TrackerBase):
    id: int
    class Config:
        from_attributes = True

