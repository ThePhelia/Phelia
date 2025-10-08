"""Initial database schema."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision = "f35b2f12e9dc"  # pragma: allowlist secret
down_revision = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'user'"),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "downloads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("hash", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("magnet", sa.Text(), nullable=False),
        sa.Column("save_path", sa.String(length=1024), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'queued'"),
        ),
        sa.Column(
            "progress",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "dlspeed",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "upspeed",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("eta", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_downloads_hash", "downloads", ["hash"], unique=False)

    op.create_table(
        "trackers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider_slug", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("torznab_url", sa.String(length=255), nullable=False),
        sa.Column(
            "requires_auth",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("provider_slug", name="uq_trackers_provider_slug"),
    )
    op.create_index(
        "ix_trackers_provider_slug", "trackers", ["provider_slug"], unique=False
    )

    op.create_table(
        "library_playlists",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_library_playlists_slug",
        "library_playlists",
        ["slug"],
        unique=True,
    )

    op.create_table(
        "library_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("list_type", sa.String(length=32), nullable=False),
        sa.Column("item_kind", sa.String(length=16), nullable=False),
        sa.Column("item_id", sa.String(length=256), nullable=False),
        sa.Column("playlist_slug", sa.String(length=64), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "list_type",
            "item_kind",
            "item_id",
            "playlist_slug",
            name="uq_library_entry",
        ),
    )
    op.create_index(
        "ix_library_entries_list_type", "library_entries", ["list_type"], unique=False
    )
    op.create_index(
        "ix_library_entries_item_kind", "library_entries", ["item_kind"], unique=False
    )
    op.create_index(
        "ix_library_entries_item_id", "library_entries", ["item_id"], unique=False
    )
    op.create_index(
        "ix_library_entries_playlist_slug",
        "library_entries",
        ["playlist_slug"],
        unique=False,
    )

    op.create_table(
        "provider_credentials",
        sa.Column(
            "provider_slug",
            sa.String(length=64),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("api_key", sa.String(length=512), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("provider_credentials")

    op.drop_index(
        "ix_library_entries_playlist_slug",
        table_name="library_entries",
    )
    op.drop_index("ix_library_entries_item_id", table_name="library_entries")
    op.drop_index("ix_library_entries_item_kind", table_name="library_entries")
    op.drop_index("ix_library_entries_list_type", table_name="library_entries")
    op.drop_table("library_entries")

    op.drop_index("ix_library_playlists_slug", table_name="library_playlists")
    op.drop_table("library_playlists")

    op.drop_index("ix_trackers_provider_slug", table_name="trackers")
    op.drop_table("trackers")

    op.drop_index("ix_downloads_hash", table_name="downloads")
    op.drop_table("downloads")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
