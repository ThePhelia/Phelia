# Metadata Search Flow

The metadata search API decouples the global search bar from direct Jackett queries.
Instead, the browser requests metadata, displays a rich preview, and only starts a
Jackett query when the user explicitly clicks **Find Torrents**.

## Endpoints

- `GET /api/v1/meta/search`
  - Queries TMDb (movies + TV) and Discogs/Last.fm (albums) in parallel.
  - Returns a flat list of `MetaSearchItem` objects with type badges and provider metadata.

- `GET /api/v1/meta/detail`
  - Expands a chosen item into a `MetaDetail` record including posters, synopsis,
    runtime/episode counts, cast, and album track lists.
  - Populates a canonical payload used for torrent search. Rules:
    - Movies: `"{title} {year}"`
    - TV: `"{title} S{season:02}E{episode:02}"` (season/episode optional)
    - Albums: `"{artist} - {album} {year}"`

- `POST /api/v1/index/start`
  - Validates the canonical payload, builds the Jackett query string, and runs a
    lightweight Jackett search. A background Celery task is enqueued when available.

## Canonical Helpers

`app/services/meta/canonical.py` contains helper functions for producing canonical
queries for each media type. These are reused by the API and unit tested in
`apps/api/tests/test_canonical_builder.py`.

## Jackett Integration

`JackettAdapter.search` exposes a minimal async search that maps the Torznab
response into `JackettSearchItem` objects. Category hints default to:

- Movies: `2000, 5000`
- TV: `5000`
- Music: `3000`

The values can be overridden with `JACKETT_MOVIE_CATS`, `JACKETT_TV_CATS`, and
`JACKETT_MUSIC_CATS` environment variables (comma-separated integers).
