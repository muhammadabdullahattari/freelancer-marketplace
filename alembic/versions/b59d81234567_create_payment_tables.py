"""Create payment, refund, and payment_events tables

Revision ID: b59d81234567
Revises: a38e8ba630ba
Create Date: 2026-09-18 16:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b59d81234567'
down_revision: Union[str, Sequence[str], None] = 'a38e8ba630ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create payment tables"""
    
    # =========================================================================
    # PAYMENTS TABLE
    # =========================================================================
    op.create_table(
        'payments',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('stripe_payment_intent_id', sa.String(100), nullable=False),
        sa.Column('idempotency_key', sa.String(255), nullable=False),
        sa.Column('contract_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('freelancer_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('stripe_status', sa.String(50), nullable=True),
        sa.Column('payment_method_id', sa.String(100), nullable=True),
        sa.Column('payment_method_type', sa.String(50), nullable=True),
        sa.Column('card_last_four', sa.String(4), nullable=True),
        sa.Column('card_brand', sa.String(50), nullable=True),
        sa.Column('amount_refunded_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('refund_reason', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('succeeded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('refunded_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['freelancer_id'], ['freelancer_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_payment_intent_id'),
        sa.UniqueConstraint('idempotency_key')
    )
    op.create_index('ix_payments_stripe_payment_intent_id', 'payments', ['stripe_payment_intent_id'])
    op.create_index('ix_payments_idempotency_key', 'payments', ['idempotency_key'])
    op.create_index('ix_payments_contract_id', 'payments', ['contract_id'])
    op.create_index('ix_payments_status', 'payments', ['status'])
    op.create_index('ix_payments_contract_status', 'payments', ['contract_id', 'status'])
    op.create_index('ix_payments_status_created_at', 'payments', ['status', 'created_at'])
    op.create_index('ix_payments_client_created_at', 'payments', ['client_id', 'created_at'])
    op.create_index('ix_payments_freelancer_created_at', 'payments', ['freelancer_id', 'created_at'])
    
    # =========================================================================
    # REFUNDS TABLE
    # =========================================================================
    op.create_table(
        'refunds',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('stripe_refund_id', sa.String(100), nullable=False),
        sa.Column('idempotency_key', sa.String(255), nullable=False),
        sa.Column('payment_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('succeeded_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_refund_id'),
        sa.UniqueConstraint('idempotency_key')
    )
    op.create_index('ix_refunds_stripe_refund_id', 'refunds', ['stripe_refund_id'])
    op.create_index('ix_refunds_payment_id', 'refunds', ['payment_id'])
    op.create_index('ix_refunds_status', 'refunds', ['status'])
    op.create_index('ix_refunds_payment_status', 'refunds', ['payment_id', 'status'])
    
    # =========================================================================
    # PAYMENT EVENTS TABLE
    # =========================================================================
    op.create_table(
        'payment_events',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('payment_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('stripe_event_id', sa.String(100), nullable=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_data', postgresql.JSON(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False, server_default='api'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_event_id')
    )
    op.create_index('ix_payment_events_payment_id', 'payment_events', ['payment_id'])
    op.create_index('ix_payment_events_stripe_event_id', 'payment_events', ['stripe_event_id'])
    op.create_index('ix_payment_events_event_type', 'payment_events', ['event_type'])
    op.create_index('ix_payment_events_payment_created', 'payment_events', ['payment_id', 'created_at'])
    
    # =========================================================================
    # SUBSCRIPTIONS TABLE
    # =========================================================================
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(100), nullable=False),
        sa.Column('freelancer_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('billing_cycle', sa.String(50), nullable=False, server_default='monthly'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['freelancer_id'], ['freelancer_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_subscription_id')
    )
    op.create_index('ix_subscriptions_stripe_subscription_id', 'subscriptions', ['stripe_subscription_id'])
    op.create_index('ix_subscriptions_freelancer_id', 'subscriptions', ['freelancer_id'])
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'])


def downgrade() -> None:
    """Drop payment tables"""
    op.drop_index('ix_subscriptions_status', table_name='subscriptions')
    op.drop_index('ix_subscriptions_freelancer_id', table_name='subscriptions')
    op.drop_index('ix_subscriptions_stripe_subscription_id', table_name='subscriptions')
    op.drop_table('subscriptions')
    
    op.drop_index('ix_payment_events_payment_created', table_name='payment_events')
    op.drop_index('ix_payment_events_event_type', table_name='payment_events')
    op.drop_index('ix_payment_events_stripe_event_id', table_name='payment_events')
    op.drop_index('ix_payment_events_payment_id', table_name='payment_events')
    op.drop_table('payment_events')
    
    op.drop_index('ix_refunds_payment_status', table_name='refunds')
    op.drop_index('ix_refunds_status', table_name='refunds')
    op.drop_index('ix_refunds_payment_id', table_name='refunds')
    op.drop_index('ix_refunds_stripe_refund_id', table_name='refunds')
    op.drop_table('refunds')
    
    op.drop_index('ix_payments_freelancer_created_at', table_name='payments')
    op.drop_index('ix_payments_client_created_at', table_name='payments')
    op.drop_index('ix_payments_status_created_at', table_name='payments')
    op.drop_index('ix_payments_contract_status', table_name='payments')
    op.drop_index('ix_payments_status', table_name='payments')
    op.drop_index('ix_payments_contract_id', table_name='payments')
    op.drop_index('ix_payments_idempotency_key', table_name='payments')
    op.drop_index('ix_payments_stripe_payment_intent_id', table_name='payments')
    op.drop_table('payments')
