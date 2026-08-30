"""product pack size price

Revision ID: 1f5b8d3a7c62
Revises: 8a2c4f6e9b1d
Create Date: 2026-08-30 15:30:06.546999
"""
from alembic import op
import sqlalchemy as sa


revision = '1f5b8d3a7c62'
down_revision = '8a2c4f6e9b1d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("product_pack_sizes", sa.Column("price", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("product_pack_sizes", "price")
