"""Core Jackett-backed torrent search integration."""

from .provider import JackettProvider
from .settings import JackettSettings

__all__ = ["JackettProvider", "JackettSettings"]
