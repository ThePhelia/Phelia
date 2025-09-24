"""Add unique constraint to trackers.name"""

from alembic import op
import sqlalchemy as sa


revision = 'b251c05cce76'
down_revision = 'dd3ffdcc1704'
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "trackers" not in inspector.get_table_names():
        return

    column_names = {column["name"] for column in inspector.get_columns("trackers")}
    if "name" not in column_names:
        return

    with op.batch_alter_table("trackers") as batch_op:
        batch_op.create_unique_constraint("uq_trackers_name", ["name"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "trackers" not in inspector.get_table_names():
        return

    constraints = inspector.get_unique_constraints("trackers")
    constraint_names = {constraint["name"] for constraint in constraints}
    if "uq_trackers_name" not in constraint_names:
        return

    with op.batch_alter_table("trackers") as batch_op:
        batch_op.drop_constraint("uq_trackers_name", type_="unique")
