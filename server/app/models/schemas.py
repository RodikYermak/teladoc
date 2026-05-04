from datetime import datetime, timezone
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.core.config import MAX_EVENT_AMOUNT, MAX_IDEMPOTENCY_KEY_LENGTH, MAX_REASON_LENGTH, MIN_REASON_LENGTH


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
