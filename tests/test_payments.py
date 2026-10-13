import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone
import json

from app.models.users import User
from app.models.contract import Contract, ContractStatus
from app.models.payment import Payment, PaymentStatus, RefundStatus
from app.services.stripe_payment import StripePaymentService
from app.dependencies.auth import get_current_user, get_current_client_user
from app.main import app


@pytest.fixture
def mock_contract(db_session, client_user, freelancer_user):
    contract = Contract(
        id=uuid4(),
        job_id=uuid4(),
        proposal_id=uuid4(),
        client_id=client_user.id,
        freelancer_id=freelancer_user.id,
        title="Payment Test Contract",
        total_amount=500.0,
        amount_paid=0.0,
        status=ContractStatus.IN_PROGRESS,
        start_date=datetime.now(timezone.utc)
    )
    db_session.add(contract)
    db_session.commit()
    db_session.refresh(contract)
    return contract


# ============================================================================
# UNIT TESTS FOR StripePaymentService
# ============================================================================

def test_create_payment_service_success(db_session, mock_contract):
    mock_intent = MagicMock()
    mock_intent.id = "pi_mock_12345"
    mock_intent.status = "requires_payment_method"

    with patch("app.services.stripe_payment.stripe.PaymentIntent.create", return_value=mock_intent):
        payment = StripePaymentService.create_payment(
            db=db_session,
            contract_id=mock_contract.id,
            client_id=mock_contract.client_id,
            freelancer_id=mock_contract.freelancer_id,
            amount_cents=50000,
            currency="USD"
        )

        assert payment is not None
        assert payment.stripe_payment_intent_id == "pi_mock_12345"
        assert payment.amount_cents == 50000
        assert payment.status == PaymentStatus.PENDING.value


def test_create_payment_invalid_amount(db_session, mock_contract):
    with pytest.raises(Exception) as exc_info:
        StripePaymentService.create_payment(
            db=db_session,
            contract_id=mock_contract.id,
            client_id=mock_contract.client_id,
            freelancer_id=mock_contract.freelancer_id,
            amount_cents=0,
            currency="USD"
        )
    assert "greater than 0" in str(getattr(exc_info.value, "message", exc_info.value))


def test_confirm_payment_service_success(db_session, mock_contract):
    mock_intent = MagicMock()
    mock_intent.id = "pi_mock_12345"
    mock_intent.status = "succeeded"
    mock_intent.payment_method = MagicMock()
    mock_intent.payment_method.type = "card"
    mock_intent.payment_method.card = MagicMock(last4="4242", brand="visa")

    with patch("app.services.stripe_payment.stripe.PaymentIntent.create", return_value=mock_intent):
        payment = StripePaymentService.create_payment(
            db=db_session,
            contract_id=mock_contract.id,
            client_id=mock_contract.client_id,
            freelancer_id=mock_contract.freelancer_id,
            amount_cents=50000
        )

    with patch("app.services.stripe_payment.stripe.PaymentIntent.confirm", return_value=mock_intent):
        result = StripePaymentService.confirm_payment(
            db=db_session,
            payment_id=payment.id,
            payment_method_id="pm_mock_card_visa"
        )

        assert result["status"] == PaymentStatus.SUCCEEDED.value
        assert result["card_last_four"] == "4242"
        assert result["card_brand"] == "visa"


def test_create_refund_service_success(db_session, mock_contract):
    mock_intent = MagicMock()
    mock_intent.id = "pi_mock_12345"
    mock_intent.status = "succeeded"
    mock_intent.payment_method = None

    with patch("app.services.stripe_payment.stripe.PaymentIntent.create", return_value=mock_intent):
        payment = StripePaymentService.create_payment(
            db=db_session,
            contract_id=mock_contract.id,
            client_id=mock_contract.client_id,
            freelancer_id=mock_contract.freelancer_id,
            amount_cents=50000
        )

    with patch("app.services.stripe_payment.stripe.PaymentIntent.confirm", return_value=mock_intent):
        StripePaymentService.confirm_payment(
            db=db_session,
            payment_id=payment.id,
            payment_method_id="pm_mock_card_visa"
        )

    mock_refund = MagicMock()
    mock_refund.id = "re_mock_12345"
    mock_refund.status = "succeeded"

    with patch("app.services.stripe_payment.stripe.Refund.create", return_value=mock_refund):
        refund = StripePaymentService.create_refund(
            db=db_session,
            payment_id=payment.id,
            amount_cents=50000,
            reason="requested_by_customer"
        )

        assert refund is not None
        assert refund.stripe_refund_id == "re_mock_12345"
        assert refund.amount_cents == 50000
        assert refund.status == RefundStatus.SUCCEEDED.value


