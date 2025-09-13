"""add username and password_enc columns to trackers

Revision ID: cdd7a497d5f9
Revises: a8f4b8a1d5e2
Create Date: 2024-10-20

"""

from alembic import op
import sqlalchemy as sa


revision = "cdd7a497d5f9"
down_revision = "a8f4b8a1d5e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "trackers" not in inspector.get_table_names():
        return
    cols = [c["name"] for c in inspector.get_columns("trackers")]
    with op.batch_alter_table("trackers") as batch_op:
        if "username" not in cols:
            batch_op.add_column(sa.Column("username", sa.String(length=128), nullable=True))
        if "password_enc" not in cols:
            batch_op.add_column(sa.Column("password_enc", sa.String(length=512), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "trackers" not in inspector.get_table_names():
        return
    cols = [c["name"] for c in inspector.get_columns("trackers")]
    with op.batch_alter_table("trackers") as batch_op:
        if "username" in cols:
            batch_op.drop_column("username")
        if "password_enc" in cols:
            batch_op.drop_column("password_enc")

