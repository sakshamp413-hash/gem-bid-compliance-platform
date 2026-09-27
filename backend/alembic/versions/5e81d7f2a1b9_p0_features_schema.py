"""p0 features schema (corrigenda, vendor_readiness, remediation_tasks, async_jobs)

Revision ID: 5e81d7f2a1b9
Revises: 429533a83b0b
Create Date: 2026-09-27 15:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5e81d7f2a1b9'
down_revision: Union[str, None] = '429533a83b0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tender_corrigenda',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tender_id', sa.Integer(), sa.ForeignKey('tenders.id'), nullable=False),
        sa.Column('corrigendum_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('pdf_hash', sa.String(length=64), nullable=True),
        sa.Column('diff_json', sa.JSON(), nullable=True),
        sa.Column('affected_bidder_ids', sa.JSON(), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_tender_corrigenda_tender_id', 'tender_corrigenda', ['tender_id'])

    op.create_table(
        'vendor_readiness_cache',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('bidder_id', sa.Integer(), sa.ForeignKey('bidders.id'), nullable=False),
        sa.Column('tender_id', sa.Integer(), sa.ForeignKey('tenders.id'), nullable=False),
        sa.Column('readiness_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('gap_items', sa.JSON(), nullable=True),
        sa.Column('computed_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_vendor_readiness_cache_bidder_id', 'vendor_readiness_cache', ['bidder_id'])
    op.create_index('ix_vendor_readiness_cache_tender_id', 'vendor_readiness_cache', ['tender_id'])

    op.create_table(
        'remediation_tasks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('submission_id', sa.Integer(), sa.ForeignKey('bid_submissions.id'), nullable=False),
        sa.Column('requirement_id', sa.String(length=80), nullable=False),
        sa.Column('label', sa.String(length=300), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('estimated_days', sa.Integer(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_remediation_tasks_submission_id', 'remediation_tasks', ['submission_id'])

    op.create_table(
        'async_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('job_type', sa.String(length=60), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='queued'),
        sa.Column('progress_pct', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('result_json', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('context_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_async_jobs_job_id', 'async_jobs', ['job_id'], unique=True)


def downgrade() -> None:
    op.drop_table('async_jobs')
    op.drop_table('remediation_tasks')
    op.drop_table('vendor_readiness_cache')
    op.drop_table('tender_corrigenda')
