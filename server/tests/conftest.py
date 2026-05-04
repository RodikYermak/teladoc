import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["DATABASE_URL"] = "postgresql+psycopg://postgres:postgres@localhost:5433/teladoc_test"

from app.main import app  # noqa
from app.db.schema import Base, TenantORM  # noqa
from app.db.schema import get_db  # noqa
from app.core.dev_data import TENANT_1, TENANT_2, TENANT_3  # noqa


TEST_DATABASE_URL = os.environ["DATABASE_URL"]

test_engine = create_engine(TEST_DATABASE_URL, future=True)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    with TestingSessionLocal() as db:
        existing_ids = {row[0] for row in db.execute(text("SELECT tenant_id FROM tenants")).all()}

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

    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def clean_tables():
    with test_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE audit_logs RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE events RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE tenants RESTART IDENTITY CASCADE"))
        conn.execute(
            text(
                """
                INSERT INTO tenants (tenant_id, configured_monthly_quota)
                VALUES
                    (:t1, 1200000),
                    (:t2, 800000),
                    (:t3, 500000)
                """
            ),
            {
                "t1": str(TENANT_1),
                "t2": str(TENANT_2),
                "t3": str(TENANT_3),
            },
        )


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()