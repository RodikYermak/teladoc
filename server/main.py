import hashlib
import json
import os
import secrets
from datetime import datetime, timezone, timedelta, date
from typing import List, Literal, Optional
from uuid import UUID, uuid4

import jwt
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Response, Request, Depends, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    UniqueConstraint,
    create_engine,
    select,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker

import time
from sqlalchemy import text




JWT_SECRET = "dev_only_super_secret_signing_key_change_me"
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "teladoc-fake-issuer"
JWT_EXPIRES_MINUTES = 60

MAX_EVENT_AMOUNT = 1_000_000_000
MAX_IDEMPOTENCY_KEY_LENGTH = 100
MAX_REASON_LENGTH = 200
MIN_REASON_LENGTH = 10

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@db:5432/teladoc",
)

security = HTTPBearer(auto_error=False)


class Base(DeclarativeBase):
    pass


class TenantORM(Base):
    __tablename__ = "tenants"

    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    configured_monthly_quota: Mapped[int] = mapped_column(Integer, nullable=False)


class EventORM(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_events_tenant_idempotency"),
    )

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(MAX_IDEMPOTENCY_KEY_LENGTH), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditRecordORM(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[int] = mapped_column(Integer, nullable=False)
    new_value: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(MAX_REASON_LENGTH), nullable=False)
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(StrictBaseModel):
    identifier: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("identifier cannot be empty")
        return trimmed


