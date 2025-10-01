"""add plugin settings table

Revision ID: 2b742bd4cfa6
Revises: f35b2f12e9dc
Create Date: 2024-07-23 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2b742bd4cfa6"
down_revision = "f35b2f12e9dc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plugin_settings",
        sa.Column("plugin_id", sa.String(length=128), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("plugin_id", "key"),
    )


def downgrade() -> None:
    op.drop_table("plugin_settings")
