"""Add indexing for document foreign keys

Revision ID: 3a9c162e661a
Revises: ff569d2627af
Create Date: 2026-07-12 00:46:41.884468
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '3a9c162e661a'
down_revision: Union[str, None] = 'ff569d2627af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add indexes for document foreign keys
    op.create_index('idx_document_pages_doc_id', 'document_pages', ['document_id'])
    op.create_index('idx_document_blocks_doc_id', 'document_blocks', ['document_id'])
    op.create_index('idx_document_entities_doc_id', 'document_entities', ['document_id'])
    op.create_index('idx_processing_jobs_doc_id', 'processing_jobs', ['document_id'])
    op.create_index('idx_human_reviews_doc_id', 'human_reviews', ['document_id'])


def downgrade() -> None:
    op.drop_index('idx_document_pages_doc_id', 'document_pages')
    op.drop_index('idx_document_blocks_doc_id', 'document_blocks')
    op.drop_index('idx_document_entities_doc_id', 'document_entities')
    op.drop_index('idx_processing_jobs_doc_id', 'processing_jobs')
    op.drop_index('idx_human_reviews_doc_id', 'human_reviews')
