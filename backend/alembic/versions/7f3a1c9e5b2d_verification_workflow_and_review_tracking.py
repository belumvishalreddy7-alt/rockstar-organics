"""verification workflow and review tracking

Purely additive: new nullable/defaulted columns on company_documents,
agriculture_photos, and product_reviews to support a fuller
submitted -> reviewed -> approved -> published -> archived workflow and
review update tracking. No existing column is renamed, retyped, or
dropped, and no data is deleted - safe to run against a database that
already has rows in these tables.

Revision ID: 7f3a1c9e5b2d
Revises: 04ea96319340
Create Date: 2026-08-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '7f3a1c9e5b2d'
down_revision = '04ea96319340'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('company_documents') as batch_op:
        batch_op.add_column(sa.Column('submitted_by_id', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('submitted_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('rejection_reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('is_approved', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('approved_by_id', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('approved_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('published_by_id', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('published_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('archived_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
        batch_op.create_foreign_key('fk_company_documents_submitted_by', 'users', ['submitted_by_id'], ['id'])
        batch_op.create_foreign_key('fk_company_documents_approved_by', 'users', ['approved_by_id'], ['id'])
        batch_op.create_foreign_key('fk_company_documents_published_by', 'users', ['published_by_id'], ['id'])

    # Backfill submitted_by/submitted_at from the existing uploader/created
    # columns so old rows have sensible values for the new fields instead
    # of NULL.
    op.execute("UPDATE company_documents SET submitted_by_id = uploaded_by_id, submitted_at = created_at")

    with op.batch_alter_table('agriculture_photos') as batch_op:
        batch_op.add_column(sa.Column('submitted_by_id', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('submitted_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('rejection_reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('approved_by_id', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('approved_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('published_by_id', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('published_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
        batch_op.create_foreign_key('fk_agriculture_photos_submitted_by', 'users', ['submitted_by_id'], ['id'])
        batch_op.create_foreign_key('fk_agriculture_photos_approved_by', 'users', ['approved_by_id'], ['id'])
        batch_op.create_foreign_key('fk_agriculture_photos_published_by', 'users', ['published_by_id'], ['id'])

    op.execute("UPDATE agriculture_photos SET submitted_by_id = uploaded_by_id, submitted_at = created_at")

    with op.batch_alter_table('product_reviews') as batch_op:
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))

    op.execute("UPDATE product_reviews SET updated_at = created_at WHERE updated_at IS NULL")


def downgrade() -> None:
    with op.batch_alter_table('product_reviews') as batch_op:
        batch_op.drop_column('updated_at')

    with op.batch_alter_table('agriculture_photos') as batch_op:
        batch_op.drop_constraint('fk_agriculture_photos_published_by', type_='foreignkey')
        batch_op.drop_constraint('fk_agriculture_photos_approved_by', type_='foreignkey')
        batch_op.drop_constraint('fk_agriculture_photos_submitted_by', type_='foreignkey')
        batch_op.drop_column('version')
        batch_op.drop_column('published_at')
        batch_op.drop_column('published_by_id')
        batch_op.drop_column('approved_at')
        batch_op.drop_column('approved_by_id')
        batch_op.drop_column('rejection_reason')
        batch_op.drop_column('submitted_at')
        batch_op.drop_column('submitted_by_id')

    with op.batch_alter_table('company_documents') as batch_op:
        batch_op.drop_constraint('fk_company_documents_published_by', type_='foreignkey')
        batch_op.drop_constraint('fk_company_documents_approved_by', type_='foreignkey')
        batch_op.drop_constraint('fk_company_documents_submitted_by', type_='foreignkey')
        batch_op.drop_column('version')
        batch_op.drop_column('archived_at')
        batch_op.drop_column('is_archived')
        batch_op.drop_column('published_at')
        batch_op.drop_column('published_by_id')
        batch_op.drop_column('approved_at')
        batch_op.drop_column('approved_by_id')
        batch_op.drop_column('is_approved')
        batch_op.drop_column('rejection_reason')
        batch_op.drop_column('submitted_at')
        batch_op.drop_column('submitted_by_id')
