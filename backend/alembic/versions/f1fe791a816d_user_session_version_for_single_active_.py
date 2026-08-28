"""user session version for single active session

Revision ID: f1fe791a816d
Revises: 30f139a6e22b
Create Date: 2026-08-28 21:39:40.085392
"""
from alembic import op
import sqlalchemy as sa


revision = 'f1fe791a816d'
down_revision = '30f139a6e22b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('session_version', sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'session_version')