def test_webhook_verification(db_session):
    mock_event = {"id": "evt_test123", "type": "payment_intent.succeeded"}
    with patch("app.services.stripe_payment.stripe.Webhook.construct_event", return_value=mock_event):
        event = StripePaymentService.verify_webhook_signature(b"dummy payload", "dummy_sig")
        assert event["id"] == "evt_test123"


# ============================================================================
# INTEGRATION TESTS FOR API ENDPOINTS
# ============================================================================

def test_api_create_payment_intent(client, client_user, mock_contract):
    app.dependency_overrides[get_current_client_user] = lambda: client_user

    mock_intent = MagicMock()
    mock_intent.id = "pi_api_test_123"
    mock_intent.status = "requires_payment_method"

    with patch("app.services.stripe_payment.stripe.PaymentIntent.create", return_value=mock_intent):
        response = client.post(
            "/payments/intents",
            json={
                "contract_id": str(mock_contract.id),
                "amount_cents": 25000,
                "currency": "USD"
            }
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    data = response.json()
    assert data["amount_cents"] == 25000
    assert data["stripe_payment_intent_id"] == "pi_api_test_123"


def test_api_confirm_payment(client, client_user, mock_contract):
    app.dependency_overrides[get_current_client_user] = lambda: client_user
    app.dependency_overrides[get_current_user] = lambda: client_user

    mock_intent = MagicMock()
    mock_intent.id = "pi_api_test_456"
    mock_intent.status = "succeeded"
    mock_intent.payment_method = MagicMock()
    mock_intent.payment_method.type = "card"
    mock_intent.payment_method.card = MagicMock(last4="1234", brand="mastercard")

    with patch("app.services.stripe_payment.stripe.PaymentIntent.create", return_value=mock_intent):
        res_create = client.post(
            "/payments/intents",
            json={
                "contract_id": str(mock_contract.id),
                "amount_cents": 10000,
                "currency": "USD"
            }
        )
    payment_id = res_create.json()["id"]

    with patch("app.services.stripe_payment.stripe.PaymentIntent.confirm", return_value=mock_intent):
        res_confirm = client.post(
            f"/payments/{payment_id}/confirm",
            json={"payment_method_id": "pm_mock_card_mastercard"}
        )

    app.dependency_overrides.clear()
    assert res_confirm.status_code == 200
    data = res_confirm.json()
    assert data["status"] == "succeeded"
    assert data["card_last_four"] == "1234"


def test_api_get_payment_details(client, client_user, mock_contract):
    app.dependency_overrides[get_current_client_user] = lambda: client_user
    app.dependency_overrides[get_current_user] = lambda: client_user

    mock_intent = MagicMock()
    mock_intent.id = "pi_api_details"
    mock_intent.status = "requires_payment_method"

    with patch("app.services.stripe_payment.stripe.PaymentIntent.create", return_value=mock_intent):
        res_create = client.post(
            "/payments/intents",
            json={
                "contract_id": str(mock_contract.id),
                "amount_cents": 15000,
                "currency": "USD"
            }
        )
    payment_id = res_create.json()["id"]

    res_get = client.get(f"/payments/{payment_id}")
    app.dependency_overrides.clear()

    assert res_get.status_code == 200
    data = res_get.json()
    assert data["id"] == payment_id
    assert data["amount"] == 150.0


def test_api_webhook_endpoint(client):
    mock_event = {
        "id": "evt_webhook_test_1",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_non_existent",
                "status": "succeeded"
            }
        }
    }

    with patch("app.services.stripe_payment.stripe.Webhook.construct_event", return_value=mock_event):
        response = client.post(
            "/payments/webhook",
            content=json.dumps(mock_event),
            headers={"Stripe-Signature": "t=123,v1=mock_sig"}
        )

    assert response.status_code == 200
    assert response.json() == {"status": "success"}


def test_api_create_checkout_session(client, client_user, mock_contract):
    app.dependency_overrides[get_current_client_user] = lambda: client_user

    mock_session = MagicMock()
    mock_session.id = "cs_test_session_999"
    mock_session.url = "https://checkout.stripe.com/pay/cs_test_session_999"
    mock_session.payment_intent = "pi_session_999"

    with patch("app.services.stripe_payment.stripe.checkout.Session.create", return_value=mock_session):
        response = client.post(
            "/payments/checkout-session",
            json={
                "contract_id": str(mock_contract.id),
                "amount_cents": 5000,
                "currency": "USD"
            }
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    data = response.json()
    assert data["session_id"] == "cs_test_session_999"
    assert data["checkout_url"] == "https://checkout.stripe.com/pay/cs_test_session_999"


def test_payment_success_landing(client):
    response = client.get("/payments/success?session_id=cs_test_123")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["session_id"] == "cs_test_123"


def test_payment_cancel_landing(client):
    response = client.get("/payments/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


