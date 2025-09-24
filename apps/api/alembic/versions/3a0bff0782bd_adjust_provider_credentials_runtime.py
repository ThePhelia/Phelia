"""Adjust provider credentials table for runtime refresh."""

from alembic import op
import sqlalchemy as sa


revision = "3a0bff0782bd"
down_revision = "f35b2f12e9dc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_credentials_new",
        sa.Column("provider_slug", sa.String(length=64), nullable=False),
        sa.Column("api_key", sa.String(length=512), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("provider_slug", name="pk_provider_credentials"),
    )

    op.execute(
        """
        INSERT INTO provider_credentials_new (provider_slug, api_key, updated_at)
        SELECT LOWER(provider), api_key, COALESCE(updated_at, CURRENT_TIMESTAMP)
        FROM provider_credentials
        WHERE api_key IS NOT NULL
        """
    )

    op.drop_table("provider_credentials")
    op.rename_table("provider_credentials_new", "provider_credentials")


def downgrade() -> None:
    op.create_table(
        "provider_credentials_old",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("api_key", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", name="uq_provider_credentials_provider"),
    )

    op.execute(
        """
        INSERT INTO provider_credentials_old (provider, api_key, created_at, updated_at)
        SELECT provider_slug, api_key, updated_at, updated_at
        FROM provider_credentials
        """
    )

    op.drop_table("provider_credentials")
    op.rename_table("provider_credentials_old", "provider_credentials")
