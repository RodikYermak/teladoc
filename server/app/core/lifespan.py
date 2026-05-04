import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select, text

from app.db.schema import SessionLocal, engine
from app.core.dev_data import TENANT_1, TENANT_2, TENANT_3
from app.db.schema import Base, TenantORM


@asynccontextmanager
async def lifespan(app: FastAPI):
    last_error = None

    for attempt in range(15):
        try:
            with engine.begin() as conn:
                conn.execute(text("SELECT 1"))
            break
        except Exception as exc:
            last_error = exc
            print(f"Database not ready yet (attempt {attempt + 1}/15): {exc}")
            time.sleep(2)
    else:
        raise RuntimeError(f"Database not ready after multiple attempts: {last_error}")

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        existing_ids = {
            row[0] for row in db.execute(select(TenantORM.tenant_id)).all()
        }

        seed_tenants = [
            (str(TENANT_1), 1_200_000),
            (str(TENANT_2), 800_000),
            (str(TENANT_3), 500_000),
        ]

        for tenant_id, quota in seed_tenants:
            if tenant_id not in existing_ids:
                db.add(TenantORM(tenant_id=tenant_id, configured_monthly_quota=quota))

        db.commit()

    yield
