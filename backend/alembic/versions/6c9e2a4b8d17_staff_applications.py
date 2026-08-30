"""staff applications

Revision ID: 6c9e2a4b8d17
Revises: 1f5b8d3a7c62
Create Date: 2026-08-30 17:22:55.639631
"""
from alembic import op
import sqlalchemy as sa


revision = '6c9e2a4b8d17'
down_revision = '1f5b8d3a7c62'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "staff_applications",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("reference_number", sa.String(length=30), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("position_applied_for", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("consent_given", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="new"),
        sa.Column("reviewer_id", sa.String(length=32), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("staff_applications")
