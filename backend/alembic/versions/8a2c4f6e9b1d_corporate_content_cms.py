"""corporate content cms

Revision ID: 8a2c4f6e9b1d
Revises: f1fe791a816d
Create Date: 2026-08-29 22:34:01.417360
"""
from alembic import op
import sqlalchemy as sa


revision = '8a2c4f6e9b1d'
down_revision = 'f1fe791a816d'
branch_labels = None
depends_on = None


def _verifiable_columns() -> list:
    """The shared verification/approval/publication/audit columns every
    corporate-content CMS table carries - see
    app.models.models.VerifiableMixin."""
    return [
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column("verification_notes", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.String(length=32), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by_id", sa.String(length=32), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("submitted_by_id", sa.String(length=32), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("reviewer_id", sa.String(length=32), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by_id", sa.String(length=32), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("published_by_id", sa.String(length=32), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "company_page_contents",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("section", sa.String(length=40), nullable=False, unique=True),
        sa.Column("fields", sa.JSON(), nullable=False),
        *_verifiable_columns(),
    )

    op.create_table(
        "leadership_profiles",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("position", sa.String(length=255), nullable=False),
        sa.Column("biography", sa.Text(), nullable=True),
        sa.Column("photo_media_id", sa.String(length=32), sa.ForeignKey("media_records.id"), nullable=True),
        sa.Column("responsibilities", sa.Text(), nullable=True),
        sa.Column("experience", sa.Text(), nullable=True),
        sa.Column("education", sa.Text(), nullable=True),
        sa.Column("profile_url", sa.String(length=500), nullable=True),
        sa.Column("joining_date", sa.DateTime(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        *_verifiable_columns(),
    )

    op.create_table(
        "manufacturing_facilities",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("facility_type", sa.String(length=100), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("capabilities", sa.Text(), nullable=True),
        sa.Column("certifications_text", sa.Text(), nullable=True),
        sa.Column("capacity", sa.String(length=255), nullable=True),
        sa.Column("established_date", sa.DateTime(), nullable=True),
        sa.Column("contact_info", sa.String(length=500), nullable=True),
        *_verifiable_columns(),
    )

    op.create_table(
        "research_facilities",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("facility_type", sa.String(length=100), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("capabilities", sa.Text(), nullable=True),
        sa.Column("equipment_info", sa.Text(), nullable=True),
        *_verifiable_columns(),
    )

    op.create_table(
        "research_areas",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_media_id", sa.String(length=32), sa.ForeignKey("media_records.id"), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        *_verifiable_columns(),
    )

    op.create_table(
        "certifications",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("certificate_number", sa.String(length=100), nullable=True),
        sa.Column("issuing_organization", sa.String(length=255), nullable=True),
        sa.Column("issue_date", sa.DateTime(), nullable=True),
        sa.Column("expiry_date", sa.DateTime(), nullable=True),
        sa.Column("document_media_id", sa.String(length=32), sa.ForeignKey("media_records.id"), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        *_verifiable_columns(),
    )

    op.create_table(
        "sustainability_initiatives",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("start_date", sa.DateTime(), nullable=True),
        sa.Column("measurable_results", sa.Text(), nullable=True),
        *_verifiable_columns(),
    )


def downgrade() -> None:
    op.drop_table("sustainability_initiatives")
    op.drop_table("certifications")
    op.drop_table("research_areas")
    op.drop_table("research_facilities")
    op.drop_table("manufacturing_facilities")
    op.drop_table("leadership_profiles")
    op.drop_table("company_page_contents")
