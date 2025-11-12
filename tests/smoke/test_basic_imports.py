"""Basic import smoke tests."""

from __future__ import annotations


def test_fastapi_import():
    """Test that FastAPI can be imported."""
    import fastapi
    assert fastapi is not None


def test_pydantic_import():
    """Test that Pydantic can be imported."""
    import pydantic
    assert pydantic is not None


def test_sqlalchemy_import():
    """Test that SQLAlchemy can be imported."""
    import sqlalchemy
    assert sqlalchemy is not None


def test_pytest_import():
    """Test that pytest can be imported."""
    import pytest
    assert pytest is not None