"""add analytics indexes

Revision ID: a38e8ba630ba
Revises: faa129106552
Create Date: 2026-09-17 01:01:08.866130

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a38e8ba630ba'
down_revision: Union[str, Sequence[str], None] = 'faa129106552'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create analytics indexes"""
    
    # =========================================================================
    # JOB INDEXES
    # =========================================================================
    # Query: Get jobs by status and date range
    op.create_index(
        'ix_jobs_status_created_at',
        'jobs',
        ['status', 'created_at'],
        postgresql_where=sa.text("deleted_at IS NULL")
    )
    
    # Query: Get jobs by client and date
    op.create_index(
        'ix_jobs_client_id_created_at',
        'jobs',
        ['client_id', 'created_at'],
        postgresql_where=sa.text("deleted_at IS NULL")
    )
    
    # Query: Get published jobs (for time-to-first-proposal)
    op.create_index(
        'ix_jobs_published_at',
        'jobs',
        ['published_at'],
        postgresql_where=sa.text("published_at IS NOT NULL AND deleted_at IS NULL")
    )
    
    # Query: Get completed jobs
    op.create_index(
        'ix_jobs_closed_at',
        'jobs',
        ['closed_at'],
        postgresql_where=sa.text("closed_at IS NOT NULL AND deleted_at IS NULL")
    )
    
    # =========================================================================
    # PROPOSAL INDEXES
    # =========================================================================
    # Query: Proposal funnel (status + date)
    op.create_index(
        'ix_proposals_status_created_at',
        'proposals',
        ['status', 'created_at'],
        postgresql_where=sa.text("deleted_at IS NULL")
    )
    
    # Query: Proposals by job
    op.create_index(
        'ix_proposals_job_id_status',
        'proposals',
        ['job_id', 'status'],
        postgresql_where=sa.text("deleted_at IS NULL")
    )
    
    # Query: Proposals by freelancer (performance metrics)
    op.create_index(
        'ix_proposals_freelancer_id_created_at',
        'proposals',
        ['freelancer_id', 'created_at'],
        postgresql_where=sa.text("deleted_at IS NULL")
    )
    
    # Query: Accepted proposals (contracts)
    op.create_index(
        'ix_proposals_accepted_at',
        'proposals',
        ['accepted_at'],
        postgresql_where=sa.text("accepted_at IS NOT NULL AND deleted_at IS NULL")
    )

    op.create_index(
        'ix_contracts_status_created_at',
        'contracts',
        ['status', 'created_at'],
        postgresql_where=sa.text("deleted_at IS NULL")
    )
    
    op.create_index(
        'ix_contracts_client_id_created_at',
        'contracts',
        ['client_id', 'created_at'],
        postgresql_where=sa.text("deleted_at IS NULL")
    )
    
    op.create_index(
        'ix_contracts_freelancer_id_created_at',
        'contracts',
        ['freelancer_id', 'created_at'],
        postgresql_where=sa.text("deleted_at IS NULL")
    )
    
    op.create_index(
        'ix_contracts_completed_at',
        'contracts',
        ['completed_at'],
        postgresql_where=sa.text("completed_at IS NOT NULL AND deleted_at IS NULL")
    )

    op.create_index(
        'ix_milestones_status_created_at',
        'milestones',
        ['status', 'created_at']
    )
    
    op.create_index(
        'ix_milestones_contract_id_status',
        'milestones',
        ['contract_id', 'status']
    )
    
    op.create_index(
        'ix_milestones_due_date',
        'milestones',
        ['due_date'],
        postgresql_where=sa.text("status != 'APPROVED' AND due_date IS NOT NULL")
    )
    
    op.create_index(
        'ix_milestones_approved_at',
        'milestones',
        ['approved_at'],
        postgresql_where=sa.text("approved_at IS NOT NULL")
    )

    op.create_index(
        'ix_reviews_freelancer_id_created_at',
        'reviews',
        ['freelancer_id', 'created_at']
    )

    op.create_index(
        'ix_reviews_contract_id',
        'reviews',
        ['contract_id']
    )


def downgrade() -> None:
    """Drop analytics indexes"""
    op.drop_index('ix_reviews_contract_id', table_name='reviews')
    op.drop_index('ix_reviews_freelancer_id_created_at', table_name='reviews')
    op.drop_index('ix_milestones_approved_at', table_name='milestones')
    op.drop_index('ix_milestones_due_date', table_name='milestones')
    op.drop_index('ix_milestones_contract_id_status', table_name='milestones')
    op.drop_index('ix_milestones_status_created_at', table_name='milestones')
    op.drop_index('ix_contracts_completed_at', table_name='contracts')
    op.drop_index('ix_contracts_freelancer_id_created_at', table_name='contracts')
    op.drop_index('ix_contracts_client_id_created_at', table_name='contracts')
    op.drop_index('ix_contracts_status_created_at', table_name='contracts')
    op.drop_index('ix_proposals_accepted_at', table_name='proposals')
    op.drop_index('ix_proposals_freelancer_id_created_at', table_name='proposals')
    op.drop_index('ix_proposals_job_id_status', table_name='proposals')
    op.drop_index('ix_proposals_status_created_at', table_name='proposals')
    op.drop_index('ix_jobs_closed_at', table_name='jobs')
    op.drop_index('ix_jobs_published_at', table_name='jobs')
    op.drop_index('ix_jobs_client_id_created_at', table_name='jobs')
    op.drop_index('ix_jobs_status_created_at', table_name='jobs')