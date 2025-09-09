"""Add unique constraint to trackers.name"""

from alembic import op
import sqlalchemy as sa


revision = 'b251c05cce76'
down_revision = '1a1ed61f4de0'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_unique_constraint('uq_trackers_name', 'trackers', ['name'])


def downgrade() -> None:
    op.drop_constraint('uq_trackers_name', 'trackers', type_='unique')
