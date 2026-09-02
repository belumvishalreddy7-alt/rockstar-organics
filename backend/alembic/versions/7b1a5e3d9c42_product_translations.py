"""product translations (owner-entered, per-language content)

Revision ID: 7b1a5e3d9c42
Revises: c9d4e6a2f813
Create Date: 2026-09-02T06:10:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '7b1a5e3d9c42'
down_revision = 'c9d4e6a2f813'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("translations", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "translations")
