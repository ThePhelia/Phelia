import os
import sys
import pytest

# Ensure environment variables for Settings before importing the app
os.environ.setdefault("APP_SECRET", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("QB_URL", "http://localhost:8080")
os.environ.setdefault("QB_USER", "admin")
os.environ.setdefault("QB_PASS", "adminadmin")
os.environ.setdefault("ANYIO_BACKEND", "asyncio")
os.environ.setdefault("METADATA_BASE_URL", "http://metadata-proxy:8080")

# Add apps/api to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.runtime_settings import runtime_settings
from app.db.session import SessionLocal, Base, engine

@pytest.fixture(autouse=True)
def setup_db():
    """Create a clean database for each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def reset_runtime_settings_state():
    runtime_settings.reset_to_env()
    yield
    runtime_settings.reset_to_env()

@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def anyio_backend():
    return "asyncio"
