# Metadata Search Flow

Phelia's metadata search pipeline decouples the global search bar from any
specific torrent provider. The browser requests metadata, renders a rich
preview, and only triggers a torrent lookup when the user explicitly clicks
**Find Torrents**. When no torrent providers are installed the API still
responds with helpful messaging so the UI can degrade gracefully.

## Endpoints

- `GET /api/v1/meta/search`
  - Queries TMDb (movies + TV) and Discogs/Last.fm (albums) in parallel.
  - Returns a flat list of `MetaSearchItem` objects with type badges and
    provider metadata.

- `GET /api/v1/meta/detail`
  - Expands a chosen item into a `MetaDetail` record including posters,
    synopsis, runtime/episode counts, cast, and album track lists.
  - Populates a canonical payload used for torrent search. Rules:
    - Movies: `"{title} {year}"`
    - TV: `"{title} S{season:02}E{episode:02}"` (season/episode optional)
    - Albums: `"{artist} - {album} {year}"`

- `GET /api/v1/search`
  - Aggregates torrent results from the configured provider registry.
  - Always returns a payload compatible with the UI; when no providers are
    available the response carries a descriptive `message` and an empty
    `items` list.

## Canonical Helpers

`app/services/meta/canonical.py` contains helper functions for producing
canonical queries for each media type. These are reused by the API and unit
tested in `apps/api/tests/test_canonical_builder.py`.
