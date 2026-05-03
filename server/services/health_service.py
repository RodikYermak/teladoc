import time

from sqlalchemy import text

from database import SessionLocal


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
