"""onlayn to'lovlar (Multicard)

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('restaurant_id', sa.Integer(), sa.ForeignKey('restaurants.id'), nullable=False),
        sa.Column('provider', sa.String(20), nullable=False, server_default='multicard'),
        sa.Column('method', sa.String(20), nullable=False, server_default='card'),
        sa.Column('invoice_id', sa.String(100), nullable=False, unique=True),
        sa.Column('provider_uuid', sa.String(64), nullable=True),
        sa.Column('amount', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('checkout_url', sa.String(500), nullable=True),
        sa.Column('short_link', sa.String(300), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('billing_id', sa.String(100), nullable=True),
        sa.Column('card_pan', sa.String(32), nullable=True),
        sa.Column('ps', sa.String(20), nullable=True),
        sa.Column('receipt_url', sa.String(500), nullable=True),
        sa.Column('raw_callback', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_payments_order_id', 'payments', ['order_id'])
    op.create_index('ix_payments_restaurant_id', 'payments', ['restaurant_id'])
    op.create_index('ix_payments_provider_uuid', 'payments', ['provider_uuid'])
    op.create_index('ix_payments_status', 'payments', ['status'])


def downgrade() -> None:
    op.drop_table('payments')