class LoginResponse(StrictBaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_at: datetime
    user: dict


class EventCreate(StrictBaseModel):
    tenant_id: UUID
    event_type: Literal["tokens", "inference_seconds"]
    amount: int = Field(gt=0, le=MAX_EVENT_AMOUNT)
    idempotency_key: str = Field(min_length=1, max_length=MAX_IDEMPOTENCY_KEY_LENGTH)
    timestamp: Optional[datetime] = None

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("idempotency_key cannot be empty or whitespace")
        return trimmed

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Event(StrictBaseModel):
    event_id: UUID
    tenant_id: UUID
    event_type: Literal["tokens", "inference_seconds"]
    amount: int
    idempotency_key: str
    timestamp: datetime
    idempotency_replayed: bool = False


class EventsResponse(StrictBaseModel):
    events: List[Event]


class TenantSummary(StrictBaseModel):
    tenant_id: UUID
    configured_monthly_quota: int
    month_to_date_usage: int
    last_activity_at: Optional[datetime] = None


class TenantsResponse(StrictBaseModel):
    tenants: List[TenantSummary]


class QuotaUpdateRequest(StrictBaseModel):
    new_monthly_quota: int = Field(gt=0, le=MAX_EVENT_AMOUNT)
    reason: str = Field(min_length=MIN_REASON_LENGTH, max_length=MAX_REASON_LENGTH)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < MIN_REASON_LENGTH:
            raise ValueError(f"reason must be at least {MIN_REASON_LENGTH} non-space characters")
        return trimmed


class QuotaUpdateResponse(StrictBaseModel):
    tenant_id: UUID
    configured_monthly_quota: int
    updated_at: datetime


class AuditRecord(StrictBaseModel):
    audit_id: UUID
    tenant_id: UUID
    action: Literal["quota_updated"]
    old_value: int
    new_value: int
    reason: str
    actor: str
    timestamp: datetime


class AuditResponse(StrictBaseModel):
    records: List[AuditRecord]


class UsageBucket(StrictBaseModel):
    bucket_start: datetime
    bucket_end: datetime
    amount: int


class TenantUsageResponse(StrictBaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    tenant_id: UUID
    from_: datetime = Field(alias="from")
    to: datetime
    granularity: Literal["day"]
    buckets: List[UsageBucket]


class AuthContext(StrictBaseModel):
    sub: str
    role: Literal["admin", "tenant"]
    tenant_id: Optional[UUID] = None
    exp: int
    iss: str


TENANT_1 = UUID("550e8400-e29b-41d4-a716-446655440000")
TENANT_2 = UUID("11111111-1111-1111-1111-111111111111")
TENANT_3 = UUID("22222222-2222-2222-2222-222222222222")

FAKE_USERS = [
    {
        "username": "admin",
        "email": "admin@teladoc.com",
        "password": "password123",
        "role": "admin",
        "display_name": "Admin User",
        "tenant_id": None,
    },
    {
        "username": "tenant",
        "email": "tenant@teladoc.com",
        "password": "password123",
        "role": "tenant",
        "display_name": "Tenant User",
        "tenant_id": str(TENANT_1),
    },
]

app = FastAPI(debug=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    last_error = None

    for attempt in range(15):
        try:
            with engine.begin() as conn:
                conn.execute(text("SELECT 1"))
            break
        except Exception as exc:
            last_error = exc
            print(f"Database not ready yet (attempt {attempt + 1}/15): {exc}")
            time.sleep(2)
    else:
        raise RuntimeError(f"Database not ready after multiple attempts: {last_error}")

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        existing_ids = {
            row[0] for row in db.execute(select(TenantORM.tenant_id)).all()
        }

        seed_tenants = [
            (str(TENANT_1), 1_200_000),
            (str(TENANT_2), 800_000),
            (str(TENANT_3), 500_000),
        ]

        for tenant_id, quota in seed_tenants:
            if tenant_id not in existing_ids:
                db.add(TenantORM(tenant_id=tenant_id, configured_monthly_quota=quota))

        db.commit()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = []
    for err in exc.errors():
        loc = [str(part) for part in err.get("loc", []) if part != "body"]
        field = ".".join(loc) if loc else "request"
        details.append(
            {
                "field": field,
                "message": err.get("msg", "Invalid value"),
                "type": err.get("type", "validation_error"),
            }
        )

    return JSONResponse(
        status_code=422,
        content={
            "code": "validation_error",
            "message": "One or more inputs are invalid.",
            "details": details,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "http_error")
        message = exc.detail.get("message", "Request failed.")
        details = exc.detail.get("details")
        payload = {"code": code, "message": message}
        if details is not None:
            payload["details"] = details
        for key, value in exc.detail.items():
            if key not in payload and key not in {"code", "message", "details"}:
                payload[key] = value
        return JSONResponse(status_code=exc.status_code, content=payload)

    if isinstance(exc.detail, str):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": "http_error", "message": exc.detail},
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={"code": "http_error", "message": "Request failed."},
    )


def unauthorized(message: str = "Authentication required") -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": "unauthorized", "message": message},
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden(message: str = "You do not have permission to perform this action") -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"code": "forbidden", "message": message},
    )


def create_access_token(user: dict) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRES_MINUTES)
    payload = {
        "sub": user["username"],
        "role": user["role"],
        "tenant_id": user["tenant_id"],
        "iss": JWT_ISSUER,
        "exp": expires_at,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expires_at


def authenticate_user(identifier: str, password: str) -> Optional[dict]:
    identifier_lower = identifier.strip().lower()
    for user in FAKE_USERS:
        matches_identifier = (
            user["username"].lower() == identifier_lower
            or user["email"].lower() == identifier_lower
        )
        password_matches = secrets.compare_digest(user["password"], password)
        if matches_identifier and password_matches:
            return user
    return None


def get_current_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthContext:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise unauthorized()

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
        )
    except jwt.ExpiredSignatureError:
        raise unauthorized("Token has expired")
    except jwt.InvalidTokenError:
        raise unauthorized("Invalid token")

    try:
        tenant_id = payload.get("tenant_id")
        auth = AuthContext(
            sub=payload["sub"],
            role=payload["role"],
            tenant_id=UUID(tenant_id) if tenant_id else None,
            exp=payload["exp"],
            iss=payload["iss"],
        )
    except Exception:
        raise unauthorized("Invalid token claims")

    if auth.role == "tenant" and auth.tenant_id is None:
        raise unauthorized("Tenant token missing tenant scope")

    return auth


def require_admin(auth: AuthContext) -> AuthContext:
    if auth.role != "admin":
        raise forbidden("Admin access required")
    return auth


def ensure_tenant_access(auth: AuthContext, tenant_id: UUID) -> None:
    if auth.role == "admin":
        return
    if auth.role == "tenant" and auth.tenant_id == tenant_id:
        return
    raise forbidden("Tenant scope does not allow access to this tenant")


def get_tenant_record(db: Session, tenant_id: UUID) -> TenantORM:
    tenant = db.get(TenantORM, str(tenant_id))
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail={"code": "tenant_not_found", "message": "Tenant not found"},
        )
    return tenant


