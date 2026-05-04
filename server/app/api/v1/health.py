from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.services.health_service import check_db_connectivity


router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "usage-api",
        "time": datetime.now(timezone.utc),
    }


@router.get("/ready")
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
