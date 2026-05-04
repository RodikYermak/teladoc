from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.schema import get_db
from app.core.dependencies import ensure_tenant_access, get_current_auth
from app.core.errors import forbidden
from app.db.schema import EventORM
from app.models.schemas import AuthContext, Event, EventCreate, EventsResponse
from app.services.tenant_service import get_tenant_record
from app.services.usage_service import (
    get_month_to_date_token_usage,
    make_payload_hash,
    orm_event_to_api,
    validate_event_timestamp,
)


router = APIRouter()


@router.get("/v1/usage/events", response_model=EventsResponse)
def list_usage_events(
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    stmt = select(EventORM).order_by(EventORM.timestamp.desc())

    if auth.role == "tenant":
        stmt = stmt.where(EventORM.tenant_id == str(auth.tenant_id))

    events = db.execute(stmt).scalars().all()
    return {"events": [orm_event_to_api(event) for event in events]}


@router.post("/v1/usage/events", response_model=Event)
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
