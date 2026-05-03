from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_auth, require_admin
from models import AuditRecordORM
from schemas import AuditRecord, AuditResponse, AuthContext


router = APIRouter()


@router.get("/v1/audit", response_model=AuditResponse)
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
