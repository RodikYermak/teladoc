# from fastapi import FastAPI

# from app.routes.issues import router as issues_router
# from app.routes.auth import router as auth_router
# from app.routes.health import router as health_router

# from app.middleware.timer import timing_middleware
# from fastapi.middleware.cors import CORSMiddleware

# app = FastAPI(
#     title="Issue Tracker API",
#     version="0.1.0",
#     description="A mini production-style API built with FastAPI",
# )

# app.middleware("http")(timing_middleware)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# app.include_router(auth_router)
# app.include_router(issues_router)
# app.include_router(health_router)


# # https://teladoc-poug.onrender.com/api/v1/issues/


# import uvicorn
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel, Field
# from typing import List
# from uuid import UUID, uuid4
# from datetime import datetime

# # Event schema
# class Event(BaseModel):
#     event_id: UUID = Field(default_factory=uuid4)
#     tenant_id: UUID
#     type: str  # "tokens" or "inference_seconds"
#     amount: int
#     timestamp: datetime

# class Events(BaseModel):
#     events: List[Event]

# app = FastAPI(debug=True)

# origins = [
#     "http://localhost:5173",
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # In-memory DB
# memory_db = {"events": []}

# @app.get("/events", response_model=Events)
# def get_events():
#     return Events(events=memory_db["events"])

# @app.post("/events", response_model=Event)
# def add_event(event: Event):
#     # Only use tenant_id, type, amount from client
#     new_event = Event(
#         tenant_id=event.tenant_id,
#         type=event.type,
#         amount=event.amount
#     )
#     memory_db["events"].append(new_event)
#     return new_event

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)

import hashlib
import json
import uvicorn
from collections import defaultdict
from datetime import datetime, timezone, timedelta, date
from fastapi import FastAPI, Header, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Literal, Optional
from uuid import UUID, uuid4


class EventCreate(BaseModel):
    tenant_id: UUID
    event_type: Literal["tokens", "inference_seconds"]
    amount: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1, max_length=100)
    timestamp: Optional[datetime] = None

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return value

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)


class Event(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    event_type: Literal["tokens", "inference_seconds"]
    amount: int
    idempotency_key: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    idempotency_replayed: bool = False


class EventsResponse(BaseModel):
    events: List[Event]


class TenantRecord(BaseModel):
    tenant_id: UUID
    configured_monthly_quota: int = Field(gt=0)


class TenantSummary(BaseModel):
    tenant_id: UUID
    configured_monthly_quota: int
    month_to_date_usage: int
    last_activity_at: Optional[datetime] = None


class TenantsResponse(BaseModel):
    tenants: List[TenantSummary]


class QuotaUpdateRequest(BaseModel):
    new_monthly_quota: int = Field(gt=0)
    reason: str = Field(min_length=10, max_length=200)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < 10:
            raise ValueError("reason must be at least 10 non-space characters")
        return trimmed


class QuotaUpdateResponse(BaseModel):
    tenant_id: UUID
    configured_monthly_quota: int
    updated_at: datetime


class AuditRecord(BaseModel):
    audit_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    action: Literal["quota_updated"]
    old_value: int
    new_value: int
    reason: str
    actor: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditResponse(BaseModel):
    records: List[AuditRecord]


class UsageBucket(BaseModel):
    bucket_start: datetime
    bucket_end: datetime
    amount: int


class TenantUsageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: UUID
    from_: datetime = Field(alias="from")
    to: datetime
    granularity: Literal["day"]
    buckets: List[UsageBucket]


app = FastAPI(debug=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory_db = {
    "events": [],
    "tenants": [
        TenantRecord(
            tenant_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            configured_monthly_quota=1200000,
        ),
        TenantRecord(
            tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
            configured_monthly_quota=800000,
        ),
        TenantRecord(
            tenant_id=UUID("22222222-2222-2222-2222-222222222222"),
            configured_monthly_quota=500000,
        ),
    ],
    "audit_logs": [],
    "idempotency_index": {},
}


def require_admin(x_admin: Optional[str]) -> str:
    if x_admin != "true":
        raise HTTPException(status_code=403, detail="Admin access required")
    return "admin@example.com"


def is_admin(x_admin: Optional[str]) -> bool:
    return x_admin == "true"


def find_tenant_index(tenant_id: UUID) -> int:
    for idx, tenant in enumerate(memory_db["tenants"]):
        if tenant.tenant_id == tenant_id:
            return idx
    raise HTTPException(status_code=404, detail="Tenant not found")


def get_tenant_record(tenant_id: UUID) -> TenantRecord:
    for tenant in memory_db["tenants"]:
        if tenant.tenant_id == tenant_id:
            return tenant
    raise HTTPException(status_code=404, detail="Tenant not found")


def ensure_tenant_exists(tenant_id: UUID) -> None:
    for tenant in memory_db["tenants"]:
        if tenant.tenant_id == tenant_id:
            return
    raise HTTPException(status_code=404, detail="Tenant not found")


def parse_iso_datetime(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}. Use ISO 8601, for example 2026-03-01T00:00:00Z",
        )

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)

    return parsed


