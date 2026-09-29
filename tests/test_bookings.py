"""
Tests for Booking System: appointment scheduling, validation, authorization, and lifecycle.
"""
from datetime import datetime, timedelta, timezone
from fastapi import status


def test_create_booking_success(client, user_headers, sample_catalogue):
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    centre_id = sample_catalogue["centre"].id
    test_id = sample_catalogue["test"].id

    payload = {
        "centre_id": centre_id,
        "test_id": test_id,
        "appointment_datetime": future_time,
        "notes": "Routine checkup",
    }
    response = client.post("/api/v1/bookings/", json=payload, headers=user_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "PENDING"
    assert data["booking_reference"].startswith("BK-")
    assert float(data["amount"]) == 450.00
    assert data["centre_name"] == "Apollo Diagnostic Lab"
    assert data["test_name"] == "Complete Blood Count"


def test_booking_past_datetime_rejected(client, user_headers, sample_catalogue):
    past_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    payload = {
        "centre_id": sample_catalogue["centre"].id,
        "test_id": sample_catalogue["test"].id,
        "appointment_datetime": past_time,
    }
    response = client.post("/api/v1/bookings/", json=payload, headers=user_headers)
    assert response.status_code == 422



def test_booking_invalid_centre(client, user_headers, sample_catalogue):
    future_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    payload = {
        "centre_id": 99999,
        "test_id": sample_catalogue["test"].id,
        "appointment_datetime": future_time,
    }
    response = client.post("/api/v1/bookings/", json=payload, headers=user_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_booking_test_not_offered_by_centre(client, user_headers, sample_catalogue):
    # Create another test not attached to this centre
    create_res = client.post(
        "/api/v1/tests/",
        json={"code": "COVID", "name": "RT-PCR Test"},
    )
    new_test_id = create_res.json()["id"]

    future_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    payload = {
        "centre_id": sample_catalogue["centre"].id,
        "test_id": new_test_id,
        "appointment_datetime": future_time,
    }
    response = client.post("/api/v1/bookings/", json=payload, headers=user_headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "not currently available" in response.json()["detail"].lower()


def test_authorization_user_cannot_view_others_booking(client, user_headers, other_headers, sample_catalogue):
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    # User A creates a booking
    create_res = client.post(
        "/api/v1/bookings/",
        json={
            "centre_id": sample_catalogue["centre"].id,
            "test_id": sample_catalogue["test"].id,
            "appointment_datetime": future_time,
        },
        headers=user_headers,
    )
    booking_id = create_res.json()["id"]

    # User B attempts to access User A's booking
    view_res = client.get(f"/api/v1/bookings/{booking_id}", headers=other_headers)
    assert view_res.status_code == status.HTTP_403_FORBIDDEN


def test_cancel_booking_success(client, user_headers, sample_catalogue):
    future_time = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    create_res = client.post(
        "/api/v1/bookings/",
        json={
            "centre_id": sample_catalogue["centre"].id,
            "test_id": sample_catalogue["test"].id,
            "appointment_datetime": future_time,
        },
        headers=user_headers,
    )
    booking_id = create_res.json()["id"]

    cancel_res = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=user_headers)
    assert cancel_res.status_code == status.HTTP_200_OK
    assert cancel_res.json()["status"] == "CANCELLED"

    # Repeated cancellation should fail
    repeat_res = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=user_headers)
    assert repeat_res.status_code == status.HTTP_400_BAD_REQUEST


def test_unauthorized_user_cannot_cancel_others_booking(client, user_headers, other_headers, sample_catalogue):
    future_time = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    create_res = client.post(
        "/api/v1/bookings/",
        json={
            "centre_id": sample_catalogue["centre"].id,
            "test_id": sample_catalogue["test"].id,
            "appointment_datetime": future_time,
        },
        headers=user_headers,
    )
    booking_id = create_res.json()["id"]

    cancel_res = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=other_headers)
    assert cancel_res.status_code == status.HTTP_403_FORBIDDEN
