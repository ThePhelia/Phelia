from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, HttpUrl, Field


class ProviderInfo(BaseModel):
    slug: str
    name: str
    type: Literal["public", "private"]
    configured: bool = False
    needs: list[str] = []


class ProviderConnectIn(BaseModel):
    username: Optional[str] = Field(default=None, min_length=1, max_length=128)
    password: Optional[str] = Field(default=None, min_length=1, max_length=256)
    cookies: Optional[str] = None


class TrackerOut(BaseModel):
    id: int
    slug: str
    name: str
    enabled: bool
    torznab_url: HttpUrl
    requires_auth: bool
    caps: dict | None = None

    class Config:
        from_attributes = True
