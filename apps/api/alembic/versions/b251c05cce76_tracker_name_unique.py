"""Add unique constraint to trackers.name"""

from alembic import op
import sqlalchemy as sa


revision = 'b251c05cce76'
down_revision = 'dd3ffdcc1704'
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table('trackers') as batch_op:
        batch_op.create_unique_constraint('uq_trackers_name', ['name'])


def downgrade() -> None:
    with op.batch_alter_table('trackers') as batch_op:
        batch_op.drop_constraint('uq_trackers_name', type_='unique')
