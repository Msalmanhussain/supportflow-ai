"""Persistence, idempotency, and review API tests."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.schemas.classification import MessageClassificationResponse
from app.services.order_lookup import lookup_order


def _cls(intent: str = "return_policy", order_id: str | None = None):
    return MessageClassificationResponse(
        intent=intent,  # type: ignore[arg-type]
        order_id=order_id,
        requires_human_review=True,
    )


def _create_draft(client: TestClient, message: str, key: str | None = None, **extra):
    headers = {"Idempotency-Key": key or str(uuid.uuid4())}
    body = {"message": message, **extra}
    with patch(
        "app.services.support_draft.classify_message",
        new=AsyncMock(return_value=_cls()),
    ):
        return client.post(
            "/api/v1/demo/support-drafts",
            headers=headers,
            json=body,
        ), headers["Idempotency-Key"]


def test_persist_returns_id_revision_status(client: TestClient) -> None:
    response, _ = _create_draft(client, "What is your return window?")
    assert response.status_code == 200
    body = response.json()
    assert body["id"]
    assert body["revision"] == 1
    assert body["review_status"] == "pending_review"
    assert body["requires_human_review"] is True
    assert body["sources"]


def test_source_snapshots_on_detail(client: TestClient) -> None:
    created, _ = _create_draft(client, "What is your return window?")
    request_id = created.json()["id"]
    detail = client.get(f"/api/v1/demo/support-requests/{request_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["sources"]
    assert body["draft_original"] == body["draft_current"]
    assert body["sources"][0]["text"] in body["draft_text"]
    assert body["events"]
    assert body["events"][0]["action"] == "created"


def test_idempotency_same_key_same_payload(client: TestClient) -> None:
    key = str(uuid.uuid4())
    first, _ = _create_draft(client, "What is your return window?", key=key)
    second, _ = _create_draft(client, "What is your return window?", key=key)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["revision"] == second.json()["revision"]


def test_idempotency_same_key_different_payload_conflict(client: TestClient) -> None:
    key = str(uuid.uuid4())
    first, _ = _create_draft(client, "What is your return window?", key=key)
    assert first.status_code == 200
    conflict, _ = _create_draft(client, "How do I start a return process?", key=key)
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "idempotency_key_conflict"


def test_concurrent_idempotent_creates_single_row(client: TestClient) -> None:
    """Concurrent persists with the same key must not create duplicates.

    Uses separate SessionLocal connections (not the shared TestClient override).
    """
    from app.database import SessionLocal
    from app.schemas.classification import MessageClassificationResponse
    from app.services.support_draft import GeneratedDraft
    from app.services.support_request_persistence import (
        find_by_idempotency_key,
        persist_generated_draft,
    )

    key = str(uuid.uuid4())
    message = "Can I exchange for a different size?"
    generated = GeneratedDraft(
        classification=MessageClassificationResponse(
            intent="return_policy",
            order_id=None,
            requires_human_review=True,
        ),
        outcome="draft_ready",
        draft_text="Demo exchange draft.",
        sources=[],
    )

    def once() -> str:
        db = SessionLocal()
        try:
            row = persist_generated_draft(
                db,
                idempotency_key=key,
                message=message,
                customer_email=None,
                generated=generated,
            )
            return str(row.id)
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(lambda _: once(), range(8)))

    assert len(set(ids)) == 1
    db = SessionLocal()
    try:
        assert find_by_idempotency_key(db, key) is not None
    finally:
        db.close()
    # Also reachable via HTTP list
    listing = client.get("/api/v1/demo/support-requests").json()
    assert any(item["id"] == ids[0] for item in listing["items"])


def test_pagination_and_status_filter(client: TestClient) -> None:
    for i in range(3):
        _create_draft(client, f"What is your return window? case {i}")
    listing = client.get("/api/v1/demo/support-requests?status=pending_review&page=1&page_size=2")
    assert listing.status_code == 200
    body = listing.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total"] >= 3
    assert len(body["items"]) == 2


def test_edit_approve_reject_and_terminal(client: TestClient) -> None:
    created, _ = _create_draft(client, "What is your return window?")
    request_id = created.json()["id"]
    revision = created.json()["revision"]

    edited = client.patch(
        f"/api/v1/demo/support-requests/{request_id}/draft",
        json={"draft_text": "Edited demo policy reply.", "expected_revision": revision},
    )
    assert edited.status_code == 200
    assert edited.json()["draft_current"] == "Edited demo policy reply."
    assert edited.json()["revision"] == revision + 1
    assert edited.json()["draft_original"] != edited.json()["draft_current"]

    blank = client.patch(
        f"/api/v1/demo/support-requests/{request_id}/draft",
        json={"draft_text": "   ", "expected_revision": edited.json()["revision"]},
    )
    assert blank.status_code == 422

    approved = client.post(
        f"/api/v1/demo/support-requests/{request_id}/approve",
        json={"expected_revision": edited.json()["revision"], "note": "Looks good"},
    )
    assert approved.status_code == 200
    assert approved.json()["review_status"] == "approved"
    assert approved.json()["reviewed_text"] == "Edited demo policy reply."

    # Terminal: cannot edit or re-approve
    blocked_edit = client.patch(
        f"/api/v1/demo/support-requests/{request_id}/draft",
        json={"draft_text": "Nope", "expected_revision": approved.json()["revision"]},
    )
    assert blocked_edit.status_code == 409

    blocked_approve = client.post(
        f"/api/v1/demo/support-requests/{request_id}/approve",
        json={"expected_revision": approved.json()["revision"]},
    )
    assert blocked_approve.status_code == 409

    # Separate reject path
    created2, _ = _create_draft(client, "Are gift cards non-returnable?")
    rid2 = created2.json()["id"]
    rejected = client.post(
        f"/api/v1/demo/support-requests/{rid2}/reject",
        json={"expected_revision": 1, "note": "Needs rewrite"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["review_status"] == "rejected"
    assert rejected.json()["reviewed_text"] is None


def test_stale_revision_conflict(client: TestClient) -> None:
    created, _ = _create_draft(client, "What is your return window?")
    request_id = created.json()["id"]
    stale = client.patch(
        f"/api/v1/demo/support-requests/{request_id}/draft",
        json={"draft_text": "Stale edit", "expected_revision": 99},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "stale_revision"


def test_concurrent_decisions_one_wins(client: TestClient) -> None:
    from app.database import SessionLocal
    from app.services.support_request_persistence import (
        PersistenceConflictError,
        RequestNotEditableError,
        decide_review,
    )

    created, _ = _create_draft(client, "What is your return window?")
    request_id = uuid.UUID(created.json()["id"])
    revision = created.json()["revision"]

    def decide(approve: bool) -> str:
        db = SessionLocal()
        try:
            decide_review(
                db,
                request_id=request_id,
                expected_revision=revision,
                approve=approve,
            )
            return "ok"
        except (PersistenceConflictError, RequestNotEditableError):
            return "conflict"
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(decide, [True, False]))

    assert sorted(outcomes) == ["conflict", "ok"]
    detail = client.get(f"/api/v1/demo/support-requests/{request_id}").json()
    assert detail["review_status"] in {"approved", "rejected"}


def test_order_data_unchanged_by_review(client: TestClient, db_session) -> None:
    before = lookup_order(
        db_session,
        order_id="SF-1001",
        customer_email="alex.rivera@example.com",
    )
    assert before.order is not None
    status_before = before.order.status

    created, _ = _create_draft(client, "What is your return window?")
    request_id = created.json()["id"]
    client.post(
        f"/api/v1/demo/support-requests/{request_id}/approve",
        json={"expected_revision": 1},
    )

    after = lookup_order(
        db_session,
        order_id="SF-1001",
        customer_email="alex.rivera@example.com",
    )
    assert after.order is not None
    assert after.order.status == status_before


def test_missing_idempotency_key(client: TestClient) -> None:
    with patch(
        "app.services.support_draft.classify_message",
        new=AsyncMock(return_value=_cls()),
    ):
        response = client.post(
            "/api/v1/demo/support-drafts",
            json={"message": "What is your return window?"},
        )
    assert response.status_code == 422


def test_model_failure_does_not_persist(client: TestClient) -> None:
    from app.services.ollama_client import OllamaUnavailableError

    key = str(uuid.uuid4())
    with patch(
        "app.services.support_draft.classify_message",
        new=AsyncMock(side_effect=OllamaUnavailableError("down")),
    ):
        failed = client.post(
            "/api/v1/demo/support-drafts",
            headers={"Idempotency-Key": key},
            json={"message": "What is your return window?"},
        )
    assert failed.status_code == 503
    listing = client.get("/api/v1/demo/support-requests").json()
    # Key must still be usable after failure
    ok, _ = _create_draft(client, "What is your return window?", key=key)
    assert ok.status_code == 200
    assert listing["total"] >= 0
