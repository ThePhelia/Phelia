
"""drop client column from downloads

Revision ID: 53c5c7dc5baf
Revises: b251c05cce76
Create Date: 2024-07-05

"""

from alembic import op
import sqlalchemy as sa

revision = "53c5c7dc5baf"
down_revision = "b251c05cce76"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "downloads" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("downloads")]
        if "client" in cols:
            with op.batch_alter_table("downloads") as batch_op:
                batch_op.drop_column("client")


def downgrade() -> None:
    with op.batch_alter_table("downloads") as batch_op:
        batch_op.add_column(sa.Column("client", sa.String(length=32), nullable=True))