def make_payload_hash(
    tenant_id: UUID,
    event_type: str,
    amount: int,
    timestamp: datetime,
) -> str:
    normalized_payload = {
        "tenant_id": str(tenant_id),
        "event_type": event_type,
        "amount": amount,
        "timestamp": timestamp.isoformat(),
    }
    raw = json.dumps(normalized_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def check_db_connectivity() -> dict:
    return {
        "configured": False,
        "status": "not_configured",
        "detail": "No external database configured; using in-memory storage.",
    }


def get_month_start(dt: datetime) -> datetime:
    dt_utc = dt.astimezone(timezone.utc)
    return datetime(dt_utc.year, dt_utc.month, 1, tzinfo=timezone.utc)


def get_month_to_date_token_usage(tenant_id: UUID, as_of: Optional[datetime] = None) -> int:
    now = as_of or datetime.now(timezone.utc)
    month_start = get_month_start(now)

    return sum(
        event.amount
        for event in memory_db["events"]
        if event.tenant_id == tenant_id
        and event.event_type == "tokens"
        and month_start <= event.timestamp <= now
    )


def validate_event_timestamp(event_timestamp: datetime) -> None:
    now = datetime.now(timezone.utc)
    future_limit = now + timedelta(minutes=5)
    past_limit = now - timedelta(days=30)

    if event_timestamp > future_limit:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "event_timestamp_in_future",
                "message": "Event timestamp cannot be more than 5 minutes in the future",
                "timestamp": event_timestamp.isoformat(),
                "max_allowed_timestamp": future_limit.isoformat(),
            },
        )

    if event_timestamp < past_limit:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "event_timestamp_too_old",
                "message": "Event timestamp cannot be more than 30 days in the past",
                "timestamp": event_timestamp.isoformat(),
                "min_allowed_timestamp": past_limit.isoformat(),
            },
        )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "usage-api",
        "time": datetime.now(timezone.utc),
    }


@app.get("/ready")
def ready():
    db_status = check_db_connectivity()
    return {
        "status": "ready",
        "service": "usage-api",
        "time": datetime.now(timezone.utc),
        "checks": {
            "db": db_status,
        },
    }


@app.get("/v1/usage/events", response_model=EventsResponse)
def list_usage_events():
    return {"events": memory_db["events"]}


@app.post("/v1/usage/events", response_model=Event)
def create_usage_event(
    event: EventCreate,
    response: Response,
    allow_overage: bool = Query(False),
    x_admin: Optional[str] = Header(default=None),
):
    ensure_tenant_exists(event.tenant_id)

    event_timestamp = event.timestamp or datetime.now(timezone.utc)
    validate_event_timestamp(event_timestamp)

    idempotency_key = (str(event.tenant_id), event.idempotency_key)
    incoming_payload_hash = make_payload_hash(
        tenant_id=event.tenant_id,
        event_type=event.event_type,
        amount=event.amount,
        timestamp=event_timestamp,
    )

    existing = memory_db["idempotency_index"].get(idempotency_key)
    if existing:
        if existing["payload_hash"] != incoming_payload_hash:
            raise HTTPException(
                status_code=409,
                detail="Idempotency key already used with a different payload",
            )

        response.status_code = status.HTTP_200_OK
        response.headers["X-Idempotent-Replay"] = "true"

        stored_event: Event = existing["event"]
        return Event(
            event_id=stored_event.event_id,
            tenant_id=stored_event.tenant_id,
            event_type=stored_event.event_type,
            amount=stored_event.amount,
            idempotency_key=stored_event.idempotency_key,
            timestamp=stored_event.timestamp,
            idempotency_replayed=True,
        )

    tenant = get_tenant_record(event.tenant_id)

    if event.event_type == "tokens":
        month_to_date_usage = get_month_to_date_token_usage(event.tenant_id, as_of=event_timestamp)
        projected_usage = month_to_date_usage + event.amount
        remaining_units = max(tenant.configured_monthly_quota - month_to_date_usage, 0)

        over_quota = projected_usage > tenant.configured_monthly_quota
        admin_override = allow_overage and is_admin(x_admin)

        if over_quota and not admin_override:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "quota_exceeded",
                    "message": "Event would exceed tenant monthly quota",
                    "tenant_id": str(event.tenant_id),
                    "configured_monthly_quota": tenant.configured_monthly_quota,
                    "month_to_date_usage": month_to_date_usage,
                    "requested_units": event.amount,
                    "remaining_units": remaining_units,
                    "allow_overage_available_for_admin": True,
                },
            )

    new_event = Event(
        tenant_id=event.tenant_id,
        event_type=event.event_type,
        amount=event.amount,
        idempotency_key=event.idempotency_key,
        timestamp=event_timestamp,
    )

    memory_db["events"].append(new_event)
    memory_db["idempotency_index"][idempotency_key] = {
        "payload_hash": incoming_payload_hash,
        "event": new_event,
    }

    response.status_code = status.HTTP_201_CREATED
    response.headers["X-Idempotent-Replay"] = "false"
    return new_event


