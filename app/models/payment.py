from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, Enum, JSON, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from sqlalchemy import Uuid
from uuid import UUID
import uuid
import enum


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"                      
    PROCESSING = "processing"                
    SUCCEEDED = "succeeded"                  
    FAILED = "failed"                        
    REFUNDED = "refunded"                    
    PARTIALLY_REFUNDED = "partially_refunded"
    CANCELLED = "cancelled"


class PaymentIntentStatus(str, enum.Enum):
    REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    REQUIRES_ACTION = "requires_action"
    PROCESSING = "processing"
    REQUIRES_CAPTURE = "requires_capture"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"


class RefundStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"

class Payment(Base):

    __tablename__ = "payments"
    
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    stripe_payment_intent_id: Mapped[str] = mapped_column(
        String(100), 
        nullable=False, 
        unique=True, 
        index=True,
        doc="Stripe PaymentIntent ID (used for idempotency)"
    )
    
    idempotency_key: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        unique=True, 
        index=True,
        doc="Deterministic key to prevent duplicate payments"
    )
    
    contract_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), 
        ForeignKey("contracts.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True,
        doc="Associated contract"
    )
    
    client_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True,
        doc="Client paying"
    )
    
    freelancer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), 
        ForeignKey("freelancer_profiles.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True,
        doc="Freelancer receiving payment"
    )
    
    amount_cents: Mapped[int] = mapped_column(
        Integer, 
        nullable=False,
        doc="Amount in cents (5000 = $50.00 USD). Use INTEGER to avoid float precision issues."
    )
    
    currency: Mapped[str] = mapped_column(
        String(3), 
        default="USD", 
        nullable=False,
        doc="ISO 4217 currency code"
    )
    
    amount_refunded_cents: Mapped[int] = mapped_column(
        Integer, 
        default=0, 
        nullable=False,
        doc="Total amount refunded in cents"
    )

    status: Mapped[str] = mapped_column(
        String(50), 
        default=PaymentStatus.PENDING.value, 
        nullable=False, 
        index=True,
        doc="Our internal payment status (PENDING, PROCESSING, SUCCEEDED, FAILED, etc)"
    )
    
    stripe_status: Mapped[str | None] = mapped_column(
        String(50), 
        nullable=True,
        doc="Mirror of Stripe's PaymentIntent.status"
    )
    
    payment_method_id: Mapped[str | None] = mapped_column(
        String(100), 
        nullable=True,
        doc="Stripe PaymentMethod ID (NOT card number)"
    )
    
    payment_method_type: Mapped[str | None] = mapped_column(
        String(50), 
        nullable=True,
        doc="card, wallet, etc"
    )
    
    card_last_four: Mapped[str | None] = mapped_column(
        String(4), 
        nullable=True,
        doc="Last 4 digits (for display only, NOT full card)"
    )
    
    card_brand: Mapped[str | None] = mapped_column(
        String(50), 
        nullable=True,
        doc="visa, mastercard, amex, discover"
    )
    
    refund_reason: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True,
        doc="Reason for refund (if any)"
    )
    
    description: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        doc="Human-readable payment description"
    )
    
    payment_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON, 
        nullable=True,
        doc="Custom JSON metadata (stored in Stripe too)"
    )
    
    error_code: Mapped[str | None] = mapped_column(
        String(50), 
        nullable=True,
        doc="Stripe error code (if payment failed)"
    )
    
    error_message: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        doc="Human-readable error message (if payment failed)"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False, 
        index=True
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    
    succeeded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        doc="When payment succeeded"
    )
    
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        doc="When payment failed"
    )
    
    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        doc="When refund was initiated"
    )
    
    contract: Mapped["Contract"] = relationship("Contract", foreign_keys=[contract_id])
    client: Mapped["User"] = relationship("User", foreign_keys=[client_id])
    freelancer: Mapped["FreelancerProfile"] = relationship("FreelancerProfile", foreign_keys=[freelancer_id])
    refunds: Mapped[list["Refund"]] = relationship("Refund", back_populates="payment", cascade="all, delete-orphan")
    events: Mapped[list["PaymentEvent"]] = relationship("PaymentEvent", back_populates="payment", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_payments_contract_status', 'contract_id', 'status'),
        Index('ix_payments_status_created_at', 'status', 'created_at'),
        Index('ix_payments_client_created_at', 'client_id', 'created_at'),
        Index('ix_payments_freelancer_created_at', 'freelancer_id', 'created_at'))
    
    def __repr__(self):
        return f"<Payment {self.id} {self.status} ${self.amount_cents/100:.2f}>"
    
    @property
    def amount_usd(self) -> float:
        return self.amount_cents / 100
    
    @property
    def amount_refunded_usd(self) -> float:
        return self.amount_refunded_cents / 100
    
    @property
    def amount_remaining_cents(self) -> int:
        return self.amount_cents - self.amount_refunded_cents


