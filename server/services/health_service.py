import time

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import SessionLocal

def _create_response(status: str, detail: str, latency_ms: float) -> dict:
    return {
        "configured": True,
        "status": status,
        "detail": detail,
        "latency_ms": latency_ms,
    }

def _measured_latency_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 2)

def check_db_connectivity() -> dict:
    started_at = time.perf_counter()

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))

        return _create_response(
            status="ok",
            detail="Database connection is healthy",
            latency_ms=_measured_latency_ms(started_at),
        )

    except SQLAlchemyError:
        return _create_response(
            status="error",
            detail="Database connection check failed",
            latency_ms=_measured_latency_ms(started_at),
        )