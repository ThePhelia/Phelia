"""Drop provider credential storage."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "4d1c4bb7f0fe"
down_revision = "2b742bd4cfa6"
branch_labels = None
depends_on = None


_TABLE_NAME = "provider_credentials"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if _TABLE_NAME in inspector.get_table_names():
        op.drop_table(_TABLE_NAME)


def downgrade() -> None:
    op.create_table(
        _TABLE_NAME,
        sa.Column("provider_slug", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("api_key", sa.String(length=512), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
