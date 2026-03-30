from fastapi import FastAPI
from app.routes.issues import router as issues_router
from app.routes.auth import router as auth_router
from app.middleware.timer import timing_middleware
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Issue Tracker API",
    version="0.1.0",
    description="A mini production-style API built with FastAPI",
)

app.middleware("http")(timing_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(issues_router)


# https://teladoc-poug.onrender.com/api/v1/issues/




# from fastapi import FastAPI
# from os import environ as env

# app = FastAPI()

# tenants = [
#     {"email": "1@user.com", "monthly_quota": 1000, "month_to_date_usage": 500, "last_activity_time": "9:00am"},
#     {"email": "2@user.com", "monthly_quota": 2000, "month_to_date_usage": 1500, "last_activity_time": "8:00am"},
#     {"email": "3@user.com", "monthly_quota": 3000, "month_to_date_usage": 1500, "last_activity_time": "11:00am"},
#     {"email": "4@user.com", "monthly_quota": 4000, "month_to_date_usage": 2500, "last_activity_time": "1:00am"},
#     {"email": "5@user.com", "monthly_quota": 5000, "month_to_date_usage": 3500, "last_activity_time": "4:00am"},
# ]

# events = []

# @app.get("/")
# def index():
#     secret = env.get("MY_VARIABLE", "not_set")
#     return {"details": f"Hello, World! Secret = {secret}"}

# @app.get("/v1/tenants")
# def get_tenants():
#     return tenants

# @app.get("/v1/tenants/{tenant_id}")
# def get_tenant_usage(tenant_id: str):
#     for tenant in tenants:
#         if tenant["email"] == tenant_id:
#             return tenant
#     return {"error": "Item not found"}


# @app.get("/health")
# def health_check():
#     return {"status": "ok"}

# @app.get("/ready")
# def readiness_check():
#     return {"status": "ok"}


# @app.post("/v1/usage/events")
# def create_event_for_tenant(event: dict):
#     events.append(event)
#     return event


# """
# Tenant Usage & Quota Dashboard — FastAPI (in-memory placeholder, no Postgres)
# All business logic rules are enforced; swap the in-memory store for real DB later.
# """

# from __future__ import annotations

# import uuid
# from datetime import datetime, timezone, timedelta
# from typing import Literal, Optional

# from fastapi import FastAPI, HTTPException, Header, Query, status
# from pydantic import BaseModel, Field, field_validator, model_validator

# # ---------------------------------------------------------------------------
# # App
# # ---------------------------------------------------------------------------

# app = FastAPI(title="Tenant Usage & Quota Dashboard", version="0.1.0")

# # ---------------------------------------------------------------------------
# # In-memory data store  (replace with Postgres + SQLAlchemy later)
# # ---------------------------------------------------------------------------

# # tenants: { tenant_id -> dict }
# TENANTS: dict[str, dict] = {
#     "tenant-001": {
#         "tenant_id": "tenant-001",
#         "name": "Acme Corp",
#         "monthly_quota": 10_000,
#         "last_activity": None,
#     },
#     "tenant-002": {
#         "tenant_id": "tenant-002",
#         "name": "Globex Inc",
#         "monthly_quota": 5_000,
#         "last_activity": None,
#     },
#     "tenant-003": {
#         "tenant_id": "tenant-003",
#         "name": "Initech LLC",
#         "monthly_quota": 20_000,
#         "last_activity": None,
#     },
# }

# # events: list of event dicts
# EVENTS: list[dict] = []

# # idempotency keys seen: { (tenant_id, idempotency_key) -> event_id }
# IDEMPOTENCY_KEYS: dict[tuple, str] = {}

# # quota audit log: list of audit dicts
# QUOTA_AUDIT_LOG: list[dict] = []

# # ---------------------------------------------------------------------------
# # Constants
# # ---------------------------------------------------------------------------

# MAX_FUTURE_MINUTES = 5
# MAX_PAST_DAYS = 30
# ADMIN_TOKEN = "admin-secret-token"   # in prod: use real auth (OAuth2 / JWT)

# VALID_EVENT_TYPES = {"tokens", "inference_seconds", "requests"}

# # ---------------------------------------------------------------------------
# # Helpers
# # ---------------------------------------------------------------------------


# def now_utc() -> datetime:
#     return datetime.now(timezone.utc)


# def is_admin(x_admin_token: Optional[str]) -> bool:
#     return x_admin_token == ADMIN_TOKEN


# def month_to_date_usage(tenant_id: str) -> float:
#     """Sum usage for the current calendar month."""
#     start = now_utc().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
#     return sum(
#         e["amount"]
#         for e in EVENTS
#         if e["tenant_id"] == tenant_id
#         and datetime.fromisoformat(e["timestamp"]) >= start
#     )


# def get_tenant_or_404(tenant_id: str) -> dict:
#     tenant = TENANTS.get(tenant_id)
#     if not tenant:
#         raise HTTPException(status_code=404, detail=f"Tenant '{tenant_id}' not found.")
#     return tenant


# # ---------------------------------------------------------------------------
# # Schemas
# # ---------------------------------------------------------------------------


# class UsageEventIn(BaseModel):
#     idempotency_key: str = Field(..., min_length=1, max_length=128)
#     tenant_id: str = Field(..., min_length=1, max_length=128)
#     type: str = Field(..., description="One of: tokens, inference_seconds, requests")
#     amount: float = Field(..., gt=0, description="Positive consumption amount")
#     timestamp: datetime = Field(..., description="ISO 8601 event time")
#     allow_overage: bool = Field(False, description="Admin-only override to exceed quota")

#     @field_validator("type")
#     @classmethod
#     def validate_type(cls, v: str) -> str:
#         if v not in VALID_EVENT_TYPES:
#             raise ValueError(f"type must be one of {sorted(VALID_EVENT_TYPES)}")
#         return v

#     @field_validator("timestamp")
#     @classmethod
#     def validate_timestamp(cls, v: datetime) -> datetime:
#         # Ensure timezone-aware
#         if v.tzinfo is None:
#             v = v.replace(tzinfo=timezone.utc)
#         n = now_utc()
#         if v > n + timedelta(minutes=MAX_FUTURE_MINUTES):
#             raise ValueError(
#                 f"timestamp cannot be more than {MAX_FUTURE_MINUTES} minutes in the future."
#             )
#         if v < n - timedelta(days=MAX_PAST_DAYS):
#             raise ValueError(
#                 f"timestamp cannot be more than {MAX_PAST_DAYS} days in the past."
#             )
#         return v

#     model_config = {"extra": "forbid"}


# class UsageEventOut(BaseModel):
#     event_id: str
#     idempotency_key: str
#     tenant_id: str
#     type: str
#     amount: float
#     timestamp: str
#     duplicate: bool = False


# class DailyBucket(BaseModel):
#     date: str
#     type: str
#     total_amount: float


# class UsageResponse(BaseModel):
#     tenant_id: str
#     from_date: str
#     to_date: str
#     granularity: str
#     buckets: list[DailyBucket]


# class TenantSummary(BaseModel):
#     tenant_id: str
#     name: str
#     monthly_quota: float
#     month_to_date_usage: float
#     remaining: float
#     last_activity: Optional[str]


# class QuotaUpdateIn(BaseModel):
#     quota: float = Field(..., gt=0, description="New monthly quota (must be positive)")
#     reason: str = Field(..., min_length=10, max_length=500)

#     model_config = {"extra": "forbid"}


# class QuotaUpdateOut(BaseModel):
#     tenant_id: str
#     old_quota: float
#     new_quota: float
#     reason: str
#     changed_by: str
#     changed_at: str


# class ErrorDetail(BaseModel):
#     error: str
#     detail: str
#     remaining_units: Optional[float] = None


# # ---------------------------------------------------------------------------
# # Routes — Health
# # ---------------------------------------------------------------------------


# @app.get("/health", tags=["Health"])
# def liveness():
#     """Liveness probe — always 200 if process is up."""
#     return {"status": "ok"}


# @app.get("/ready", tags=["Health"])
# def readiness():
#     """
#     Readiness probe — checks DB connectivity.
#     With the in-memory store this always passes; swap for a real DB ping later.
#     """
#     db_ok = True   # TODO: replace with `await db.execute("SELECT 1")`
#     if not db_ok:
#         raise HTTPException(status_code=503, detail="Database not reachable.")
#     return {"status": "ok", "db": "reachable"}


# # ---------------------------------------------------------------------------
# # Routes — Usage Events
# # ---------------------------------------------------------------------------


# @app.post(
#     "/v1/usage/events",
#     response_model=UsageEventOut,
#     status_code=status.HTTP_201_CREATED,
#     tags=["Usage"],
#     summary="Record a usage event for a tenant",
# )
# def create_usage_event(
#     event: UsageEventIn,
#     x_admin_token: Optional[str] = Header(default=None),
# ):
#     """
#     Record a usage event. Business rules enforced:
#     - Idempotency: duplicate (tenant_id, idempotency_key) pairs are detected and
#       returned as-is without double-counting (HTTP 200 with duplicate=true).
#     - Quota enforcement: rejects events that would exceed the tenant's monthly quota
#       unless the caller is an admin with allow_overage=true.
#     - Timestamp validation: rejects events >5 min in the future or >30 days old.
#     """
#     tenant = get_tenant_or_404(event.tenant_id)
#     admin = is_admin(x_admin_token)

#     # --- allow_overage requires admin ---
#     if event.allow_overage and not admin:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="allow_overage=true requires admin privileges.",
#         )

#     # --- Idempotency check ---
#     idem_key = (event.tenant_id, event.idempotency_key)
#     if idem_key in IDEMPOTENCY_KEYS:
#         existing_id = IDEMPOTENCY_KEYS[idem_key]
#         existing = next(e for e in EVENTS if e["event_id"] == existing_id)
#         return UsageEventOut(**existing, duplicate=True)

#     # --- Quota enforcement ---
#     if not event.allow_overage:
#         current_usage = month_to_date_usage(event.tenant_id)
#         quota = tenant["monthly_quota"]
#         remaining = quota - current_usage
#         if event.amount > remaining:
#             raise HTTPException(
#                 status_code=status.HTTP_409_CONFLICT,
#                 detail={
#                     "error": "quota_exceeded",
#                     "detail": (
#                         f"This event ({event.amount} units) would exceed the tenant's "
#                         f"monthly quota of {quota}."
#                     ),
#                     "remaining_units": max(remaining, 0),
#                 },
#             )

#     # --- Persist event ---
#     event_id = str(uuid.uuid4())
#     ts = event.timestamp.isoformat()
#     record = {
#         "event_id": event_id,
#         "idempotency_key": event.idempotency_key,
#         "tenant_id": event.tenant_id,
#         "type": event.type,
#         "amount": event.amount,
#         "timestamp": ts,
#         "duplicate": False,
#     }
#     EVENTS.append(record)
#     IDEMPOTENCY_KEYS[idem_key] = event_id

#     # Update last_activity on the tenant
#     TENANTS[event.tenant_id]["last_activity"] = ts

#     return UsageEventOut(**record)


# # ---------------------------------------------------------------------------
# # Routes — Tenant Usage Aggregation
# # ---------------------------------------------------------------------------


# @app.get(
#     "/v1/tenants/{tenant_id}/usage",
#     response_model=UsageResponse,
#     tags=["Usage"],
#     summary="Aggregated usage for a tenant over a date range",
# )
# def get_tenant_usage(
#     tenant_id: str,
#     from_date: datetime = Query(..., alias="from", description="ISO 8601 start date"),
#     to_date: datetime = Query(..., alias="to", description="ISO 8601 end date"),
#     granularity: Literal["day"] = Query("day", description="Aggregation bucket size"),
# ):
#     """
#     Returns daily-bucketed usage for a tenant between [from, to].
#     Buckets are grouped by (date, event type).
#     """
#     get_tenant_or_404(tenant_id)

#     if from_date.tzinfo is None:
#         from_date = from_date.replace(tzinfo=timezone.utc)
#     if to_date.tzinfo is None:
#         to_date = to_date.replace(tzinfo=timezone.utc)

#     if from_date > to_date:
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             detail="'from' must be before 'to'.",
#         )

#     # Filter events for this tenant in range
#     filtered = [
#         e for e in EVENTS
#         if e["tenant_id"] == tenant_id
#         and from_date <= datetime.fromisoformat(e["timestamp"]) <= to_date
#     ]

#     # Aggregate: { (date_str, type) -> total }
#     buckets: dict[tuple, float] = {}
#     for e in filtered:
#         day = datetime.fromisoformat(e["timestamp"]).date().isoformat()
#         key = (day, e["type"])
#         buckets[key] = buckets.get(key, 0) + e["amount"]

#     result = [
#         DailyBucket(date=day, type=typ, total_amount=total)
#         for (day, typ), total in sorted(buckets.items())
#     ]

#     return UsageResponse(
#         tenant_id=tenant_id,
#         from_date=from_date.date().isoformat(),
#         to_date=to_date.date().isoformat(),
#         granularity=granularity,
#         buckets=result,
#     )


# # ---------------------------------------------------------------------------
# # Routes — Tenants
# # ---------------------------------------------------------------------------


# @app.get(
#     "/v1/tenants",
#     response_model=list[TenantSummary],
#     tags=["Tenants"],
#     summary="List all tenants with quota and MTD usage",
# )
# def list_tenants():
#     """Returns all tenants with their monthly quota, month-to-date usage, and last activity."""
#     result = []
#     for t in TENANTS.values():
#         mtd = month_to_date_usage(t["tenant_id"])
#         result.append(
#             TenantSummary(
#                 tenant_id=t["tenant_id"],
#                 name=t["name"],
#                 monthly_quota=t["monthly_quota"],
#                 month_to_date_usage=mtd,
#                 remaining=max(t["monthly_quota"] - mtd, 0),
#                 last_activity=t["last_activity"],
#             )
#         )
#     return result


# @app.put(
#     "/v1/tenants/{tenant_id}/quota",
#     response_model=QuotaUpdateOut,
#     tags=["Tenants"],
#     summary="Update a tenant's monthly quota (admin only)",
# )
# def update_tenant_quota(
#     tenant_id: str,
#     body: QuotaUpdateIn,
#     x_admin_token: Optional[str] = Header(default=None),
# ):
#     """
#     Admin-only. Updates the tenant's monthly quota and writes an audit record.
#     Requires a non-empty reason (min 10 characters).
#     """
#     if not is_admin(x_admin_token):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Admin token required. Pass X-Admin-Token header.",
#         )

#     tenant = get_tenant_or_404(tenant_id)
#     old_quota = tenant["monthly_quota"]
#     tenant["monthly_quota"] = body.quota

#     audit = {
#         "tenant_id": tenant_id,
#         "old_quota": old_quota,
#         "new_quota": body.quota,
#         "reason": body.reason,
#         "changed_by": "admin",   # TODO: replace with real user identity from JWT
#         "changed_at": now_utc().isoformat(),
#     }
#     QUOTA_AUDIT_LOG.append(audit)

#     return QuotaUpdateOut(**audit)


# @app.get(
#     "/v1/tenants/{tenant_id}/quota/audit",
#     tags=["Tenants"],
#     summary="View quota change audit log for a tenant (admin only)",
# )
# def get_quota_audit(
#     tenant_id: str,
#     x_admin_token: Optional[str] = Header(default=None),
# ):
#     """Returns all historical quota changes for a tenant."""
#     if not is_admin(x_admin_token):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Admin token required.",
#         )
#     get_tenant_or_404(tenant_id)
#     return [a for a in QUOTA_AUDIT_LOG if a["tenant_id"] == tenant_id]