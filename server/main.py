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

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone


class EventCreate(BaseModel):
    tenant_id: UUID
    event_type: Literal["tokens", "inference_seconds"]
    amount: int = Field(gt=0)


class Event(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    event_type: Literal["tokens", "inference_seconds"]
    amount: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
    reason: str = Field(min_length=3, max_length=200)


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
}


def require_admin(x_admin: Optional[str]) -> str:
    if x_admin != "true":
        raise HTTPException(status_code=403, detail="Admin access required")
    return "admin@example.com"


def find_tenant_index(tenant_id: UUID) -> int:
    for idx, tenant in enumerate(memory_db["tenants"]):
        if tenant.tenant_id == tenant_id:
            return idx
    raise HTTPException(status_code=404, detail="Tenant not found")


@app.get("/v1/usage/events", response_model=EventsResponse)
def list_usage_events():
    return {"events": memory_db["events"]}


@app.post("/v1/usage/events", response_model=Event, status_code=201)
def create_usage_event(event: EventCreate):
    new_event = Event(
        tenant_id=event.tenant_id,
        event_type=event.event_type,
        amount=event.amount,
    )
    memory_db["events"].append(new_event)
    return new_event


@app.get("/v1/tenants", response_model=TenantsResponse)
def list_tenants():
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    tenant_summaries: List[TenantSummary] = []

    for tenant in memory_db["tenants"]:
        tenant_events = [
            event for event in memory_db["events"]
            if event.tenant_id == tenant.tenant_id
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


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)