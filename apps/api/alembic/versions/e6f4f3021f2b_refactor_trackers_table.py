"""refactor trackers table to provider-based fields

Revision ID: e6f4f3021f2b
Revises: cdd7a497d5f9
Create Date: 2024-06-01

"""
from alembic import op
import sqlalchemy as sa


revision = "e6f4f3021f2b"
down_revision = "cdd7a497d5f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()
    if "trackers" not in table_names:
        return

    tracker_columns = {column["name"] for column in inspector.get_columns("trackers")}
    if "provider_slug" in tracker_columns:
        constraints = inspector.get_unique_constraints("trackers")
        has_provider_slug_constraint = any(
            "provider_slug" in constraint.get("column_names", [])
            for constraint in constraints
        )
        if not has_provider_slug_constraint:
            with op.batch_alter_table("trackers") as batch_op:
                batch_op.create_unique_constraint(
                    "uq_trackers_provider_slug", ["provider_slug"]
                )

        tracker_indexes = inspector.get_indexes("trackers")
        has_provider_slug_index = any(
            index.get("name") == "ix_trackers_provider_slug"
            or "provider_slug" in index.get("column_names", [])
            for index in tracker_indexes
        )
        if not has_provider_slug_index:
            op.create_index(
                "ix_trackers_provider_slug", "trackers", ["provider_slug"]
            )

        return

    if "trackers_new" in table_names:
        op.drop_table("trackers_new")
        inspector = sa.inspect(bind)

    op.create_table(
        "trackers_new",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider_slug", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("torznab_url", sa.String(length=255), nullable=True),
        sa.Column("jackett_indexer_id", sa.String(length=64), nullable=True),
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

    op.execute(
        """
        INSERT INTO trackers_new (
            id,
            provider_slug,
            display_name,
            type,
            enabled,
            torznab_url,
            jackett_indexer_id,
            requires_auth,
            created_at,
            updated_at
        )
        SELECT
            id,
            name,
            name,
            type,
            enabled,
            base_url,
            NULL,
            CASE
                WHEN COALESCE(username, password_enc, creds_enc) IS NOT NULL
                THEN 1
                ELSE 0
            END,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM trackers
        """
    )

    op.drop_table("trackers")
    op.rename_table("trackers_new", "trackers")
    op.create_index("ix_trackers_provider_slug", "trackers", ["provider_slug"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "trackers" not in inspector.get_table_names():
        return

    op.drop_index("ix_trackers_provider_slug", table_name="trackers")

    op.create_table(
        "trackers_old",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("base_url", sa.String(length=255), nullable=True),
        sa.Column("creds_enc", sa.String(length=512), nullable=True),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("username", sa.String(length=128), nullable=True),
        sa.Column("password_enc", sa.String(length=512), nullable=True),
        sa.UniqueConstraint("name", name="uq_trackers_name"),
    )

    op.execute(
        """
        INSERT INTO trackers_old (
            id,
            name,
            type,
            base_url,
            creds_enc,
            enabled,
            username,
            password_enc
        )
        SELECT
            id,
            provider_slug,
            type,
            torznab_url,
            NULL,
            enabled,
            NULL,
            NULL
        FROM trackers
        """
    )

    op.drop_table("trackers")
    op.rename_table("trackers_old", "trackers")
