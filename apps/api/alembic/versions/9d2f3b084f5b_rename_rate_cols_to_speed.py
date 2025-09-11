"""rename rate columns to speed columns in downloads

Revision ID: 9d2f3b084f5b
Revises: 53c5c7dc5baf
Create Date: 2024-08-06
"""

from alembic import op
import sqlalchemy as sa


revision = "9d2f3b084f5b"
down_revision = "53c5c7dc5baf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "downloads" not in inspector.get_table_names():
        return

    def columns():
        return [c["name"] for c in inspector.get_columns("downloads")]

    with op.batch_alter_table("downloads") as batch_op:
        cols = columns()

        # Handle dlspeed (was rate_down)
        if "dlspeed" in cols:
            if "rate_down" in cols:
                batch_op.drop_column("rate_down")
        elif "rate_down" in cols:
            batch_op.alter_column(
                "rate_down",
                new_column_name="dlspeed",
                existing_type=sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        else:
            batch_op.add_column(sa.Column("dlspeed", sa.Integer(), nullable=False, server_default=sa.text("0")))

        # Handle upspeed (was rate_up)
        cols = columns()  # refresh
        if "upspeed" in cols:
            if "rate_up" in cols:
                batch_op.drop_column("rate_up")
        elif "rate_up" in cols:
            batch_op.alter_column(
                "rate_up",
                new_column_name="upspeed",
                existing_type=sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        else:
            batch_op.add_column(sa.Column("upspeed", sa.Integer(), nullable=False, server_default=sa.text("0")))

    op.execute(sa.text("UPDATE downloads SET dlspeed = 0 WHERE dlspeed IS NULL"))
    op.execute(sa.text("UPDATE downloads SET upspeed = 0 WHERE upspeed IS NULL"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "downloads" not in inspector.get_table_names():
        return

    cols = [c["name"] for c in inspector.get_columns("downloads")]

    with op.batch_alter_table("downloads") as batch_op:
        if "dlspeed" in cols:
            batch_op.alter_column(
                "dlspeed",
                new_column_name="rate_down",
                existing_type=sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        if "upspeed" in cols:
            batch_op.alter_column(
                "upspeed",
                new_column_name="rate_up",
                existing_type=sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )

    op.execute(sa.text("UPDATE downloads SET rate_down = 0 WHERE rate_down IS NULL"))
    op.execute(sa.text("UPDATE downloads SET rate_up = 0 WHERE rate_up IS NULL"))
