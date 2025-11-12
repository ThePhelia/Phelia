"""Library persistence helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy.orm import Session

from app.db import models
from app.schemas.ui import (
    DiscoverItem,
    LibraryPlaylist,
    LibrarySummary,
    ListMutationInput,
    ListMutationItem,
)


class LibraryError(RuntimeError):
    """Base error for library operations."""


class UnknownListError(LibraryError):
    """Raised when a mutation references an unknown list."""


class PlaylistRequiredError(LibraryError):
    """Raised when playlist mutations are missing an identifier."""


def _as_discover(item: ListMutationItem) -> DiscoverItem:
    payload = item.model_dump()
    payload.setdefault("title", item.id)
    payload.setdefault("kind", item.kind)
    payload.setdefault("id", item.id)
    return DiscoverItem.model_validate(payload)


def _entry_to_discover(entry: models.LibraryEntry) -> DiscoverItem:
    snapshot = entry.snapshot or {}
    snapshot.setdefault("id", entry.item_id)
    snapshot.setdefault("kind", entry.item_kind)
    snapshot.setdefault("title", snapshot.get("title") or entry.item_id)
    return DiscoverItem.model_validate(snapshot)


def _ensure_playlist(
    db: Session, slug: str, title: str | None = None
) -> models.LibraryPlaylist:
    playlist = (
        db.query(models.LibraryPlaylist)
        .filter(models.LibraryPlaylist.slug == slug)
        .one_or_none()
    )
    if playlist is None:
        playlist = models.LibraryPlaylist(slug=slug, title=title or slug)
        db.add(playlist)
        db.commit()
        db.refresh(playlist)
    elif title and playlist.title != title:
        playlist.title = title
        playlist.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(playlist)
    return playlist


def _upsert_entry(
    db: Session,
    *,
    list_type: str,
    item: DiscoverItem,
    playlist_slug: str | None = None,
) -> models.LibraryEntry:
    query = (
        db.query(models.LibraryEntry)
        .filter(models.LibraryEntry.list_type == list_type)
        .filter(models.LibraryEntry.item_kind == item.kind)
        .filter(models.LibraryEntry.item_id == item.id)
    )
    if playlist_slug:
        query = query.filter(models.LibraryEntry.playlist_slug == playlist_slug)
    else:
        query = query.filter(models.LibraryEntry.playlist_slug.is_(None))

    entry = query.one_or_none()
    snapshot = item.model_dump()
    if entry is None:
        entry = models.LibraryEntry(
            list_type=list_type,
            item_kind=item.kind,
            item_id=item.id,
            playlist_slug=playlist_slug,
            snapshot=snapshot,
        )
        db.add(entry)
    else:
        entry.snapshot = snapshot
        entry.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)
    return entry


def _delete_entry(
    db: Session,
    *,
    list_type: str,
    item: ListMutationItem,
    playlist_slug: str | None = None,
) -> bool:
    query = (
        db.query(models.LibraryEntry)
        .filter(models.LibraryEntry.list_type == list_type)
        .filter(models.LibraryEntry.item_kind == item.kind)
        .filter(models.LibraryEntry.item_id == item.id)
    )
    if playlist_slug:
        query = query.filter(models.LibraryEntry.playlist_slug == playlist_slug)
    else:
        query = query.filter(models.LibraryEntry.playlist_slug.is_(None))
    entry = query.one_or_none()
    if entry is None:
        return False
    db.delete(entry)
    db.commit()
    return True


def apply_mutation(db: Session, mutation: ListMutationInput) -> None:
    list_type = mutation.list
    playlist_slug = None
    if list_type == "playlist":
        if not mutation.playlist_id:
            raise PlaylistRequiredError("playlist id required")
        playlist_slug = mutation.playlist_id
        _ensure_playlist(db, playlist_slug, title=mutation.playlist_title)
        list_type = "playlist"
    elif list_type not in {"watchlist", "favorites"}:
        raise UnknownListError(list_type)

    item = _as_discover(mutation.item)

    if mutation.action == "add":
        _upsert_entry(db, list_type=list_type, item=item, playlist_slug=playlist_slug)
    elif mutation.action == "remove":
        _delete_entry(
            db, list_type=list_type, item=mutation.item, playlist_slug=playlist_slug
        )
    else:
        raise UnknownListError(mutation.action)


def _collect_entries(entries: Iterable[models.LibraryEntry]) -> list[DiscoverItem]:
    return [_entry_to_discover(entry) for entry in entries]


def build_summary(db: Session) -> LibrarySummary:
    watchlist_entries = (
        db.query(models.LibraryEntry)
        .filter(models.LibraryEntry.list_type == "watchlist")
        .filter(models.LibraryEntry.playlist_slug.is_(None))
        .order_by(models.LibraryEntry.created_at.desc())
        .all()
    )
    favorites_entries = (
        db.query(models.LibraryEntry)
        .filter(models.LibraryEntry.list_type == "favorites")
        .filter(models.LibraryEntry.playlist_slug.is_(None))
        .order_by(models.LibraryEntry.created_at.desc())
        .all()
    )

    playlists: list[LibraryPlaylist] = []
    for playlist in (
        db.query(models.LibraryPlaylist)
        .order_by(models.LibraryPlaylist.created_at.asc())
        .all()
    ):
        items = (
            db.query(models.LibraryEntry)
            .filter(models.LibraryEntry.list_type == "playlist")
            .filter(models.LibraryEntry.playlist_slug == playlist.slug)
            .order_by(models.LibraryEntry.created_at.desc())
            .all()
        )
        playlists.append(
            LibraryPlaylist(
                id=playlist.slug,
                title=playlist.title,
                items=_collect_entries(items),
            )
        )

    return LibrarySummary(
        watchlist=_collect_entries(watchlist_entries),
        favorites=_collect_entries(favorites_entries),
        playlists=playlists,
    )


def get_entry(db: Session, kind: str, item_id: str) -> models.LibraryEntry | None:
    return (
        db.query(models.LibraryEntry)
        .filter(models.LibraryEntry.item_kind == kind)
        .filter(models.LibraryEntry.item_id == item_id)
        .order_by(models.LibraryEntry.created_at.desc())
        .first()
    )
