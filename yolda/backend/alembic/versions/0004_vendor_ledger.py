"""vendor ledger entries

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'vendor_ledger_entries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('restaurant_id', sa.Integer(), sa.ForeignKey('restaurants.id'), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('amount', sa.BigInteger(), nullable=False),
        sa.Column('order_id', sa.BigInteger(), nullable=True),
        sa.Column('note', sa.String(300), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_vendor_ledger_entries_restaurant_id', 'vendor_ledger_entries', ['restaurant_id'])
    op.create_index('ix_vendor_ledger_entries_created_at', 'vendor_ledger_entries', ['created_at'])


def downgrade() -> None:
    op.drop_table('vendor_ledger_entries')
