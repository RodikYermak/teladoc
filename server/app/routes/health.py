from fastapi import APIRouter
# from app.db import engine

router = APIRouter()

@router.get("/health")
def check_health():
    return {"status": "ok"}

# @router.get("/ready")
# def check_ready():
#     try:
#         with engine.connect() as conn:
#             conn.execute("SELECT 1")
#         return {"status": "ready"}
#     except Exception:
#         return {"status": "not ready"}