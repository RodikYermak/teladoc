from datetime import datetime, timezone

from fastapi import HTTPException


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


def get_month_start(dt: datetime) -> datetime:
    dt_utc = dt.astimezone(timezone.utc)
    return datetime(dt_utc.year, dt_utc.month, 1, tzinfo=timezone.utc)
