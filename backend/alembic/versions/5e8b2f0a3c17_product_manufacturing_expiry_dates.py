"""product manufacturing and expiry dates

Revision ID: 5e8b2f0a3c17
Revises: 9a3f7c1e5d24
Create Date: 2026-09-01 13:10:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '5e8b2f0a3c17'
down_revision = '9a3f7c1e5d24'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("manufacturing_date", sa.Date(), nullable=True))
    op.add_column("products", sa.Column("expiry_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "expiry_date")
    op.drop_column("products", "manufacturing_date")
