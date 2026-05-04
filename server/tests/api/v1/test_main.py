from datetime import datetime, timedelta, timezone

from app.core.dev_data import TENANT_1


def login(client, identifier="admin", password="password123"):
    response = client.post(
        "/v1/auth/login",
        json={"identifier": identifier, "password": password},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_idempotency_does_not_double_count(client):
    headers = login(client, "tenant1", "password123")
    fixed_timestamp = datetime.now(timezone.utc).isoformat()

    payload = {
        "tenant_id": str(TENANT_1),
        "event_type": "tokens",
        "amount": 100,
        "idempotency_key": "idem-001",
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

    tenants_response = client.get("/v1/tenants", headers=headers)
    assert tenants_response.status_code == 200, tenants_response.text
    tenants = tenants_response.json()["tenants"]
    assert len(tenants) == 1
    assert tenants[0]["tenant_id"] == str(TENANT_1)
    assert tenants[0]["month_to_date_usage"] == 100


def test_quota_enforcement_blocks_and_returns_remaining_units(client):
    headers = login(client, "tenant1", "password123")

    first = client.post(
        "/v1/usage/events",
        json={
            "tenant_id": str(TENANT_1),
            "event_type": "tokens",
            "amount": 1_199_950,
            "idempotency_key": "quota-ok",
        },
        headers=headers,
    )
    assert first.status_code == 201, first.text

    blocked = client.post(
        "/v1/usage/events",
        json={
            "tenant_id": str(TENANT_1),
            "event_type": "tokens",
            "amount": 100,
            "idempotency_key": "quota-block",
        },
        headers=headers,
    )
    assert blocked.status_code == 409, blocked.text

    body = blocked.json()
    assert body["code"] == "quota_exceeded"
    assert body["configured_monthly_quota"] == 1_200_000
    assert body["month_to_date_usage"] == 1_199_950
    assert body["requested_units"] == 100
    assert body["remaining_units"] == 50
    assert body["allow_overage_available_for_admin"] is True


def test_admin_overage_override_works(client):
    admin_headers = login(client, "admin", "password123")

    first = client.post(
        "/v1/usage/events",
        json={
            "tenant_id": str(TENANT_1),
            "event_type": "tokens",
            "amount": 1_200_000,
            "idempotency_key": "admin-base",
        },
        headers=admin_headers,
    )
    assert first.status_code == 201, first.text

    overage = client.post(
        "/v1/usage/events?allow_overage=true",
        json={
            "tenant_id": str(TENANT_1),
            "event_type": "tokens",
            "amount": 100,
            "idempotency_key": "admin-overage",
        },
        headers=admin_headers,
    )
    assert overage.status_code == 201, overage.text
    assert overage.json()["amount"] == 100

    tenants_response = client.get("/v1/tenants", headers=admin_headers)
    assert tenants_response.status_code == 200, tenants_response.text

    tenant_row = next(
        tenant for tenant in tenants_response.json()["tenants"]
        if tenant["tenant_id"] == str(TENANT_1)
    )
    assert tenant_row["month_to_date_usage"] == 1_200_100


def test_quota_updates_require_reason_and_create_audit_record(client):
    admin_headers = login(client, "admin", "password123")

    invalid = client.put(
        f"/v1/tenants/{TENANT_1}/quota",
        json={
            "new_monthly_quota": 900_000,
            "reason": "short",
        },
        headers=admin_headers,
    )
    assert invalid.status_code == 422, invalid.text

    valid = client.put(
        f"/v1/tenants/{TENANT_1}/quota",
        json={
            "new_monthly_quota": 900_000,
            "reason": "Reducing quota for automated test coverage",
        },
        headers=admin_headers,
    )
    assert valid.status_code == 200, valid.text
    body = valid.json()
    assert body["tenant_id"] == str(TENANT_1)
    assert body["configured_monthly_quota"] == 900_000

    audit = client.get("/v1/audit", headers=admin_headers)
    assert audit.status_code == 200, audit.text
    records = audit.json()["records"]
    assert len(records) == 1

    record = records[0]
    assert record["tenant_id"] == str(TENANT_1)
    assert record["action"] == "quota_updated"
    assert record["old_value"] == 1_200_000
    assert record["new_value"] == 900_000
    assert record["reason"] == "Reducing quota for automated test coverage"
    assert record["actor"] == "admin"


def test_timestamp_validation_boundaries(client):
    headers = login(client, "tenant1", "password123")

    valid_past = (datetime.now(timezone.utc) - timedelta(days=29, hours=23)).isoformat()
    valid_response = client.post(
        "/v1/usage/events",
        json={
            "tenant_id": str(TENANT_1),
            "event_type": "tokens",
            "amount": 10,
            "idempotency_key": "valid-ts-boundary",
            "timestamp": valid_past,
        },
        headers=headers,
    )
    assert valid_response.status_code == 201, valid_response.text

    too_old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    too_old_response = client.post(
        "/v1/usage/events",
        json={
            "tenant_id": str(TENANT_1),
            "event_type": "tokens",
            "amount": 10,
            "idempotency_key": "too-old-ts",
            "timestamp": too_old,
        },
        headers=headers,
    )
    assert too_old_response.status_code == 400, too_old_response.text
    assert too_old_response.json()["code"] == "event_timestamp_too_old"

    too_future = (datetime.now(timezone.utc) + timedelta(minutes=6)).isoformat()
    too_future_response = client.post(
        "/v1/usage/events",
        json={
            "tenant_id": str(TENANT_1),
            "event_type": "tokens",
            "amount": 10,
            "idempotency_key": "too-future-ts",
            "timestamp": too_future,
        },
        headers=headers,
    )
    assert too_future_response.status_code == 400, too_future_response.text
    assert too_future_response.json()["code"] == "event_timestamp_in_future"