def parse_iso_datetime(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_datetime",
                "message": f"Invalid {field_name}. Use ISO 8601, for example 2026-03-01T00:00:00Z",
            },
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
    started_at = time.perf_counter()

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))

        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)

        return {
            "configured": True,
            "status": "ok",
            "detail": "Database connection is healthy.",
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)

        return {
            "configured": True,
            "status": "error",
            "detail": str(exc),
            "latency_ms": latency_ms,
        }


def get_month_start(dt: datetime) -> datetime:
    dt_utc = dt.astimezone(timezone.utc)
    return datetime(dt_utc.year, dt_utc.month, 1, tzinfo=timezone.utc)


def get_month_to_date_token_usage(
    db: Session,
    tenant_id: UUID,
    as_of: Optional[datetime] = None,
) -> int:
    now = as_of or datetime.now(timezone.utc)
    month_start = get_month_start(now)

    total = db.scalar(
        select(func.coalesce(func.sum(EventORM.amount), 0)).where(
            EventORM.tenant_id == str(tenant_id),
            EventORM.event_type == "tokens",
            EventORM.timestamp >= month_start,
            EventORM.timestamp <= now,
        )
    )
    return int(total or 0)


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


def orm_event_to_api(event: EventORM, replayed: bool = False) -> Event:
    return Event(
        event_id=UUID(event.event_id),
        tenant_id=UUID(event.tenant_id),
        event_type=event.event_type,
        amount=event.amount,
        idempotency_key=event.idempotency_key,
        timestamp=event.timestamp,
        idempotency_replayed=replayed,
    )


@app.post("/v1/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    user = authenticate_user(payload.identifier, payload.password)
    if not user:
        raise unauthorized("Invalid username/email or password")

    access_token, expires_at = create_access_token(user)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_at=expires_at,
        user={
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "display_name": user["display_name"],
            "tenant_id": user["tenant_id"],
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
    is_ready = db_status["status"] == "ok"

    payload = {
        "status": "ready" if is_ready else "not_ready",
        "service": "usage-api",
        "time": datetime.now(timezone.utc),
        "checks": {
            "db": db_status,
        },
    }

    if not is_ready:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "service_not_ready",
                "message": "Service is not ready",
                "details": payload["checks"],
            },
        )

    return payload


@app.get("/v1/usage/events", response_model=EventsResponse)
def list_usage_events(
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    stmt = select(EventORM).order_by(EventORM.timestamp.desc())

    if auth.role == "tenant":
        stmt = stmt.where(EventORM.tenant_id == str(auth.tenant_id))

    events = db.execute(stmt).scalars().all()
    return {"events": [orm_event_to_api(event) for event in events]}


@app.post("/v1/usage/events", response_model=Event)
def create_usage_event(
    event: EventCreate,
    response: Response,
    allow_overage: bool = Query(False),
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    tenant = get_tenant_record(db, event.tenant_id)
    ensure_tenant_access(auth, event.tenant_id)

    if allow_overage and auth.role != "admin":
        raise forbidden("Only admins can use allow_overage")

    event_timestamp = event.timestamp or datetime.now(timezone.utc)
    validate_event_timestamp(event_timestamp)

    incoming_payload_hash = make_payload_hash(
        tenant_id=event.tenant_id,
        event_type=event.event_type,
        amount=event.amount,
        timestamp=event_timestamp,
    )

    existing = db.execute(
        select(EventORM).where(
            EventORM.tenant_id == str(event.tenant_id),
            EventORM.idempotency_key == event.idempotency_key,
        )
    ).scalar_one_or_none()

    if existing:
        if existing.payload_hash != incoming_payload_hash:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "idempotency_conflict",
                    "message": "Idempotency key already used with a different payload",
                },
            )

        response.status_code = status.HTTP_200_OK
        response.headers["X-Idempotent-Replay"] = "true"
        return orm_event_to_api(existing, replayed=True)

    if event.event_type == "tokens":
        month_to_date_usage = get_month_to_date_token_usage(db, event.tenant_id, as_of=event_timestamp)
        projected_usage = month_to_date_usage + event.amount
        remaining_units = max(tenant.configured_monthly_quota - month_to_date_usage, 0)

        over_quota = projected_usage > tenant.configured_monthly_quota
        admin_override = allow_overage and auth.role == "admin"

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

    new_event = EventORM(
        event_id=str(uuid4()),
        tenant_id=str(event.tenant_id),
        event_type=event.event_type,
        amount=event.amount,
        idempotency_key=event.idempotency_key,
        payload_hash=incoming_payload_hash,
        timestamp=event_timestamp,
    )

    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    response.status_code = status.HTTP_201_CREATED
    response.headers["X-Idempotent-Replay"] = "false"
    return orm_event_to_api(new_event)


