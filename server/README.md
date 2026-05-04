# Refactored Usage API Server

This server was refactored into the same package-style layout as the provided `project` folder while preserving the original API routes and business logic.

## Structure

```text
app/
  api/v1/          # FastAPI routers
  core/            # config, errors, auth dependencies, lifespan seed logic
  db/              # SQLAlchemy engine/session and ORM schema
  models/          # Pydantic request/response schemas
  services/        # auth, health, tenant, usage business helpers
  utils/           # shared datetime helpers
  main.py          # FastAPI app entrypoint
tests/
  api/v1/          # endpoint tests
```

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Run with Docker Compose

```bash
docker compose up --build
```

## Run tests

The tests expect the `test-db` Postgres service to be available on local port `5433`.

```bash
docker compose up -d test-db
pytest -q
```
