from datetime import datetime, timedelta, timezone

from main import TENANT_1


def login(client, identifier="admin", password="password123"):
    response = client.post(
        "/v1/auth/login",
        json={"identifier": identifier, "password": password},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_event_persists_to_real_postgres(client):
    headers = login(client, "tenant", "password123")

    payload = {
        "tenant_id": str(TENANT_1),
        "event_type": "tokens",
        "amount": 250,
        "idempotency_key": "pg-int-1",
    }

    create_response = client.post("/v1/usage/events", json=payload, headers=headers)
    assert create_response.status_code == 201, create_response.text

    list_response = client.get("/v1/usage/events", headers=headers)
    assert list_response.status_code == 200, list_response.text

    events = list_response.json()["events"]
    assert len(events) == 1
    assert events[0]["amount"] == 250
    assert events[0]["tenant_id"] == str(TENANT_1)


def test_idempotency_does_not_double_count_with_real_postgres(client):
    headers = login(client, "tenant", "password123")
    fixed_timestamp = datetime.now(timezone.utc).isoformat()

    payload = {
        "tenant_id": str(TENANT_1),
        "event_type": "tokens",
        "amount": 100,
        "idempotency_key": "pg-idem-1",
        "timestamp": fixed_timestamp,
    }

    first = client.post("/v1/usage/events", json=payload, headers=headers)
    assert first.status_code == 201, first.text

    second = client.post("/v1/usage/events", json=payload, headers=headers)
    assert second.status_code == 200, second.text
    assert second.json()["idempotency_replayed"] is True

    tenants = client.get("/v1/tenants", headers=headers)
    assert tenants.status_code == 200, tenants.text
    row = tenants.json()["tenants"][0]
    assert row["month_to_date_usage"] == 100


def test_quota_enforcement_blocks_with_real_postgres(client):
    headers = login(client, "tenant", "password123")

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
    assert body["remaining_units"] == 50


def test_admin_can_update_quota_and_audit_is_written(client):
    headers = login(client, "admin", "password123")

    update = client.put(
        f"/v1/tenants/{TENANT_1}/quota",
        json={
            "new_monthly_quota": 900000,
            "reason": "Reducing quota for integration test",
        },
        headers=headers,
    )
    assert update.status_code == 200, update.text

    audit = client.get("/v1/audit", headers=headers)
    assert audit.status_code == 200, audit.text
    records = audit.json()["records"]
    assert len(records) == 1
    assert records[0]["tenant_id"] == str(TENANT_1)
    assert records[0]["new_value"] == 900000


def test_timestamp_validation_with_real_postgres(client):
    headers = login(client, "tenant", "password123")

    too_old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()

    response = client.post(
        "/v1/usage/events",
        json={
            "tenant_id": str(TENANT_1),
            "event_type": "tokens",
            "amount": 10,
            "idempotency_key": "old-ts",
            "timestamp": too_old,
        },
        headers=headers,
    )
    assert response.status_code == 400, response.text
    assert response.json()["code"] == "event_timestamp_too_old"