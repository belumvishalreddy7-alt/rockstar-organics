"""otp_codes: allow purpose="login" rows (no pending signup payload)

Revision ID: b47e2f9a6c31
Revises: 3f9a6d2b7c48
Create Date: 2026-09-01 15:10:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'b47e2f9a6c31'
down_revision = '3f9a6d2b7c48'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A purpose="login" OTP (staff/dealer/distributor sign-in second factor)
    # is for an account that already exists, so it never fills in the
    # pending-signup columns - they need to accept NULL for that row shape.
    # batch_alter_table for SQLite compatibility (see other ALTER-constraint
    # migrations in this history).
    with op.batch_alter_table("otp_codes") as batch_op:
        batch_op.alter_column("pending_full_name", existing_type=sa.String(length=255), nullable=True)
        batch_op.alter_column("pending_password_hash", existing_type=sa.String(length=255), nullable=True)
        batch_op.alter_column("pending_role", existing_type=sa.String(length=32), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("otp_codes") as batch_op:
        batch_op.alter_column("pending_role", existing_type=sa.String(length=32), nullable=False)
        batch_op.alter_column("pending_password_hash", existing_type=sa.String(length=255), nullable=False)
        batch_op.alter_column("pending_full_name", existing_type=sa.String(length=255), nullable=False)
