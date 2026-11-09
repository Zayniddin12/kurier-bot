"""naqd buyurtmalar: yetkazish haqi cash yozuvidan ayiriladi (earn + cash -> bitta cash)

Revision ID: 0007
Revises: 0006

Balans o'zgarmaydi: (+fee) + (-total) == -(total - fee).
"""
from alembic import op

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE ledger_entries c
        SET amount = c.amount + e.amount,
            note = 'Naqd pul mijozdan olindi (yetkazish haqi ayirildi)'
        FROM ledger_entries e
        WHERE c.type = 'cash' AND e.type = 'earn'
          AND c.order_id IS NOT NULL AND c.order_id = e.order_id AND c.courier_id = e.courier_id
    """)
    op.execute("""
        DELETE FROM ledger_entries e
        USING ledger_entries c
        WHERE e.type = 'earn' AND c.type = 'cash'
          AND c.order_id IS NOT NULL AND c.order_id = e.order_id AND c.courier_id = e.courier_id
    """)


def downgrade() -> None:
    pass  # qaytarib bo'lmaydi (yozuvlar birlashtirilgan)
