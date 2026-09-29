"""
Tests for Diagnostic Centres, Diagnostic Tests, and Test Pricing.
"""
from fastapi import status


def test_create_diagnostic_test(client):
    payload = {
        "code": "LFT",
        "name": "Liver Function Test",
        "description": "Evaluates hepatic health.",
    }
    response = client.post("/api/v1/tests/", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["code"] == "LFT"
    assert data["name"] == "Liver Function Test"


def test_create_duplicate_test_code(client, sample_catalogue):
    payload = {
        "code": "CBC",
        "name": "Another CBC",
        "description": "Duplicate code test",
    }
    response = client.post("/api/v1/tests/", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response.json()["detail"].lower()


def test_list_diagnostic_tests(client, sample_catalogue):
    response = client.get("/api/v1/tests/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert any(t["code"] == "CBC" for t in data)


def test_create_diagnostic_centre_with_initial_tests(client, sample_catalogue):
    test_id = sample_catalogue["test"].id
    payload = {
        "name": "Max Healthcare - Koramangala",
        "location": "Koramangala, Bangalore",
        "contact_phone": "+91 80 9988 7766",
        "initial_tests": [
            {"test_id": test_id, "price": 499.00, "is_available": True}
        ],
    }
    response = client.post("/api/v1/centres/", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Max Healthcare - Koramangala"
    assert len(data["available_tests"]) == 1
    assert float(data["available_tests"][0]["price"]) == 499.00


def test_list_diagnostic_centres_filter_by_location(client, sample_catalogue):
    response = client.get("/api/v1/centres/?location=Indiranagar")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert "Indiranagar" in data[0]["location"]


def test_list_diagnostic_centres_filter_by_test_id(client, sample_catalogue):
    test_id = sample_catalogue["test"].id
    response = client.get(f"/api/v1/centres/?test_id={test_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert any(t["test_id"] == test_id for t in data[0]["available_tests"])


def test_add_or_update_centre_test_pricing(client, sample_catalogue):
    centre_id = sample_catalogue["centre"].id
    test_id = sample_catalogue["test"].id

    payload = {"test_id": test_id, "price": 550.00, "is_available": True}
    response = client.post(f"/api/v1/centres/{centre_id}/tests", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    test_item = next(t for t in data["available_tests"] if t["test_id"] == test_id)
    assert float(test_item["price"]) == 550.00
