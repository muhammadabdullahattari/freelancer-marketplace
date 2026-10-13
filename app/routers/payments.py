from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
import logging

from app.database import get_db
from app.dependencies.auth import get_current_user, get_current_client_user
from app.models.users import User
from app.models.contract import Contract
from app.models.payment import Payment
from app.services.stripe_payment import StripePaymentService
from app.schemas.payment import (
    PaymentCreateRequest,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    PaymentConfirmRequest,
    RefundCreateRequest,
    PaymentResponse,
    PaymentConfirmResponse,
    RefundResponse,
    PaymentHistoryItem,
)
from app.core.errors import ValidationException, BusinessLogicException, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/success")
def payment_success_landing(session_id: Optional[str] = None):
    """
    Public landing page redirect from Stripe Checkout after payment success.
    """
    return {
        "message": "Payment completed successfully! Thank you.",
        "session_id": session_id,
        "status": "success"
    }


@router.get("/cancel")
def payment_cancel_landing():
    """
    Public landing page redirect from Stripe Checkout when payment is cancelled.
    """
    return {
        "message": "Payment was cancelled. You can try again.",
        "status": "cancelled"
    }


@router.post("/checkout-session", response_model=CheckoutSessionResponse, status_code=status.HTTP_201_CREATED)
def create_checkout_session(
    payload: CheckoutSessionRequest,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Hosted Checkout Session URL. Open the returned checkout_url in a browser to enter test card details. (Client only)
    """
    contract = db.query(Contract).filter(Contract.id == payload.contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )
    if contract.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to create payment for this contract"
        )

    try:
        result = StripePaymentService.create_checkout_session(
            db=db,
            contract_id=payload.contract_id,
            client_id=current_user.id,
            freelancer_id=contract.freelancer_id,
            amount_cents=payload.amount_cents,
            currency=payload.currency,
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
        )
        return CheckoutSessionResponse(**result)
    except ValidationException as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ve.message)
    except BusinessLogicException as ble:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ble.message)


@router.post("/intents", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment_intent(
    payload: PaymentCreateRequest,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe PaymentIntent for a contract. (Client only)
    """
    contract = db.query(Contract).filter(Contract.id == payload.contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )
    if contract.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to create payment for this contract"
        )

    try:
        payment = StripePaymentService.create_payment(
            db=db,
            contract_id=payload.contract_id,
            client_id=current_user.id,
            freelancer_id=contract.freelancer_id,
            amount_cents=payload.amount_cents,
            currency=payload.currency,
            metadata=payload.metadata,
        )
        return payment
    except ValidationException as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ve.message)
    except BusinessLogicException as ble:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ble.message)


@router.post("/{payment_id}/confirm", response_model=PaymentConfirmResponse)
def confirm_payment(
    payment_id: UUID,
    payload: PaymentConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Confirm a Stripe PaymentIntent with payment_method_id.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    if payment.client_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to confirm this payment"
        )

    try:
        result = StripePaymentService.confirm_payment(
            db=db,
            payment_id=payment_id,
            payment_method_id=payload.payment_method_id
        )
        return PaymentConfirmResponse(**result)
    except ValidationException as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ve.message)
    except BusinessLogicException as ble:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ble.message)


@router.post("/{payment_id}/refund", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
def refund_payment(
    payment_id: UUID,
    payload: RefundCreateRequest,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db),
):
    """
    Create a refund for a succeeded payment. (Client or Admin)
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    if payment.client_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to request refund for this payment"
        )

    try:
        refund = StripePaymentService.create_refund(
            db=db,
            payment_id=payment_id,
            amount_cents=payload.amount_cents,
            reason=payload.reason
        )
        return refund
    except ValidationException as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ve.message)
    except BusinessLogicException as ble:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ble.message)


@router.get("/{payment_id}")
def get_payment_details(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get details of a specific payment.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    if payment.client_id != current_user.id and payment.freelancer_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this payment"
        )

    try:
        return StripePaymentService.get_payment_details(db=db, payment_id=payment_id)
    except ValidationException as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ve.message)


@router.get("/contract/{contract_id}", response_model=List[PaymentHistoryItem])
def get_contract_payment_history(
    contract_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get payment history for a contract.
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )
    if contract.client_id != current_user.id and contract.freelancer_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view payment history for this contract"
        )

    history = StripePaymentService.get_payment_history(db=db, contract_id=contract_id)
    return history


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
):
    """
    Stripe Webhook Endpoint. Unauthenticated; signature-verified.
    """
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header"
        )

    payload = await request.body()
    try:
        event = StripePaymentService.verify_webhook_signature(payload, stripe_signature)
        success = StripePaymentService.process_webhook_event(db, event)
        if not success:
            logger.warning(f"Webhook event processing returned false: {event.get('id')}")
            return {"status": "event_processing_warning"}
        return {"status": "success"}
    except ValidationException as ve:
        logger.error(f"Webhook validation error: {ve.message}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ve.message)
    except Exception as e:
        logger.error(f"Webhook unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook handler internal error"
        )
