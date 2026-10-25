"""Synthetic order lookup API tests."""

from fastapi.testclient import TestClient

MATCHING = {"order_id": "SF-1001", "customer_email": "alex.rivera@example.com"}
WRONG_EMAIL = {"order_id": "SF-1001", "customer_email": "nobody@example.com"}
NONEXISTENT = {"order_id": "SF-DOES-NOT-EXIST", "customer_email": "alex.rivera@example.com"}


def test_matching_order_returns_simulated_details(client: TestClient) -> None:
    response = client.post("/api/v1/demo/order-lookups", json=MATCHING)
    assert response.status_code == 200
    body = response.json()
    assert body["order_id"] == "SF-1001"
    assert body["status"] == "Processing"
    assert body["is_simulated"] is True
    assert "last_update" in body
    # Must not leak customer PII or internal IDs
    assert "email" not in body
    assert "full_name" not in body
    assert "customer" not in body
    assert "id" not in body
    assert "notes" not in body


def test_wrong_email_and_nonexistent_order_same_public_error(client: TestClient) -> None:
    wrong = client.post("/api/v1/demo/order-lookups", json=WRONG_EMAIL)
    missing = client.post("/api/v1/demo/order-lookups", json=NONEXISTENT)
    assert wrong.status_code == 404
    assert missing.status_code == 404
    assert wrong.json() == missing.json()
    assert wrong.json()["detail"]["code"] == "order_not_found"


def test_invalid_input_rejected(client: TestClient) -> None:
    missing_email = client.post(
        "/api/v1/demo/order-lookups",
        json={"order_id": "SF-1001"},
    )
    assert missing_email.status_code == 422
    assert missing_email.json()["detail"]["code"] == "validation_error"

    blank_order = client.post(
        "/api/v1/demo/order-lookups",
        json={"order_id": "   ", "customer_email": "alex.rivera@example.com"},
    )
    assert blank_order.status_code == 422

    bad_email = client.post(
        "/api/v1/demo/order-lookups",
        json={"order_id": "SF-1001", "customer_email": "not-an-email"},
    )
    assert bad_email.status_code == 422


def test_email_matching_is_case_insensitive(client: TestClient) -> None:
    response = client.post(
        "/api/v1/demo/order-lookups",
        json={
            "order_id": "SF-1001",
            "customer_email": "Alex.Rivera@Example.com",
        },
    )
    assert response.status_code == 200
    assert response.json()["order_id"] == "SF-1001"
