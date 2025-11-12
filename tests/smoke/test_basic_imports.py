"""Basic smoke tests."""

from __future__ import annotations


def test_basic_python():
    """Test that basic Python functionality works."""
    assert 1 + 1 == 2


def test_basic_import():
    """Test that basic imports work."""
    import sys
    import os
    assert sys is not None
    assert os is not None