@app.get("/v1/tenants", response_model=TenantsResponse)
def list_tenants(
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    stmt = select(TenantORM)
    if auth.role == "tenant":
        stmt = stmt.where(TenantORM.tenant_id == str(auth.tenant_id))

    tenants = db.execute(stmt).scalars().all()
    summaries = []

    for tenant in tenants:
        month_to_date_usage = db.scalar(
            select(func.coalesce(func.sum(EventORM.amount), 0)).where(
                EventORM.tenant_id == tenant.tenant_id,
                EventORM.event_type == "tokens",
                EventORM.timestamp >= month_start,
            )
        ) or 0

        last_activity_at = db.scalar(
            select(func.max(EventORM.timestamp)).where(EventORM.tenant_id == tenant.tenant_id)
        )

        summaries.append(
            TenantSummary(
                tenant_id=UUID(tenant.tenant_id),
                configured_monthly_quota=tenant.configured_monthly_quota,
                month_to_date_usage=int(month_to_date_usage),
                last_activity_at=last_activity_at,
            )
        )

    return {"tenants": summaries}


@app.put("/v1/tenants/{tenant_id}/quota", response_model=QuotaUpdateResponse)
def update_tenant_quota(
    tenant_id: UUID,
    payload: QuotaUpdateRequest,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    require_admin(auth)

    tenant = get_tenant_record(db, tenant_id)
    old_quota = tenant.configured_monthly_quota
    tenant.configured_monthly_quota = payload.new_monthly_quota

    audit_record = AuditRecordORM(
        audit_id=str(uuid4()),
        tenant_id=str(tenant_id),
        action="quota_updated",
        old_value=old_quota,
        new_value=payload.new_monthly_quota,
        reason=payload.reason,
        actor=auth.sub,
        timestamp=datetime.now(timezone.utc),
    )

    db.add(audit_record)
    db.commit()

    return QuotaUpdateResponse(
        tenant_id=tenant_id,
        configured_monthly_quota=payload.new_monthly_quota,
        updated_at=audit_record.timestamp,
    )


@app.get("/v1/audit", response_model=AuditResponse)
def list_audit_logs(
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    require_admin(auth)

    records = db.execute(
        select(AuditRecordORM).order_by(AuditRecordORM.timestamp.desc())
    ).scalars().all()

    return {
        "records": [
            AuditRecord(
                audit_id=UUID(record.audit_id),
                tenant_id=UUID(record.tenant_id),
                action=record.action,
                old_value=record.old_value,
                new_value=record.new_value,
                reason=record.reason,
                actor=record.actor,
                timestamp=record.timestamp,
            )
            for record in records
        ]
    }


@app.get("/v1/tenants/{tenant_id}/usage", response_model=TenantUsageResponse)
def get_tenant_usage(
    tenant_id: UUID,
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    granularity: Literal["day"] = Query("day"),
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    get_tenant_record(db, tenant_id)
    ensure_tenant_access(auth, tenant_id)

    from_dt = parse_iso_datetime(from_, "from")
    to_dt = parse_iso_datetime(to, "to")

    if from_dt >= to_dt:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_date_range", "message": "'from' must be earlier than 'to'"},
        )

    if granularity != "day":
        raise HTTPException(
            status_code=400,
            detail={"code": "unsupported_granularity", "message": "Only granularity=day is supported"},
        )

    events = db.execute(
        select(EventORM).where(
            EventORM.tenant_id == str(tenant_id),
            EventORM.event_type == "tokens",
            EventORM.timestamp >= from_dt,
            EventORM.timestamp < to_dt,
        )
    ).scalars().all()

    bucket_totals: dict[date, int] = {}
    for event in events:
        bucket_day = event.timestamp.astimezone(timezone.utc).date()
        bucket_totals[bucket_day] = bucket_totals.get(bucket_day, 0) + event.amount

    current_day_start = datetime(from_dt.year, from_dt.month, from_dt.day, tzinfo=timezone.utc)
    last_day_start = datetime(to_dt.year, to_dt.month, to_dt.day, tzinfo=timezone.utc)

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