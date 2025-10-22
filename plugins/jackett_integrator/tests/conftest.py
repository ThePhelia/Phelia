import os
import sys
from pathlib import Path

import pytest


PLUGIN_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PLUGIN_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate docker integration during tests."""

    monkeypatch.setenv("PHELIA_PLUGIN_SKIP_DOCKER", "1")
