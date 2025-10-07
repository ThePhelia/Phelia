"""Pydantic schemas exposed by the proxy."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProxyPayload(BaseModel):
    provider: str = Field(..., description="Upstream provider name")
    cached: bool = Field(False, description="Whether the response originated from cache")
    fetched_at: datetime = Field(..., description="Timestamp the payload was fetched")
    data: Any = Field(..., description="Raw upstream JSON payload")


class ErrorResponse(BaseModel):
    error: str
    status: int
    upstream_status: int | None = None
    request_id: str | None = None
