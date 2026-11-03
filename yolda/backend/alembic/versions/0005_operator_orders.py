"""operator buyurtmalar sahifasi: izohlar, mijoz eslatmalari, bloklash, jurnal

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('courier_note', sa.String(500), nullable=True))
    op.create_table(
        'order_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.BigInteger(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('actor', sa.String(200), nullable=False, server_default=''),
        sa.Column('text', sa.String(500), nullable=False),
    )
    op.create_index('ix_order_logs_order_id', 'order_logs', ['order_id'])
    op.create_table(
        'customer_notes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('phone', sa.String(30), nullable=False),
        sa.Column('text', sa.String(500), nullable=False),
        sa.Column('author', sa.String(200), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_customer_notes_phone', 'customer_notes', ['phone'])
    op.create_table(
        'blocked_customers',
        sa.Column('phone', sa.String(30), primary_key=True),
        sa.Column('reason', sa.String(300), nullable=False, server_default=''),
        sa.Column('blocked_by', sa.String(200), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('blocked_customers')
    op.drop_table('customer_notes')
    op.drop_table('order_logs')
    op.drop_column('orders', 'courier_note')
