from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import TenantORM


def get_tenant_record(db: Session, tenant_id: UUID) -> TenantORM:
    tenant = db.get(TenantORM, str(tenant_id))
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail={"code": "tenant_not_found", "message": "Tenant not found"},
        )
    return tenant
