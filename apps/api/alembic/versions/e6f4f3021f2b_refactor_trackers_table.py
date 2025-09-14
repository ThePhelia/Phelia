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
    if "trackers" not in inspector.get_table_names():
        return
    cols = [c["name"] for c in inspector.get_columns("trackers")]
    uqs = [c["name"] for c in inspector.get_unique_constraints("trackers")]
    idxs = [c["name"] for c in inspector.get_indexes("trackers")]
    with op.batch_alter_table("trackers") as batch_op:
        if "uq_trackers_name" in uqs:
            batch_op.drop_constraint("uq_trackers_name", type_="unique")
        if "name" in cols:
            batch_op.alter_column("name", new_column_name="provider_slug")
        if "base_url" in cols:
            batch_op.alter_column("base_url", new_column_name="torznab_url")
        for col in ("creds_enc", "username", "password_enc"):
            if col in cols:
                batch_op.drop_column(col)
        if "display_name" not in cols:
            batch_op.add_column(sa.Column("display_name", sa.String(length=128), nullable=True))
        if "jackett_indexer_id" not in cols:
            batch_op.add_column(sa.Column("jackett_indexer_id", sa.String(length=64), nullable=True))
        if "requires_auth" not in cols:
            batch_op.add_column(sa.Column("requires_auth", sa.Boolean(), nullable=True, server_default=sa.false()))
        if "created_at" not in cols:
            batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
        if "updated_at" not in cols:
            batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
        if "ix_trackers_provider_slug" not in idxs:
            batch_op.create_index("ix_trackers_provider_slug", ["provider_slug"], unique=False)
        batch_op.create_unique_constraint("uq_trackers_provider_slug", ["provider_slug"])
    op.execute("UPDATE trackers SET display_name = provider_slug WHERE display_name IS NULL")
    op.execute("UPDATE trackers SET requires_auth = false WHERE requires_auth IS NULL")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "trackers" not in inspector.get_table_names():
        return
    cols = [c["name"] for c in inspector.get_columns("trackers")]
    idxs = [c["name"] for c in inspector.get_indexes("trackers")]
    with op.batch_alter_table("trackers") as batch_op:
        batch_op.drop_constraint("uq_trackers_provider_slug", type_="unique")
        if "ix_trackers_provider_slug" in idxs:
            batch_op.drop_index("ix_trackers_provider_slug")
        if "provider_slug" in cols:
            batch_op.alter_column("provider_slug", new_column_name="name")
        if "torznab_url" in cols:
            batch_op.alter_column("torznab_url", new_column_name="base_url")
        for col in ("display_name", "jackett_indexer_id", "requires_auth", "created_at", "updated_at"):
            if col in cols:
                batch_op.drop_column(col)
        batch_op.add_column(sa.Column("creds_enc", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("username", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("password_enc", sa.String(length=512), nullable=True))
        batch_op.create_unique_constraint("uq_trackers_name", ["name"])
