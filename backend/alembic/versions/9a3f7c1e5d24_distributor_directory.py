"""distributor directory opt-in fields

Revision ID: 9a3f7c1e5d24
Revises: 6c9e2a4b8d17
Create Date: 2026-08-30 18:10:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '9a3f7c1e5d24'
down_revision = '6c9e2a4b8d17'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("distributor_profiles", sa.Column("directory_opt_in", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("distributor_profiles", sa.Column("show_public_phone", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("distributor_profiles", sa.Column("show_public_email", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("distributor_profiles", "show_public_email")
    op.drop_column("distributor_profiles", "show_public_phone")
    op.drop_column("distributor_profiles", "directory_opt_in")
