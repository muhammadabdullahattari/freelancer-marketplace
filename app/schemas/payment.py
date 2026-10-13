from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class PaymentCreateRequest(BaseModel):
    contract_id: UUID
    amount_cents: int = Field(..., gt=0, description="Amount in cents (e.g. 1000 = $10.00)")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    metadata: Optional[Dict[str, Any]] = None


class CheckoutSessionRequest(BaseModel):
    contract_id: UUID
    amount_cents: int = Field(..., gt=0, description="Amount in cents (e.g. 5000 = $50.00)")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    success_url: Optional[str] = Field(default=None, description="URL to redirect after payment success")
    cancel_url: Optional[str] = Field(default=None, description="URL to redirect if user cancels")


class CheckoutSessionResponse(BaseModel):
    payment_id: str
    checkout_url: str
    session_id: str


class PaymentConfirmRequest(BaseModel):
    payment_method_id: str = Field(..., min_length=1, description="Stripe PaymentMethod ID (pm_...)")


class RefundCreateRequest(BaseModel):
    amount_cents: Optional[int] = Field(default=None, gt=0, description="Amount in cents to refund. Null for full refund.")
    reason: str = Field(default="requested_by_customer", description="Reason for refund")


class PaymentResponse(BaseModel):
    id: UUID
    contract_id: UUID
    client_id: UUID
    freelancer_id: UUID
    amount_cents: int
    amount_usd: float
    currency: str
    status: str
    stripe_status: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    card_last_four: Optional[str] = None
    card_brand: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    succeeded_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentConfirmResponse(BaseModel):
    payment_id: str
    stripe_intent_id: str
    status: str
    requires_action: bool
    client_secret: Optional[str] = None
    card_last_four: Optional[str] = None
    card_brand: Optional[str] = None


class RefundResponse(BaseModel):
    id: UUID
    payment_id: UUID
    stripe_refund_id: Optional[str] = None
    amount_cents: int
    reason: str
    status: str
    created_at: datetime
    succeeded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentHistoryItem(BaseModel):
    id: str
    amount: float
    status: str
    created_at: str
    succeeded_at: Optional[str] = None
