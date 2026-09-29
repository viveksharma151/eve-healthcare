"""
Unit and integration tests for authentication (Signup, Login, Profile).
"""
import pytest
from fastapi import status


def test_signup_success(client):
    payload = {
        "email": "newpatient@test.com",
        "full_name": "New Patient",
        "password": "strongpassword123",
    }
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newpatient@test.com"
    assert data["user"]["full_name"] == "New Patient"


def test_signup_duplicate_email(client, test_user):
    payload = {
        "email": test_user.email,
        "full_name": "Another User",
        "password": "password123",
    }
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response.json()["detail"].lower()


def test_signup_validation_short_password(client):
    payload = {
        "email": "short@test.com",
        "full_name": "Short Pass",
        "password": "123",  # less than 6 chars
    }
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 422



def test_login_success(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "password123"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == test_user.email


def test_login_invalid_password(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "wrongpassword"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_nonexistent_email(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@test.com", "password": "password123"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_profile(client, user_headers):
    response = client.get("/api/v1/auth/me", headers=user_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "patient@test.com"


def test_get_profile_unauthorized(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