class Refund(Base):
    
    __tablename__ = "refunds"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    stripe_refund_id: Mapped[str] = mapped_column(
        String(100), 
        nullable=False, 
        unique=True, 
        index=True,
        doc="Stripe Refund ID"
    )
    
    idempotency_key: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        unique=True, 
        index=True,
        doc="Idempotency key for refund"
    )
    
    payment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), 
        ForeignKey("payments.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    amount_cents: Mapped[int] = mapped_column(
        Integer, 
        nullable=False,
        doc="Refund amount in cents"
    )
    
    reason: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        doc="Why refund was issued (e.g., service_not_provided, customer_request)"
    )
    
    status: Mapped[str] = mapped_column(
        String(50), 
        default=RefundStatus.PENDING.value, 
        nullable=False, 
        index=True
    )
    
    refund_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False, 
        index=True
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    
    succeeded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    payment: Mapped["Payment"] = relationship("Payment", back_populates="refunds", foreign_keys=[payment_id])
    
    __table_args__ = (
        Index('ix_refunds_payment_status', 'payment_id', 'status'),
    )
    
    def __repr__(self):
        return f"<Refund {self.id} ${self.amount_cents/100:.2f} {self.status}>"
    
    @property
    def amount_usd(self) -> float:
        return self.amount_cents / 100


class PaymentEvent(Base):
    
    __tablename__ = "payment_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    payment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), 
        ForeignKey("payments.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    stripe_event_id: Mapped[str | None] = mapped_column(
        String(100), 
        nullable=True, 
        unique=True, 
        index=True,
        doc="Stripe webhook event ID (for deduplication)"
    )
    
    event_type: Mapped[str] = mapped_column(
        String(100), 
        nullable=False, 
        index=True,
        doc="payment.created, payment.succeeded, refund.created, etc"
    )
    
    event_data: Mapped[dict] = mapped_column(
        JSON, 
        nullable=False,
        doc="Full Stripe event payload (or our event data)"
    )
    
    source: Mapped[str] = mapped_column(
        String(50), 
        default="api", 
        nullable=False,
        doc="api (our code) or webhook (from Stripe)"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False, 
        index=True
    )
    
    payment: Mapped["Payment"] = relationship("Payment", back_populates="events", foreign_keys=[payment_id])
    
    __table_args__ = (
        Index('ix_payment_events_payment_created', 'payment_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<PaymentEvent {self.event_type}>"


class Subscription(Base):
   
    __tablename__ = "subscriptions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    stripe_subscription_id: Mapped[str] = mapped_column(
        String(100), 
        nullable=False, 
        unique=True, 
        index=True
    )
    
    freelancer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), 
        ForeignKey("freelancer_profiles.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    status: Mapped[str] = mapped_column(
        String(50), 
        default=SubscriptionStatus.ACTIVE.value, 
        nullable=False, 
        index=True
    )
    
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(50), default="monthly", nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    freelancer: Mapped["FreelancerProfile"] = relationship("FreelancerProfile", foreign_keys=[freelancer_id])
    
    def __repr__(self):
        return f"<Subscription {self.id} {self.status}>"