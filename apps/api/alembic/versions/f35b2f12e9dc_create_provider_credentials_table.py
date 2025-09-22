"""create provider credentials table

Revision ID: f35b2f12e9dc
Revises: e6f4f3021f2b
Create Date: 2024-11-01

"""

from alembic import op
import sqlalchemy as sa


revision = "f35b2f12e9dc"
down_revision = "e6f4f3021f2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_credentials",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("api_key", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("provider", name="uq_provider_credentials_provider"),
    )


def downgrade() -> None:
    op.drop_table("provider_credentials")