@app.get("/v1/tenants", response_model=TenantsResponse)
def list_tenants():
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    tenant_summaries: List[TenantSummary] = []

    for tenant in memory_db["tenants"]:
        tenant_events = [
            event for event in memory_db["events"] if event.tenant_id == tenant.tenant_id
        ]

        month_to_date_usage = sum(
            event.amount
            for event in tenant_events
            if event.timestamp >= month_start and event.event_type == "tokens"
        )

        last_activity_at = None
        if tenant_events:
            last_activity_at = max(event.timestamp for event in tenant_events)

        tenant_summaries.append(
            TenantSummary(
                tenant_id=tenant.tenant_id,
                configured_monthly_quota=tenant.configured_monthly_quota,
                month_to_date_usage=month_to_date_usage,
                last_activity_at=last_activity_at,
            )
        )

    return {"tenants": tenant_summaries}


@app.put("/v1/tenants/{tenant_id}/quota", response_model=QuotaUpdateResponse)
def update_tenant_quota(
    tenant_id: UUID,
    payload: QuotaUpdateRequest,
    x_admin: Optional[str] = Header(default=None),
):
    actor = require_admin(x_admin)

    tenant_index = find_tenant_index(tenant_id)
    tenant = memory_db["tenants"][tenant_index]

    old_quota = tenant.configured_monthly_quota
    new_quota = payload.new_monthly_quota

    updated_tenant = TenantRecord(
        tenant_id=tenant.tenant_id,
        configured_monthly_quota=new_quota,
    )
    memory_db["tenants"][tenant_index] = updated_tenant

    audit_record = AuditRecord(
        tenant_id=tenant_id,
        action="quota_updated",
        old_value=old_quota,
        new_value=new_quota,
        reason=payload.reason,
        actor=actor,
    )
    memory_db["audit_logs"].append(audit_record)

    return QuotaUpdateResponse(
        tenant_id=tenant_id,
        configured_monthly_quota=new_quota,
        updated_at=audit_record.timestamp,
    )


@app.get("/v1/audit", response_model=AuditResponse)
def list_audit_logs(x_admin: Optional[str] = Header(default=None)):
    require_admin(x_admin)
    return {"records": memory_db["audit_logs"]}


@app.get("/v1/tenants/{tenant_id}/usage", response_model=TenantUsageResponse)
def get_tenant_usage(
    tenant_id: UUID,
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    granularity: Literal["day"] = Query("day"),
):
    ensure_tenant_exists(tenant_id)

    from_dt = parse_iso_datetime(from_, "from")
    to_dt = parse_iso_datetime(to, "to")

    if from_dt >= to_dt:
        raise HTTPException(status_code=400, detail="'from' must be earlier than 'to'")

    if granularity != "day":
        raise HTTPException(status_code=400, detail="Only granularity=day is supported")

    bucket_totals: dict[date, int] = defaultdict(int)

    for event in memory_db["events"]:
        if event.tenant_id != tenant_id:
            continue
        if event.event_type != "tokens":
            continue
        if not (from_dt <= event.timestamp < to_dt):
            continue

        bucket_day = event.timestamp.astimezone(timezone.utc).date()
        bucket_totals[bucket_day] += event.amount

    current_day_start = datetime(
        from_dt.year, from_dt.month, from_dt.day, tzinfo=timezone.utc
    )
    last_day_start = datetime(
        to_dt.year, to_dt.month, to_dt.day, tzinfo=timezone.utc
    )

    if to_dt.time() != datetime.min.time():
        days_end_exclusive = last_day_start + timedelta(days=1)
    else:
        days_end_exclusive = last_day_start

    buckets: List[UsageBucket] = []
    cursor = current_day_start

    while cursor < days_end_exclusive:
        next_cursor = cursor + timedelta(days=1)
        bucket_amount = bucket_totals.get(cursor.date(), 0)

        bucket_start = max(cursor, from_dt)
        bucket_end = min(next_cursor, to_dt)

        if bucket_start < bucket_end:
            buckets.append(
                UsageBucket(
                    bucket_start=bucket_start,
                    bucket_end=bucket_end,
                    amount=bucket_amount,
                )
            )

        cursor = next_cursor

    return TenantUsageResponse(
        tenant_id=tenant_id,
        from_=from_dt,
        to=to_dt,
        granularity=granularity,
        buckets=buckets,
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)