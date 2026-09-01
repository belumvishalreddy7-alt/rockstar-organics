"""drop unused product pack size/crop/claim/certification/document tables

Revision ID: c9d4e6a2f813
Revises: b47e2f9a6c31
Create Date: 2026-09-01 17:20:00.000000
"""
from alembic import op


revision = 'c9d4e6a2f813'
down_revision = 'b47e2f9a6c31'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # These sub-entity tables (structured pack sizes, crop associations,
    # marketing claims, certifications, documents) were never surfaced to
    # real customers except pack sizes on the public product page - removed
    # at the owner's explicit request as unused product-system clutter.
    op.drop_table("product_documents")
    op.drop_table("product_certifications")
    op.drop_table("product_claims")
    op.drop_table("product_crops")
    op.drop_table("product_pack_sizes")


def downgrade() -> None:
    from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text

    op.create_table(
        "product_pack_sizes",
        Column("id", String(32), primary_key=True),
        Column("product_id", String(32), ForeignKey("products.id"), nullable=False),
        Column("quantity", String(30), nullable=False),
        Column("unit", String(20), nullable=False),
        Column("packaging_type", String(60), nullable=True),
        Column("sku", String(60), nullable=True),
        Column("price", Numeric(10, 2), nullable=True),
        Column("availability_status", String(20), nullable=False, server_default="available"),
        Column("sort_order", Integer, nullable=False, server_default="0"),
    )
    op.create_table(
        "product_crops",
        Column("id", String(32), primary_key=True),
        Column("product_id", String(32), ForeignKey("products.id"), nullable=False),
        Column("crop_name", String(100), nullable=False),
        Column("crop_category", String(100), nullable=True),
        Column("target_use", String(255), nullable=True),
        Column("application_stage", String(100), nullable=True),
        Column("sort_order", Integer, nullable=False, server_default="0"),
    )
    op.create_table(
        "product_claims",
        Column("id", String(32), primary_key=True),
        Column("product_id", String(32), ForeignKey("products.id"), nullable=False),
        Column("claim_text", Text, nullable=False),
        Column("category", String(30), nullable=False, server_default="benefit"),
        Column("source_evidence", Text, nullable=True),
        Column("verification_status", String(20), nullable=False, server_default="pending"),
        Column("verified_by_id", String(32), ForeignKey("users.id"), nullable=True),
        Column("verified_at", DateTime, nullable=True),
        Column("created_at", DateTime, nullable=True),
    )
    op.create_table(
        "product_certifications",
        Column("id", String(32), primary_key=True),
        Column("product_id", String(32), ForeignKey("products.id"), nullable=False),
        Column("name", String(255), nullable=False),
        Column("issuing_organization", String(255), nullable=True),
        Column("certificate_number", String(100), nullable=True),
        Column("issue_date", DateTime, nullable=True),
        Column("expiry_date", DateTime, nullable=True),
        Column("media_id", String(32), ForeignKey("media_records.id"), nullable=True),
        Column("verification_status", String(20), nullable=False, server_default="pending"),
        Column("created_at", DateTime, nullable=True),
    )
    op.create_table(
        "product_documents",
        Column("id", String(32), primary_key=True),
        Column("product_id", String(32), ForeignKey("products.id"), nullable=False),
        Column("document_type", String(30), nullable=False),
        Column("title", String(255), nullable=False),
        Column("version", String(30), nullable=True),
        Column("issue_date", DateTime, nullable=True),
        Column("expiry_date", DateTime, nullable=True),
        Column("document_number", String(100), nullable=True),
        Column("media_id", String(32), ForeignKey("media_records.id"), nullable=False),
        Column("uploaded_by_id", String(32), ForeignKey("users.id"), nullable=True),
        Column("verification_status", String(20), nullable=False, server_default="pending"),
        Column("reviewed_by_id", String(32), ForeignKey("users.id"), nullable=True),
        Column("reviewed_at", DateTime, nullable=True),
        Column("created_at", DateTime, nullable=True),
    )
