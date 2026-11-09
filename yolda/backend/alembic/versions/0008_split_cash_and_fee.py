"""naqd buyurtmalar: birlashtirilgan cash yozuvi qayta ikkiga bo'linadi (earn +fee, cash −total)

Revision ID: 0008
Revises: 0007

0007 dagi birlashtirishni qaytaradi. Balans o'zgarmaydi: (+fee) + (−total) == −(total − fee).
"""
from alembic import op

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None

NET_NOTE = 'Naqd pul mijozdan olindi (yetkazish haqi ayirildi)'


def upgrade() -> None:
    # 1) yetkazish haqini alohida earn qatori sifatida qaytarish (cash dan 1 ms oldin)
    op.execute(f"""
        INSERT INTO ledger_entries (courier_id, type, amount, order_id, note, created_at)
        SELECT c.courier_id, 'earn', c.amount + o.total, c.order_id, 'Yetkazish haqi', c.created_at - interval '1 millisecond'
        FROM ledger_entries c JOIN orders o ON o.id = c.order_id
        WHERE c.type = 'cash' AND c.note = '{NET_NOTE}' AND c.order_id IS NOT NULL
    """)
    # 2) cash qatori yana butun summa
    op.execute(f"""
        UPDATE ledger_entries c
        SET amount = -o.total, note = 'Naqd pul mijozdan olindi'
        FROM orders o
        WHERE o.id = c.order_id AND c.type = 'cash' AND c.note = '{NET_NOTE}'
    """)


def downgrade() -> None:
    pass
