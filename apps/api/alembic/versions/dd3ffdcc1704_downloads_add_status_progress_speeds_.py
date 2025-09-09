"""create initial tables"""

from alembic import op
import sqlalchemy as sa

revision = 'dd3ffdcc1704'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False, server_default='user'),
    )

    # trackers table
    op.create_table(
        'trackers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('type', sa.String(length=16), nullable=False),
        sa.Column('base_url', sa.String(length=255), nullable=True),
        sa.Column('creds_enc', sa.String(length=512), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('1')),
    )

    # downloads table
    op.create_table(
        'downloads',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('hash', sa.String(length=64), nullable=True),
        sa.Column('name', sa.String(length=512), nullable=True),
        sa.Column('magnet', sa.Text(), nullable=False),
        sa.Column('save_path', sa.String(length=1024), nullable=False),
        sa.Column('client', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='queued'),
        sa.Column('progress', sa.Float(), nullable=False, server_default='0'),
        sa.Column('dlspeed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('upspeed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('eta', sa.Integer(), nullable=True, server_default='0'),
    )
    op.create_index(op.f('ix_downloads_hash'), 'downloads', ['hash'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_downloads_hash'), table_name='downloads')
    op.drop_table('downloads')
    op.drop_table('trackers')
    op.drop_table('users')
