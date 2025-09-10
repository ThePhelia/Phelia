
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
    if "downloads" not in inspector.get_table_names():
        return
    cols = [c["name"] for c in inspector.get_columns("downloads")]
    with op.batch_alter_table("downloads") as batch_op:
        if "client" in cols:
            batch_op.drop_column("client")

        if "status" in cols:
            batch_op.alter_column(
                "status",
                existing_type=sa.String(length=32),
                nullable=False,
                server_default=sa.text("'queued'"),
            )
        else:
            batch_op.add_column(
                sa.Column(
                    "status",
                    sa.String(length=32),
                    nullable=False,
                    server_default=sa.text("'queued'"),
                )
            )

        if "progress" in cols:
            batch_op.alter_column(
                "progress",
                existing_type=sa.Float(),
                nullable=False,
                server_default=sa.text("0"),
            )
        else:
            batch_op.add_column(
                sa.Column(
                    "progress",
                    sa.Float(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )

        if "dlspeed" in cols:
            batch_op.alter_column(
                "dlspeed",
                existing_type=sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        else:
            batch_op.add_column(
                sa.Column(
                    "dlspeed",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )

        if "upspeed" in cols:
            batch_op.alter_column(
                "upspeed",
                existing_type=sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        else:
            batch_op.add_column(
                sa.Column(
                    "upspeed",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )

        if "eta" in cols:
            batch_op.alter_column(
                "eta",
                existing_type=sa.Integer(),
                nullable=True,
                server_default=sa.text("0"),
            )
        else:
            batch_op.add_column(
                sa.Column(
                    "eta",
                    sa.Integer(),
                    nullable=True,
                    server_default=sa.text("0"),
                )
            )

    op.execute(sa.text("UPDATE downloads SET status = 'queued' WHERE status IS NULL"))
    op.execute(sa.text("UPDATE downloads SET progress = 0 WHERE progress IS NULL"))
    op.execute(sa.text("UPDATE downloads SET dlspeed = 0 WHERE dlspeed IS NULL"))
    op.execute(sa.text("UPDATE downloads SET upspeed = 0 WHERE upspeed IS NULL"))
    op.execute(sa.text("UPDATE downloads SET eta = 0 WHERE eta IS NULL"))


def downgrade() -> None:
    with op.batch_alter_table("downloads") as batch_op:
        batch_op.add_column(sa.Column("client", sa.String(length=32), nullable=True))
