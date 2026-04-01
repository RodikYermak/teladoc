from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from main import app, memory_db, TENANT_1


client = TestClient(app)


def login(identifier: str, password: str) -> dict:
    response = client.post(
        "/v1/auth/login",
        json={
            "identifier": identifier,
            "password": password,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return {
        "Authorization": f"Bearer {body['access_token']}",
    }


@pytest.fixture(autouse=True)
def reset_memory_db():
    memory_db["events"].clear()
    memory_db["audit_logs"].clear()
    memory_db["idempotency_index"].clear()

    memory_db["tenants"][0] = memory_db["tenants"][0].model_copy(
        update={"configured_monthly_quota": 1_200_000}
    )
    memory_db["tenants"][1] = memory_db["tenants"][1].model_copy(
        update={"configured_monthly_quota": 800_000}
    )
    memory_db["tenants"][2] = memory_db["tenants"][2].model_copy(
        update={"configured_monthly_quota": 500_000}
    )


def test_idempotency_does_not_double_count():
    headers = login("tenant", "password123")
    idem_key = "idem-001"
    fixed_timestamp = datetime.now(timezone.utc).isoformat()

    payload = {
        "tenant_id": str(TENANT_1),
        "event_type": "tokens",
        "amount": 100,
        "idempotency_key": idem_key,
        "timestamp": fixed_timestamp,
    }

    first = client.post("/v1/usage/events", json=payload, headers=headers)
    assert first.status_code == 201, first.text
    first_body = first.json()
    assert first_body["amount"] == 100
    assert first_body["idempotency_replayed"] is False

    second = client.post("/v1/usage/events", json=payload, headers=headers)
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["idempotency_replayed"] is True

    events_response = client.get("/v1/usage/events", headers=headers)
    assert events_response.status_code == 200
    events = events_response.json()["events"]
    assert len(events) == 1
    assert events[0]["amount"] == 100

    tenants_response = client.get("/v1/tenants", headers=headers)
    assert tenants_response.status_code == 200
    tenant = tenants_response.json()["tenants"][0]
    assert tenant["tenant_id"] == str(TENANT_1)
    assert tenant["month_to_date_usage"] == 100


def test_quota_enforcement_blocks_and_returns_remaining_units():
    headers = login("tenant", "password123")

    first_payload = {
        "tenant_id": str(TENANT_1),
        "event_type": "tokens",
        "amount": 1_199_900,
        "idempotency_key": "quota-ok-1",
    }
    first = client.post("/v1/usage/events", json=first_payload, headers=headers)
    assert first.status_code == 201, first.text

    blocked_payload = {
        "tenant_id": str(TENANT_1),
        "event_type": "tokens",
        "amount": 200,
        "idempotency_key": "quota-block-1",
    }
    blocked = client.post("/v1/usage/events", json=blocked_payload, headers=headers)
    assert blocked.status_code == 409, blocked.text

    body = blocked.json()
    assert body["code"] == "quota_exceeded"
    assert body["configured_monthly_quota"] == 1_200_000
    assert body["month_to_date_usage"] == 1_199_900
    assert body["requested_units"] == 200
    assert body["remaining_units"] == 100

    events_response = client.get("/v1/usage/events", headers=headers)
    events = events_response.json()["events"]
    assert len(events) == 1


def test_admin_overage_override_works():
    admin_headers = login("admin", "password123")

    update_quota = client.put(
        f"/v1/tenants/{TENANT_1}/quota",
        json={
            "new_monthly_quota": 100,
            "reason": "Lowering quota for overage test",
        },
        headers=admin_headers,
    )
    assert update_quota.status_code == 200, update_quota.text

    normal_payload = {
        "tenant_id": str(TENANT_1),
        "event_type": "tokens",
        "amount": 90,
        "idempotency_key": "overage-base",
    }
    normal_event = client.post("/v1/usage/events", json=normal_payload, headers=admin_headers)
    assert normal_event.status_code == 201, normal_event.text

    blocked_payload = {
        "tenant_id": str(TENANT_1),
        "event_type": "tokens",
        "amount": 20,
        "idempotency_key": "overage-blocked",
    }
    blocked = client.post("/v1/usage/events", json=blocked_payload, headers=admin_headers)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["code"] == "quota_exceeded"

    override_payload = {
        "tenant_id": str(TENANT_1),
        "event_type": "tokens",
        "amount": 20,
        "idempotency_key": "overage-allowed",
    }
    override = client.post(
        "/v1/usage/events?allow_overage=true",
        json=override_payload,
        headers=admin_headers,
    )
    assert override.status_code == 201, override.text

    tenants = client.get("/v1/tenants", headers=admin_headers)
    tenant_row = next(t for t in tenants.json()["tenants"] if t["tenant_id"] == str(TENANT_1))
    assert tenant_row["month_to_date_usage"] == 110


def test_quota_update_requires_reason_and_creates_audit_record():
    admin_headers = login("admin", "password123")

    missing_reason = client.put(
        f"/v1/tenants/{TENANT_1}/quota",
        json={
            "new_monthly_quota": 999999,
            "reason": "short",
        },
        headers=admin_headers,
    )
    assert missing_reason.status_code == 422, missing_reason.text
    body = missing_reason.json()
    assert body["code"] == "validation_error"

    audit_before = client.get("/v1/audit", headers=admin_headers)
    assert audit_before.status_code == 200
    assert audit_before.json()["records"] == []

    valid_update = client.put(
        f"/v1/tenants/{TENANT_1}/quota",
        json={
            "new_monthly_quota": 900000,
            "reason": "Reduce quota after contract change",
        },
        headers=admin_headers,
    )
    assert valid_update.status_code == 200, valid_update.text
    updated_body = valid_update.json()
    assert updated_body["tenant_id"] == str(TENANT_1)
    assert updated_body["configured_monthly_quota"] == 900000

    audit_after = client.get("/v1/audit", headers=admin_headers)
    assert audit_after.status_code == 200
    records = audit_after.json()["records"]
    assert len(records) == 1

    record = records[0]
    assert record["tenant_id"] == str(TENANT_1)
    assert record["action"] == "quota_updated"
    assert record["old_value"] == 1_200_000
    assert record["new_value"] == 900000
    assert record["reason"] == "Reduce quota after contract change"
    assert record["actor"] == "admin"


def test_timestamp_validation_boundaries():
    headers = login("tenant", "password123")
    now = datetime.now(timezone.utc)

    valid_future = (now + timedelta(minutes=4, seconds=50)).isoformat()
    valid_future_payload = {
        "tenant_id": str(TENANT_1),
        "event_type": "tokens",
        "amount": 10,
        "idempotency_key": "ts-valid-future",
        "timestamp": valid_future,
    }
    valid_future_response = client.post(
        "/v1/usage/events",
        json=valid_future_payload,
        headers=headers,
    )
    assert valid_future_response.status_code == 201, valid_future_response.text

    too_future = (now + timedelta(minutes=5, seconds=10)).isoformat()
    too_future_payload = {
        "tenant_id": str(TENANT_1),
        "event_type": "tokens",
        "amount": 10,
        "idempotency_key": "ts-too-future",
        "timestamp": too_future,
    }
    too_future_response = client.post(
        "/v1/usage/events",
        json=too_future_payload,
        headers=headers,
    )
    assert too_future_response.status_code == 400, too_future_response.text
    assert too_future_response.json()["code"] == "event_timestamp_in_future"

    valid_past = (now - timedelta(days=29, hours=23, minutes=59)).isoformat()
    valid_past_payload = {
        "tenant_id": str(TENANT_1),
        "event_type": "tokens",
        "amount": 10,
        "idempotency_key": "ts-valid-past",
        "timestamp": valid_past,
    }
    valid_past_response = client.post(
        "/v1/usage/events",
        json=valid_past_payload,
        headers=headers,
    )
    assert valid_past_response.status_code == 201, valid_past_response.text

    too_old = (now - timedelta(days=30, seconds=10)).isoformat()
    too_old_payload = {
        "tenant_id": str(TENANT_1),
        "event_type": "tokens",
        "amount": 10,
        "idempotency_key": "ts-too-old",
        "timestamp": too_old,
    }
    too_old_response = client.post(
        "/v1/usage/events",
        json=too_old_payload,
        headers=headers,
    )
    assert too_old_response.status_code == 400, too_old_response.text
    assert too_old_response.json()["code"] == "event_timestamp_too_old"