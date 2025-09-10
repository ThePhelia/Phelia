"""set default for downloads.created_at

Revision ID: a8f4b8a1d5e2
Revises: 9d2f3b084f5b
Create Date: 2024-09-15
"""

from alembic import op
import sqlalchemy as sa


revision = "a8f4b8a1d5e2"
down_revision = "9d2f3b084f5b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "downloads" not in inspector.get_table_names():
        return
    cols = [c["name"] for c in inspector.get_columns("downloads")]
    if "created_at" not in cols:
        return
    with op.batch_alter_table("downloads") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(),
            server_default=sa.func.now(),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "downloads" not in inspector.get_table_names():
        return
    cols = [c["name"] for c in inspector.get_columns("downloads")]
    if "created_at" not in cols:
        return
    with op.batch_alter_table("downloads") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(),
            server_default=None,
        )
