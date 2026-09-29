"""
Tests for Simulated Payments and Idempotent Webhook Processing.
"""
from datetime import datetime, timedelta, timezone
from fastapi import status


def _create_pending_booking(client, user_headers, sample_catalogue):
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    res = client.post(
        "/api/v1/bookings/",
        json={
            "centre_id": sample_catalogue["centre"].id,
            "test_id": sample_catalogue["test"].id,
            "appointment_datetime": future_time,
        },
        headers=user_headers,
    )
    return res.json()


def test_simulate_payment_success(client, user_headers, sample_catalogue):
    booking = _create_pending_booking(client, user_headers, sample_catalogue)
    booking_id = booking["id"]

    payload = {
        "booking_id": booking_id,
        "simulate_status": "SUCCESS",
    }
    response = client.post("/payments/", json=payload, headers=user_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["booking_status"] == "CONFIRMED"
    assert data["payment_reference"].startswith("PAY-")

    # Verify booking status changed to CONFIRMED in DB
    booking_res = client.get(f"/api/v1/bookings/{booking_id}", headers=user_headers)
    assert booking_res.json()["status"] == "CONFIRMED"


def test_simulate_payment_failure(client, user_headers, sample_catalogue):
    booking = _create_pending_booking(client, user_headers, sample_catalogue)
    booking_id = booking["id"]

    payload = {
        "booking_id": booking_id,
        "simulate_status": "FAILED",
    }
    response = client.post("/payments/", json=payload, headers=user_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "FAILED"
    assert data["booking_status"] == "FAILED"

    booking_res = client.get(f"/api/v1/bookings/{booking_id}", headers=user_headers)
    assert booking_res.json()["status"] == "FAILED"


def test_simulate_payment_unauthorized_user(client, user_headers, other_headers, sample_catalogue):
    booking = _create_pending_booking(client, user_headers, sample_catalogue)
    booking_id = booking["id"]

    payload = {"booking_id": booking_id, "simulate_status": "SUCCESS"}
    response = client.post("/payments/", json=payload, headers=other_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_cannot_pay_for_already_confirmed_booking(client, user_headers, sample_catalogue):
    booking = _create_pending_booking(client, user_headers, sample_catalogue)
    booking_id = booking["id"]

    # First payment succeeds
    client.post("/payments/", json={"booking_id": booking_id, "simulate_status": "SUCCESS"}, headers=user_headers)

    # Second payment attempt on same booking
    res = client.post("/payments/", json={"booking_id": booking_id, "simulate_status": "SUCCESS"}, headers=user_headers)
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "already been confirmed" in res.json()["detail"].lower()


def test_cannot_pay_for_cancelled_booking(client, user_headers, sample_catalogue):
    booking = _create_pending_booking(client, user_headers, sample_catalogue)
    booking_id = booking["id"]

    # Cancel booking
    client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=user_headers)

    # Attempt payment
    res = client.post("/payments/", json={"booking_id": booking_id, "simulate_status": "SUCCESS"}, headers=user_headers)
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "cancelled booking" in res.json()["detail"].lower()


def test_webhook_payment_success_confirms_booking(client, user_headers, sample_catalogue):
    booking = _create_pending_booking(client, user_headers, sample_catalogue)
    booking_id = booking["id"]

    payload = {
        "event_id": "evt_test_1001",
        "event_type": "payment.succeeded",
        "booking_id": booking_id,
        "amount": float(booking["amount"]),
        "status": "SUCCESS",
        "provider_transaction_id": "txn_mock_001",
    }
    response = client.post("/payments/webhook/", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "processed"
    assert data["booking_status"] == "CONFIRMED"

    booking_res = client.get(f"/api/v1/bookings/{booking_id}", headers=user_headers)
    assert booking_res.json()["status"] == "CONFIRMED"


def test_webhook_idempotency_same_event_delivered_multiple_times(client, user_headers, sample_catalogue, db_session):
    from app.models.payment import Payment

    booking = _create_pending_booking(client, user_headers, sample_catalogue)
    booking_id = booking["id"]

    payload = {
        "event_id": "evt_idempotency_unique_999",
        "event_type": "payment.succeeded",
        "booking_id": booking_id,
        "amount": float(booking["amount"]),
        "status": "SUCCESS",
        "provider_transaction_id": "txn_idem_001",
    }

    # First delivery
    first_res = client.post("/payments/webhook/", json=payload)
    assert first_res.status_code == status.HTTP_200_OK
    assert first_res.json()["status"] == "processed"

    # Second delivery with identical event_id
    second_res = client.post("/payments/webhook/", json=payload)
    assert second_res.status_code == status.HTTP_200_OK
    assert second_res.json()["status"] == "already_processed"
    assert second_res.json()["booking_status"] == "CONFIRMED"

    # Third delivery
    third_res = client.post("/payments/webhook/", json=payload)
    assert third_res.status_code == status.HTTP_200_OK
    assert third_res.json()["status"] == "already_processed"

    # Verify no duplicate payment records were created in database
    payment_records = db_session.query(Payment).filter(Payment.booking_id == booking_id).all()
    assert len(payment_records) == 1


def test_webhook_amount_mismatch_rejected(client, user_headers, sample_catalogue):
    booking = _create_pending_booking(client, user_headers, sample_catalogue)
    booking_id = booking["id"]

    payload = {
        "event_id": "evt_mismatch_999",
        "event_type": "payment.succeeded",
        "booking_id": booking_id,
        "amount": 99999.00,  # doesn't match booking amount
        "status": "SUCCESS",
    }
    response = client.post("/payments/webhook/", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "amount mismatch" in response.json()["detail"].lower()


def test_webhook_invalid_booking_id(client):
    payload = {
        "event_id": "evt_invalid_booking_404",
        "event_type": "payment.succeeded",
        "booking_id": 999999,
        "amount": 450.00,
        "status": "SUCCESS",
    }
    response = client.post("/payments/webhook/", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
