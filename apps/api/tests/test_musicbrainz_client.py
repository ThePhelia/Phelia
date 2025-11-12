from __future__ import annotations

import pytest

from app.services.metadata.metadata_client import MetadataProxyError
from app.services.metadata.providers.musicbrainz import MusicBrainzClient


class DummyMetadataClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict[str, str] | None, str | None]] = []

    async def mb(
        self,
        path: str,
        params: dict[str, str] | None = None,
        *,
        request_id: str | None = None,
    ) -> dict[str, object]:
        self.calls.append((path, params, request_id))
        return self.payload


class ErrorMetadataClient:
    async def mb(self, path: str, params=None, *, request_id=None):  # type: ignore[override]
        raise MetadataProxyError(503, {"error": "upstream"})


@pytest.mark.anyio
async def test_musicbrainz_client_uses_metadata_proxy() -> None:
    payload = {
        "release-groups": [
            {
                "id": "rg-1",
                "title": "In Rainbows",
                "first-release-date": "2007-10-10",
                "primary-type": "Album",
                "artist-credit": [
                    {
                        "artist": {"id": "artist-1", "name": "Radiohead"},
                    }
                ],
            }
        ],
        "provider": "musicbrainz",
    }
    metadata_client = DummyMetadataClient(payload)
    client = MusicBrainzClient(
        user_agent="TestAgent/1.0", metadata_client=metadata_client
    )

    result = await client.lookup_release_group(artist="Radiohead", album="In Rainbows")

    assert metadata_client.calls
    path, params, request_id = metadata_client.calls[0]
    assert path == "release-group"
    assert params is not None and params["fmt"] == "json"
    assert request_id is None
    assert result is not None
    assert result["release_group"]["id"] == "rg-1"
    assert result["artist"]["name"] == "Radiohead"


@pytest.mark.anyio
async def test_musicbrainz_client_handles_proxy_error() -> None:
    client = MusicBrainzClient(
        user_agent="TestAgent/1.0",
        metadata_client=ErrorMetadataClient(),  # type: ignore[arg-type]
    )

    result = await client.lookup_release_group(artist="Radiohead", album="In Rainbows")
    assert result is None
