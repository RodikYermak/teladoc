import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models import EventORM
from schemas import Event
from utils.datetime import get_month_start


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
