"""corporate content photo fields for facilities and initiatives

Revision ID: 3f9a6d2b7c48
Revises: 5e8b2f0a3c17
Create Date: 2026-09-01 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '3f9a6d2b7c48'
down_revision = '5e8b2f0a3c17'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No inline ForeignKey() here on purpose - SQLite's ALTER TABLE can't add
    # a column and a constraint in one non-batch statement (same reason
    # submitted_by_id/approved_by_id etc. were added as plain columns
    # elsewhere in this history). The ORM model still declares the real
    # ForeignKey("media_records.id") for relationship/query purposes.
    op.add_column("manufacturing_facilities", sa.Column("photo_media_id", sa.String(length=32), nullable=True))
    op.add_column("research_facilities", sa.Column("photo_media_id", sa.String(length=32), nullable=True))
    op.add_column("sustainability_initiatives", sa.Column("photo_media_id", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("sustainability_initiatives", "photo_media_id")
    op.drop_column("research_facilities", "photo_media_id")
    op.drop_column("manufacturing_facilities", "photo_media_id")
