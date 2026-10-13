class DummyStripeError(Exception):
    def __init__(self, message="Stripe error", user_message="Stripe error", code=None):
        super().__init__(message)
        self.user_message = user_message
        self.code = code


class DummyStripeModule:
    api_key = None
    api_version = None
    max_network_retries = None

    class error:
        StripeError = DummyStripeError
        InvalidRequestError = DummyStripeError
        AuthenticationError = DummyStripeError
        RateLimitError = DummyStripeError
        APIConnectionError = DummyStripeError
        CardError = DummyStripeError
        IdempotencyError = DummyStripeError
        SignatureVerificationError = DummyStripeError

    class PaymentIntent:
        @staticmethod
        def create(*args, **kwargs):
            raise DummyStripeError("Stripe SDK not installed")

        @staticmethod
        def confirm(*args, **kwargs):
            raise DummyStripeError("Stripe SDK not installed")

        @staticmethod
        def retrieve(*args, **kwargs):
            raise DummyStripeError("Stripe SDK not installed")

    class Refund:
        @staticmethod
        def create(*args, **kwargs):
            raise DummyStripeError("Stripe SDK not installed")

    class Webhook:
        @staticmethod
        def construct_event(*args, **kwargs):
            raise DummyStripeError("Stripe SDK not installed")

    class PaymentMethod:
        @staticmethod
        def retrieve(*args, **kwargs):
            raise DummyStripeError("Stripe SDK not installed")

    class checkout:
        class Session:
            @staticmethod
            def create(*args, **kwargs):
                mock_session = DummyStripeModule()
                mock_session.id = "cs_mock_12345"
                mock_session.url = "https://checkout.stripe.com/pay/cs_mock_12345"
                mock_session.payment_intent = "pi_mock_12345"
                mock_session.payment_status = "unpaid"
                return mock_session
    
try:
    import stripe
    from stripe import (
        StripeError,
        InvalidRequestError,
        AuthenticationError,
        RateLimitError,
        APIConnectionError,
        CardError,
    )
except ImportError:
    stripe = DummyStripeModule()
    StripeError = DummyStripeError
    InvalidRequestError = DummyStripeError
    AuthenticationError = DummyStripeError
    RateLimitError = DummyStripeError
    APIConnectionError = DummyStripeError
    CardError = DummyStripeError

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import uuid
from uuid import UUID
import logging
import hashlib
import hmac
import json
from typing import Optional, Dict, Any, Tuple

from app.core.config import settings
from app.core.errors import BusinessLogicException, ValidationException, ErrorCode
from app.models.payment import (
    Payment,
    Refund,
    PaymentEvent,
    PaymentStatus,
    RefundStatus,
)
from app.models.contract import Contract, ContractStatus
from app.models.users import User
from app.models.freelancer_profile import FreelancerProfile

logger = logging.getLogger(__name__)

if isinstance(stripe, DummyStripeModule):
    logger.warning("⚠️  [Stripe] Using DummyStripeModule (Stripe SDK package is NOT installed in Python environment).")
else:
    logger.info(f"✅ [Stripe] Real Stripe SDK initialized with secret key ({settings.STRIPE_SECRET_KEY[:8]}...).")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    stripe.api_version = settings.STRIPE_API_VERSION
    stripe.max_network_retries = settings.STRIPE_MAX_RETRIES

STRIPE_ERROR_MAP = {
    "card_declined": {
        "user_message": "Your card was declined. Please use a different card.",
        "category": "card_error",
        "action": "retry_with_different_card"
    },
    "insufficient_funds": {
        "user_message": "Insufficient funds. Please use a different card.",
        "category": "card_error",
        "action": "retry_with_different_card"
    },
    "lost_card": {
        "user_message": "Your card has been reported as lost.",
        "category": "card_error",
        "action": "contact_support"
    },
    "stolen_card": {
        "user_message": "Your card has been reported as stolen.",
        "category": "card_error",
        "action": "contact_support"
    },
    "expired_card": {
        "user_message": "Your card has expired. Please use a different card.",
        "category": "card_error",
        "action": "retry_with_different_card"
    },
    "incorrect_cvc": {
        "user_message": "Incorrect CVC. Please check and try again.",
        "category": "card_error",
        "action": "retry"
    },
    "incorrect_zip": {
        "user_message": "Incorrect zip code. Please check and try again.",
        "category": "card_error",
        "action": "retry"
    },
    "processing_error": {
        "user_message": "Processing error. Please try again.",
        "category": "processing_error",
        "action": "retry"
    },
    
    "authentication_required": {
        "user_message": "3D Secure authentication required. Please complete the authentication.",
        "category": "authentication",
        "action": "requires_3d_secure"
    },
    
    "rate_limit": {
        "user_message": "Too many requests. Please try again later.",
        "category": "api_error",
        "action": "retry_later"
    },
    "api_connection_error": {
        "user_message": "Connection error. Please try again.",
        "category": "network_error",
        "action": "retry"
    },
}

