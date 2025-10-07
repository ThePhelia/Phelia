import os

import pytest

os.environ.setdefault("TMDB_API_KEY", "test-key")


@pytest.fixture
def anyio_backend():
    return "asyncio"
