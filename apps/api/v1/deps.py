import os
from fastapi import Depends
from app.services.jackett import JackettClient

def get_jackett() -> JackettClient:
    base = os.getenv("JACKETT_URL") or os.getenv("JACKETT_BASE") or "http://jackett:9117"
    key = os.getenv("JACKETT_API_KEY", "")
    return JackettClient(base, key)

