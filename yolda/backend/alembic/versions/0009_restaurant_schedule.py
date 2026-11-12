"""restoran haftalik ish jadvali (schedule) va hours uzunligi

Revision ID: 0009
Revises: 0008
"""
import sqlalchemy as sa
from alembic import op

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('restaurants', sa.Column('schedule', sa.JSON(), nullable=True))
    op.alter_column('restaurants', 'hours', type_=sa.String(200), existing_type=sa.String(30))


def downgrade() -> None:
    op.alter_column('restaurants', 'hours', type_=sa.String(30), existing_type=sa.String(200))
    op.drop_column('restaurants', 'schedule')
