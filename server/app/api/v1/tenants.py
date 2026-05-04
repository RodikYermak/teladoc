from datetime import datetime, timezone, timedelta, date
from typing import List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.schema import get_db
from app.core.dependencies import ensure_tenant_access, get_current_auth, require_admin
from app.db.schema import AuditRecordORM, EventORM, TenantORM
from app.models.schemas import (
    AuthContext,
    QuotaUpdateRequest,
    QuotaUpdateResponse,
    TenantSummary,
    TenantsResponse,
    TenantUsageResponse,
    UsageBucket,
)
from app.services.tenant_service import get_tenant_record
from app.utils.datetime import parse_iso_datetime


router = APIRouter()


@router.get("/v1/tenants", response_model=TenantsResponse)
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


@router.put("/v1/tenants/{tenant_id}/quota", response_model=QuotaUpdateResponse)
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


@router.get("/v1/tenants/{tenant_id}/usage", response_model=TenantUsageResponse)
def get_tenant_usage(
    tenant_id: UUID,
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    granularity: str = Query("day"),
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
