"""Shared pytest configuration for top-level tests."""

from __future__ import annotations

from . import _testenv as _testenv_module

ENV_BOOTSTRAP = _testenv_module

__all__ = ["ENV_BOOTSTRAP"]
