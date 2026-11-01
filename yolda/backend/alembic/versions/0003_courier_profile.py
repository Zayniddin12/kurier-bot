"""courier profile fields

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

COLS = [('birth_date', sa.Date()), ('license_no', sa.String(30)), ('vehicle_doc', sa.String(30)),
        ('car_model', sa.String(60)), ('city', sa.String(60))]


def upgrade() -> None:
    for name, t in COLS:
        op.add_column('couriers', sa.Column(name, t, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(COLS):
        op.drop_column('couriers', name)