class StripePaymentService:
    
    @staticmethod
    def create_payment(
        db: Session,
        contract_id: UUID,
        client_id: UUID,
        freelancer_id: UUID,
        amount_cents: int,
        currency: str = "USD",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Payment:

        
        logger.info(
            f"Creating payment: ${amount_cents/100:.2f} {currency} "
            f"for contract {contract_id} from client {client_id}"
        )
        
        try:
            
            if amount_cents <= 0:
                raise BusinessLogicException(ErrorCode.INVALID_AMOUNT, "Amount must be greater than 0")
            
            if not currency or len(currency) != 3:
                raise BusinessLogicException(ErrorCode.INVALID_CURRENCY, "Invalid currency code")
            
            contract = db.query(Contract).filter(
                Contract.id == contract_id
            ).first()
            
            if not contract:
                raise BusinessLogicException(ErrorCode.CONTRACT_NOT_FOUND, "Contract not found")
            
            if contract.client_id != client_id:
                raise ValidationException(
                    ErrorCode.UNAUTHORIZED,
                    "Client is not authorized for this contract"
                )
            
            if contract.freelancer_id != freelancer_id:
                raise ValidationException(
                    ErrorCode.UNAUTHORIZED,
                    "Freelancer does not match contract"
                )
            
            if contract.status != ContractStatus.IN_PROGRESS:
                raise ValidationException(
                    ErrorCode.INVALID_CONTRACT_STATE,
                    f"Cannot pay contract in {contract.status} state"
                )
            
            logger.debug(f"Acquiring lock on contract {contract_id}")
            
            contract_locked = db.query(Contract).with_for_update(
                nowait=False,  
                skip_locked=False
            ).filter(
                Contract.id == contract_id
            ).first()
            
            if not contract_locked:
                raise BusinessLogicException(
                    ErrorCode.INTERNAL_ERROR,
                    "Failed to acquire contract lock"
                )
            
            existing_payment = db.query(Payment).filter(
                Payment.contract_id == contract_id,
                Payment.status.in_([
                    PaymentStatus.PENDING.value,
                    PaymentStatus.PROCESSING.value,
                    PaymentStatus.SUCCEEDED.value
                ])
            ).first()
            
            if existing_payment:
                logger.info(
                    f"Payment already exists for contract {contract_id}: "
                    f"{existing_payment.id} (status: {existing_payment.status})"
                )
                return existing_payment
            
            idempotency_key = StripePaymentService._generate_idempotency_key(
                contract_id, amount_cents, "payment_creation"
            )
            
            existing_by_key = db.query(Payment).filter(
                Payment.idempotency_key == idempotency_key
            ).first()
            
            if existing_by_key:
                logger.info(f"Payment with idempotency key exists: {existing_by_key.id}")
                return existing_by_key
            
            stripe_metadata = {
                "contract_id": str(contract_id),
                "client_id": str(client_id),
                "freelancer_id": str(freelancer_id),
                "marketplace": "freelancer-marketplace",
                **(metadata or {})
            }
            
            logger.info(f"Creating Stripe PaymentIntent: ${amount_cents/100:.2f} {currency}")
            
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                metadata=stripe_metadata,
                idempotency_key=idempotency_key,
                description=f"Payment for contract {contract_id}"
            )
            
            logger.info(f"Stripe PaymentIntent created: {intent.id} (status: {intent.status})")
            
            payment = Payment(
                stripe_payment_intent_id=intent.id,
                idempotency_key=idempotency_key,
                contract_id=contract_id,
                client_id=client_id,
                freelancer_id=freelancer_id,
                amount_cents=amount_cents,
                currency=currency,
                status=PaymentStatus.PENDING.value,
                stripe_status=intent.status,
                metadata=stripe_metadata,
                description=f"Payment for contract {contract_id}"
            )
            
            db.add(payment)
            db.flush()
            
            StripePaymentService._log_payment_event(
                db,
                payment.id,
                "payment.created",
                {
                    "stripe_intent_id": intent.id,
                    "amount": amount_cents,
                    "currency": currency,
                    "status": intent.status
                }
            )
            
            db.commit()
            db.refresh(payment)
            
            logger.info(f" Payment created successfully: {payment.id}")
            return payment
            
        except ValidationException:
            db.rollback()
            raise
        
        except stripe.error.IdempotencyError as e:
            logger.warning(f"Idempotency error (expected): {e.user_message}")
            db.rollback()
            
            try:
                existing = db.query(Payment).filter(
                    Payment.idempotency_key == idempotency_key
                ).first()
                if existing:
                    return existing
            except:
                pass
            
            raise BusinessLogicException(
                ErrorCode.PAYMENT_FAILED,
                f"Payment creation failed: {e.user_message}"
            )
        
        except stripe.error.StripeError as e:
            logger.error(f" Stripe error: {e.user_message}", exc_info=True)
            db.rollback()
            raise BusinessLogicException(
                ErrorCode.PAYMENT_FAILED,
                f"Payment creation failed: {e.user_message}"
            )
        
        except Exception as e:
            logger.error(f" Payment creation failed: {str(e)}", exc_info=True)
            db.rollback()
            raise BusinessLogicException(
                ErrorCode.INTERNAL_ERROR,
                f"Payment creation failed: {str(e)}"
            )
    
    @staticmethod
    def confirm_payment(
        db: Session,
        payment_id: UUID,
        payment_method_id: str
    ) -> Dict[str, Any]:
        
        logger.info(f"Confirming payment {payment_id}")
        
        try:
            
            payment = db.query(Payment).filter(
                Payment.id == payment_id
            ).first()
            
            if not payment:
                raise BusinessLogicException(ErrorCode.PAYMENT_NOT_FOUND, "Payment not found")
            
            if payment.status != PaymentStatus.PENDING.value:
                raise ValidationException(
                    ErrorCode.INVALID_PAYMENT_STATE,
                    f"Payment cannot be confirmed (status: {payment.status})"
                )
         
            logger.info(f"Submitting PaymentIntent {payment.stripe_payment_intent_id} to Stripe")
            
            intent = stripe.PaymentIntent.confirm(
                payment.stripe_payment_intent_id,
                payment_method=payment_method_id,
                off_session=False
            )
            
            logger.info(f"PaymentIntent confirmed: status={intent.status}")
                        
            payment.stripe_status = intent.status
            payment.payment_method_id = payment_method_id
            payment.payment_method_type = intent.payment_method.type if intent.payment_method else None
            
            # Extract card info if available
            if intent.payment_method and intent.payment_method.card:
                card = intent.payment_method.card
                payment.card_last_four = card.last4
                payment.card_brand = card.brand
            
            if intent.status == "succeeded":
                payment.status = PaymentStatus.SUCCEEDED.value
                payment.succeeded_at = datetime.now(timezone.utc)
                logger.info(f"Payment succeeded: {payment.id}")
                
            elif intent.status == "requires_action":
                logger.warning(f"Payment requires action (3D Secure): {payment.id}")
                
            elif intent.status == "processing":
                payment.status = PaymentStatus.PROCESSING.value
                logger.info(f"Payment processing: {payment.id}")
                
            elif intent.status in ["canceled", "requires_payment_method"]:
                payment.status = PaymentStatus.FAILED.value
                payment.failed_at = datetime.now(timezone.utc)
                
                if intent.last_payment_error:
                    error = intent.last_payment_error
                    payment.error_code = error.code
                    payment.error_message = error.message
                
                logger.error(f"Payment failed: {payment.id} - {payment.error_message}")
            
            db.commit()
            db.refresh(payment)
            
            StripePaymentService._log_payment_event(
                db,
                payment.id,
                "payment.confirmed",
                {
                    "stripe_status": intent.status,
                    "payment_status": payment.status
                }
            )

            
            return {
                "payment_id": str(payment.id),
                "stripe_intent_id": intent.id,
                "status": payment.status,
                "requires_action": intent.status == "requires_action",
                "client_secret": intent.client_secret if intent.status == "requires_action" else None,
                "card_last_four": payment.card_last_four,
                "card_brand": payment.card_brand
            }
            
        except ValidationException:
            raise
        
        except CardError as e:
            # Card was declined
            logger.error(f"Card declined: {e.user_message}")
            
            if 'payment' in locals():
                payment.status = PaymentStatus.FAILED.value
                payment.failed_at = datetime.now(timezone.utc)
                payment.error_code = e.code
                payment.error_message = e.user_message
                db.commit()
            
            error_info = STRIPE_ERROR_MAP.get(e.code, {})
            user_message = error_info.get("user_message", e.user_message)
            
            raise BusinessLogicException(ErrorCode.PAYMENT_FAILED, user_message)
        
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error during confirmation: {e.user_message}", exc_info=True)
            
            if 'payment' in locals():
                payment.status = PaymentStatus.FAILED.value
                payment.failed_at = datetime.now(timezone.utc)
                payment.error_code = getattr(e, 'code', 'stripe_error')
                payment.error_message = e.user_message
                db.commit()
            
            raise BusinessLogicException(ErrorCode.PAYMENT_FAILED, e.user_message)
        
        except Exception as e:
            logger.error(f"Confirmation failed: {str(e)}", exc_info=True)
            db.rollback()
            raise BusinessLogicException(
                ErrorCode.INTERNAL_ERROR,
                f"Payment confirmation failed: {str(e)}"
            )
    
    @staticmethod
    def create_refund(
        db: Session,
        payment_id: UUID,
        amount_cents: Optional[int] = None,
        reason: str = "requested_by_customer"
    ) -> Refund:
        
        logger.info(f"Creating refund for payment {payment_id} (amount: {amount_cents})")
        
        try:
            
            payment = db.query(Payment).filter(
                Payment.id == payment_id
            ).first()
            
            if not payment:
                raise BusinessLogicException(ErrorCode.PAYMENT_NOT_FOUND, "Payment not found")
            
            if payment.status != PaymentStatus.SUCCEEDED.value:
                raise ValidationException(
                    ErrorCode.INVALID_PAYMENT_STATE,
                    f"Can only refund succeeded payments (current: {payment.status})"
                )
            
            refund_amount = amount_cents or payment.amount_cents
            
            remaining_refundable = payment.amount_cents - payment.amount_refunded_cents
            if refund_amount > remaining_refundable:
                raise ValidationException(
                    ErrorCode.INVALID_AMOUNT,
                    f"Refund amount (${refund_amount/100:.2f}) exceeds available "
                    f"(${remaining_refundable/100:.2f})"
                )
            
            idempotency_key = StripePaymentService._generate_idempotency_key(
                payment_id, refund_amount, f"refund_{reason}"
            )
            
            existing_refund = db.query(Refund).filter(
                Refund.idempotency_key == idempotency_key
            ).first()
            
            if existing_refund:
                logger.info(f"Refund already exists: {existing_refund.id}")
                return existing_refund
            
            logger.info(
                f"Creating Stripe refund: ${refund_amount/100:.2f} "
                f"for PaymentIntent {payment.stripe_payment_intent_id}"
            )
            
            stripe_refund = stripe.Refund.create(
                payment_intent=payment.stripe_payment_intent_id,
                amount=refund_amount,
                metadata={"reason": reason},
                idempotency_key=idempotency_key
            )
            
            logger.info(f"Stripe refund created: {stripe_refund.id} (status: {stripe_refund.status})")

            refund = Refund(
                stripe_refund_id=stripe_refund.id,
                idempotency_key=idempotency_key,
                payment_id=payment_id,
                amount_cents=refund_amount,
                reason=reason,
                status=RefundStatus.PENDING.value if stripe_refund.status == "pending" else RefundStatus.SUCCEEDED.value
            )
            
            if stripe_refund.status == "succeeded":
                refund.succeeded_at = datetime.now(timezone.utc)
            
            db.add(refund)
            db.flush()
            
            payment.amount_refunded_cents += refund_amount
            payment.refunded_at = datetime.now(timezone.utc)
            
            if payment.amount_refunded_cents == payment.amount_cents:
                payment.status = PaymentStatus.REFUNDED.value
                logger.info(f"Payment fully refunded: {payment.id}")
            else:
                payment.status = PaymentStatus.PARTIALLY_REFUNDED.value
                logger.info(f"Payment partially refunded: {payment.id}")
            
            db.commit()
            db.refresh(refund)
            
            StripePaymentService._log_payment_event(
                db,
                payment.id,
                "refund.created",
                {
                    "stripe_refund_id": stripe_refund.id,
                    "amount": refund_amount,
                    "reason": reason,
                    "status": stripe_refund.status
                }
            )
            
            logger.info(f"Refund created: {refund.id}")
            return refund
            
        except ValidationException:
            raise
        
        except stripe.error.StripeError as e:
            logger.error(f"Stripe refund error: {e.user_message}", exc_info=True)
            db.rollback()
            raise BusinessLogicException(
                ErrorCode.REFUND_FAILED,
                f"Refund failed: {e.user_message}"
            )
        
    @staticmethod
    def create_checkout_session(
        db: Session,
        contract_id: UUID,
        client_id: UUID,
        freelancer_id: UUID,
        amount_cents: int,
        currency: str = "USD",
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info(
            f"Creating Stripe Checkout Session: ${amount_cents/100:.2f} {currency} "
            f"for contract {contract_id} from client {client_id}"
        )
        try:
            if amount_cents <= 0:
                raise BusinessLogicException(ErrorCode.INVALID_AMOUNT, "Amount must be greater than 0")
            if not currency or len(currency) != 3:
                raise BusinessLogicException(ErrorCode.INVALID_CURRENCY, "Invalid currency code")

            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            if not contract:
                raise BusinessLogicException(ErrorCode.CONTRACT_NOT_FOUND, "Contract not found")
            if contract.client_id != client_id:
                raise BusinessLogicException(ErrorCode.UNAUTHORIZED, "Client is not authorized for this contract")
            if contract.freelancer_id != freelancer_id:
                raise BusinessLogicException(ErrorCode.UNAUTHORIZED, "Freelancer does not match contract")
            if contract.status != ContractStatus.IN_PROGRESS:
                raise BusinessLogicException(ErrorCode.INVALID_CONTRACT_STATE, f"Cannot pay contract in {contract.status} state")

            idempotency_key = StripePaymentService._generate_idempotency_key(
                contract_id, amount_cents, "checkout_session"
            )

            payment = Payment(
                stripe_payment_intent_id=f"cs_pending_{uuid.uuid4().hex}",
                idempotency_key=idempotency_key,
                contract_id=contract_id,
                client_id=client_id,
                freelancer_id=freelancer_id,
                amount_cents=amount_cents,
                currency=currency,
                status=PaymentStatus.PENDING.value,
                description=f"Checkout session for contract {contract_id}"
            )
            db.add(payment)
            db.flush()

            default_success = f"http://localhost:8000/payments/success?session_id={{CHECKOUT_SESSION_ID}}"
            default_cancel = "http://localhost:8000/payments/cancel"

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": currency.lower(),
                        "product_data": {
                            "name": f"Payment for Contract {contract_id}",
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=success_url or default_success,
                cancel_url=cancel_url or default_cancel,
                metadata={
                    "contract_id": str(contract_id),
                    "client_id": str(client_id),
                    "freelancer_id": str(freelancer_id),
                    "payment_id": str(payment.id),
                },
                idempotency_key=idempotency_key,
            )

            session_id = str(getattr(session, "id", "cs_pending"))
            session_url = str(getattr(session, "url", ""))
            session_intent = getattr(session, "payment_intent", None)
            if session_intent is not None and not isinstance(session_intent, str):
                session_intent = str(session_intent)

            payment.stripe_payment_intent_id = session_intent or session_id
            payment.stripe_status = str(getattr(session, "payment_status", "unpaid"))
            db.commit()
            db.refresh(payment)

            StripePaymentService._log_payment_event(
                db, payment.id, "checkout.session.created", {"session_id": session_id, "url": session_url}
            )

            return {
                "payment_id": str(payment.id),
                "checkout_url": session_url,
                "session_id": session_id,
            }
        except BusinessLogicException:
            db.rollback()
            raise
        except Exception as e:
            logger.error(f"Checkout session creation failed: {str(e)}", exc_info=True)
            db.rollback()
            raise BusinessLogicException(ErrorCode.INTERNAL_ERROR, f"Checkout session creation failed: {str(e)}")

    @staticmethod
    def verify_webhook_signature(payload: bytes, signature: str) -> Dict[str, Any]:
        
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                settings.STRIPE_WEBHOOK_SECRET
            )
            logger.info(f"Webhook verified: {event['type']} id={event['id']}")
            return event
            
        except ValueError as e:
            logger.error(f"Webhook payload invalid: {str(e)}")
            raise BusinessLogicException(ErrorCode.INVALID_WEBHOOK, "Invalid webhook payload")
            
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            raise BusinessLogicException(ErrorCode.INVALID_WEBHOOK, "Invalid webhook signature")
    
    @staticmethod
    def process_webhook_event(db: Session, event: Dict[str, Any]) -> bool:
        
        event_type = event['type']
        stripe_event_id = event['id']
        
        logger.info(f"Processing webhook: {event_type} {stripe_event_id}")
        
        try:
          
            existing_event = db.query(PaymentEvent).filter(
                PaymentEvent.stripe_event_id == stripe_event_id
            ).first()
            
            if existing_event:
                logger.info(f"Webhook already processed: {stripe_event_id} (idempotent)")
                return True
            
            if event_type == "payment_intent.succeeded":
                return StripePaymentService._handle_payment_succeeded(db, event)
            
            elif event_type == "payment_intent.payment_failed":
                return StripePaymentService._handle_payment_failed(db, event)
            
            elif event_type == "charge.refunded":
                return StripePaymentService._handle_charge_refunded(db, event)
            
            elif event_type == "charge.dispute.created":
                return StripePaymentService._handle_dispute_created(db, event)
            
            elif event_type == "checkout.session.completed":
                return StripePaymentService._handle_checkout_session_completed(db, event)
            
            else:
                logger.warning(f"Unhandled event type: {event_type}")
                return True
            
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}", exc_info=True)
            db.rollback()
            return False

    @staticmethod
    def _handle_checkout_session_completed(db: Session, event: Dict[str, Any]) -> bool:
        session = event['data']['object']
        payment_id_str = session.get('metadata', {}).get('payment_id')
        logger.info(f"Handling checkout.session.completed for payment: {payment_id_str}")
        try:
            payment = None
            if payment_id_str:
                payment = db.query(Payment).filter(Payment.id == UUID(payment_id_str)).first()

            if payment:
                payment.status = PaymentStatus.SUCCEEDED.value
                payment.stripe_status = "succeeded"
                payment.succeeded_at = datetime.now(timezone.utc)
                if session.get('payment_intent'):
                    payment.stripe_payment_intent_id = session['payment_intent']
                db.commit()
                StripePaymentService._log_payment_event(
                    db, payment.id, "checkout.session.completed", session
                )
                logger.info(f"Payment succeeded via Checkout Session: {payment.id}")
            return True
        except Exception as e:
            logger.error(f"Checkout session completed handler error: {str(e)}", exc_info=True)
            db.rollback()
            return False
    
    @staticmethod
    def _handle_payment_succeeded(db: Session, event: Dict[str, Any]) -> bool:
        
        intent = event['data']['object']
        stripe_intent_id = intent['id']
        
        logger.info(f"Handling payment_intent.succeeded: {stripe_intent_id}")
        
        try:
            payment = db.query(Payment).filter(
                Payment.stripe_payment_intent_id == stripe_intent_id
            ).first()
            
            if not payment:
                logger.warning(f"Payment not found for intent: {stripe_intent_id}")
                return True
            
            payment.status = PaymentStatus.SUCCEEDED.value
            payment.stripe_status = intent['status']
            payment.succeeded_at = datetime.now(timezone.utc)
            
            if intent.get('payment_method'):
                try:
                    pm = stripe.PaymentMethod.retrieve(intent['payment_method'])
                    if pm.card:
                        payment.card_last_four = pm.card.last4
                        payment.card_brand = pm.card.brand
                except:
                    pass
            
            db.commit()
            
            StripePaymentService._log_payment_event(
                db, payment.id, "payment_intent.succeeded", intent
            )
            
            logger.info(f" Payment succeeded: {payment.id}")
            
            return True
            
        except Exception as e:
            logger.error(f" Payment succeeded handler error: {str(e)}", exc_info=True)
            db.rollback()
            return False
    
    @staticmethod
    def _handle_payment_failed(db: Session, event: Dict[str, Any]) -> bool:
        
        intent = event['data']['object']
        stripe_intent_id = intent['id']
        
        logger.warning(f"Handling payment_intent.payment_failed: {stripe_intent_id}")
        
        try:
            payment = db.query(Payment).filter(
                Payment.stripe_payment_intent_id == stripe_intent_id
            ).first()
            
            if not payment:
                logger.warning(f"Payment not found for intent: {stripe_intent_id}")
                return True
            
            payment.status = PaymentStatus.FAILED.value
            payment.stripe_status = intent['status']
            payment.failed_at = datetime.now(timezone.utc)
            
            if intent.get('last_payment_error'):
                error = intent['last_payment_error']
                payment.error_code = error.get('code')
                payment.error_message = error.get('message')
            
            db.commit()
            
            StripePaymentService._log_payment_event(
                db, payment.id, "payment_intent.payment_failed", intent
            )
            
            logger.error(f"Payment failed: {payment.id} - {payment.error_message}")
            
            
            return True
            
        except Exception as e:
            logger.error(f"Payment failed handler error: {str(e)}", exc_info=True)
            db.rollback()
            return False
    
    @staticmethod
    def _handle_charge_refunded(db: Session, event: Dict[str, Any]) -> bool:
        
        charge = event['data']['object']
        stripe_intent_id = charge.get('payment_intent')
        
        logger.info(f"Handling charge.refunded: {stripe_intent_id}")
        
        try:
            payment = db.query(Payment).filter(
                Payment.stripe_payment_intent_id == stripe_intent_id
            ).first()
            
            if not payment:
                logger.warning(f"Payment not found for charge: {charge['id']}")
                return True
            
            refunded_amount = charge.get('amount_refunded', 0)
            payment.amount_refunded_cents = refunded_amount
            
            if refunded_amount == payment.amount_cents:
                payment.status = PaymentStatus.REFUNDED.value
                logger.info(f"Payment fully refunded: {payment.id}")
            elif refunded_amount > 0:
                payment.status = PaymentStatus.PARTIALLY_REFUNDED.value
                logger.info(f"Payment partially refunded: {payment.id}")
            
            db.commit()
            
            StripePaymentService._log_payment_event(
                db, payment.id, "charge.refunded", charge
            )
            
            return True
            
        except Exception as e:
            logger.error(f" Charge refunded handler error: {str(e)}", exc_info=True)
            db.rollback()
            return False
    
    @staticmethod
    def _handle_dispute_created(db: Session, event: Dict[str, Any]) -> bool:
        
        dispute = event['data']['object']
        charge_id = dispute.get('charge')
        
        logger.error(f"  DISPUTE CREATED: {dispute['id']} for charge {charge_id}")
        
        return True
    

    @staticmethod
    def reconcile_pending_payments(db: Session, batch_size: int = 100) -> Dict[str, Any]:

        logger.info("🔄 Starting payment reconciliation job")
        
        stats = {
            "total_checked": 0,
            "updated_to_succeeded": 0,
            "updated_to_failed": 0,
            "still_pending": 0,
            "errors": 0
        }
        
        try:
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)
            
            pending_payments = db.query(Payment).filter(
                Payment.status == PaymentStatus.PENDING.value,
                Payment.created_at < cutoff_time
            ).limit(batch_size).all()
            
            logger.info(f"Found {len(pending_payments)} pending payments to reconcile")
            
            for payment in pending_payments:
                stats["total_checked"] += 1
                
                try:
                    logger.debug(f"Reconciling payment {payment.id}")
                    
                    # Query Stripe for current status
                    intent = stripe.PaymentIntent.retrieve(
                        payment.stripe_payment_intent_id
                    )
                    
                    local_status = payment.status
                    stripe_status = intent.status
                                        
                    if stripe_status == "succeeded" and local_status != PaymentStatus.SUCCEEDED.value:
                        logger.info(
                            f"Reconciliation: {payment.id} succeeded in Stripe "
                            f"but local is {local_status}"
                        )
                        
                        payment.status = PaymentStatus.SUCCEEDED.value
                        payment.stripe_status = stripe_status
                        payment.succeeded_at = datetime.now(timezone.utc)
                        
                        # Extract card info
                        if intent.payment_method and intent.payment_method.card:
                            payment.card_last_four = intent.payment_method.card.last4
                            payment.card_brand = intent.payment_method.card.brand
                        
                        db.commit()
                        stats["updated_to_succeeded"] += 1
                        logger.info(f" Reconciled to SUCCEEDED: {payment.id}")
                        
                    elif stripe_status in ["requires_payment_method", "canceled"] and local_status != PaymentStatus.FAILED.value:
                        logger.info(
                            f"Reconciliation: {payment.id} failed in Stripe "
                            f"but local is {local_status}"
                        )
                        
                        payment.status = PaymentStatus.FAILED.value
                        payment.stripe_status = stripe_status
                        payment.failed_at = datetime.now(timezone.utc)
                        
                        if intent.last_payment_error:
                            payment.error_code = intent.last_payment_error.code
                            payment.error_message = intent.last_payment_error.message
                        
                        db.commit()
                        stats["updated_to_failed"] += 1
                        logger.info(f" Reconciled to FAILED: {payment.id}")
                        
                    else:
                        stats["still_pending"] += 1
                        logger.debug(f"Payment still pending: {payment.id}")
                    
                except stripe.error.StripeError as e:
                    logger.error(
                        f"Reconciliation error for {payment.id}: {e.user_message}",
                        exc_info=True
                    )
                    stats["errors"] += 1
                    
                except Exception as e:
                    logger.error(
                        f"Reconciliation error for {payment.id}: {str(e)}",
                        exc_info=True
                    )
                    stats["errors"] += 1
                    db.rollback()
            
            logger.info(f" Reconciliation complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f" Reconciliation failed: {str(e)}", exc_info=True)
            db.rollback()
            raise
    
    @staticmethod
    def _generate_idempotency_key(
        resource_id: UUID,
        amount: int,
        action: str
    ) -> str:
        
        key_base = f"{resource_id}_{amount}_{action}"
        return hashlib.sha256(key_base.encode()).hexdigest()[:64]
    
    @staticmethod
    def _log_payment_event(
        db: Session,
        payment_id: UUID,
        event_type: str,
        event_data: Dict[str, Any],
        stripe_event_id: Optional[str] = None
    ) -> None:
        
        try:
            event = PaymentEvent(
                payment_id=payment_id,
                stripe_event_id=stripe_event_id,
                event_type=event_type,
                event_data=event_data,
                source="webhook" if stripe_event_id else "api"
            )
            db.add(event)
            db.commit()
            logger.debug(f"Logged event: {event_type} for payment {payment_id}")
            
        except Exception as e:
            logger.error(f"Failed to log payment event: {str(e)}", exc_info=True)
            db.rollback()
    
    @staticmethod
    def get_payment_details(db: Session, payment_id: UUID) -> Dict[str, Any]:
        
        payment = db.query(Payment).filter(
            Payment.id == payment_id
        ).first()
        
        if not payment:
            raise ValidationException(ErrorCode.PAYMENT_NOT_FOUND, "Payment not found")
        
        return {
            "id": str(payment.id),
            "amount": payment.amount_usd,
            "currency": payment.currency,
            "status": payment.status,
            "stripe_status": payment.stripe_status,
            "card_last_four": payment.card_last_four,
            "card_brand": payment.card_brand,
            "created_at": payment.created_at.isoformat(),
            "succeeded_at": payment.succeeded_at.isoformat() if payment.succeeded_at else None,
            "failed_at": payment.failed_at.isoformat() if payment.failed_at else None,
            "error_message": payment.error_message
        }
    
    @staticmethod
    def get_payment_history(
        db: Session,
        contract_id: UUID,
        limit: int = 50
    ) -> list[Dict[str, Any]]:
        
        payments = db.query(Payment).filter(
            Payment.contract_id == contract_id
        ).order_by(
            Payment.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": str(p.id),
                "amount": p.amount_usd,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
                "succeeded_at": p.succeeded_at.isoformat() if p.succeeded_at else None
            }
            for p in payments
        ]