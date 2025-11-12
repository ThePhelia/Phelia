import pytest

from ._testenv import Base, SessionLocal, engine, runtime_settings


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
