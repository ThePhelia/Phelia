"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("", tags=["health"])
@router.get("/", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
