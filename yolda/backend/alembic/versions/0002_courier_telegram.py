"""courier telegram_id

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('couriers', sa.Column('telegram_id', sa.BigInteger(), nullable=True))
    op.create_unique_constraint('uq_couriers_telegram_id', 'couriers', ['telegram_id'])


def downgrade() -> None:
    op.drop_constraint('uq_couriers_telegram_id', 'couriers', type_='unique')
    op.drop_column('couriers', 'telegram_id')
