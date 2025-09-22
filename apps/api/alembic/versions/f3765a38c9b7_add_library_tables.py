"""add library tables

Revision ID: f3765a38c9b7
Revises: f35b2f12e9dc
Create Date: 2025-01-16 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "f3765a38c9b7"
down_revision = "f35b2f12e9dc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "library_playlists",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_library_playlists_slug", "library_playlists", ["slug"], unique=True)

    op.create_table(
        "library_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("list_type", sa.String(length=32), nullable=False),
        sa.Column("item_kind", sa.String(length=16), nullable=False),
        sa.Column("item_id", sa.String(length=256), nullable=False),
        sa.Column("playlist_slug", sa.String(length=64), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "list_type",
            "item_kind",
            "item_id",
            "playlist_slug",
            name="uq_library_entry",
        ),
    )
    op.create_index("ix_library_entries_list_type", "library_entries", ["list_type"])
    op.create_index("ix_library_entries_item_kind", "library_entries", ["item_kind"])
    op.create_index("ix_library_entries_item_id", "library_entries", ["item_id"])
    op.create_index("ix_library_entries_playlist_slug", "library_entries", ["playlist_slug"])


def downgrade() -> None:
    op.drop_index("ix_library_entries_playlist_slug", table_name="library_entries")
    op.drop_index("ix_library_entries_item_id", table_name="library_entries")
    op.drop_index("ix_library_entries_item_kind", table_name="library_entries")
    op.drop_index("ix_library_entries_list_type", table_name="library_entries")
    op.drop_table("library_entries")

    op.drop_index("ix_library_playlists_slug", table_name="library_playlists")
    op.drop_table("library_playlists")
