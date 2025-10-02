"""Expose the running Phelia backend version."""

from __future__ import annotations

import os


DEFAULT_VERSION = "0.7.0"


def get_version() -> str:
    """Return the declared backend version for compatibility checks."""

    return os.getenv("PHELIA_VERSION", DEFAULT_VERSION)

