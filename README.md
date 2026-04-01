# Teladoc Usage Dashboard

## How to run locally

From the project root, run:

```docker compose up --build```

### That starts:
- frontend on http://localhost:5173
- backend on http://localhost:8000
- postgres on localhost:5432

### Demo credentials

admin / password123
tenant1 / password123
tenant2 / password123
tenant3 / password123

## Overview

This project is a small full-stack tenant usage dashboard built with:

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL
- **Frontend:** React + Vite
- **Local dev/runtime:** Docker Compose

It supports:

- tenant and admin login
- usage event ingestion
- quota tracking
- idempotent event creation
- admin quota updates with audit trail
- tenant-scoped and admin-scoped views

---

## What this change includes

### Backend
- FastAPI service with JWT-based auth
- PostgreSQL persistence
- tenant usage events API
- quota enforcement
- idempotency protection
- audit logging for quota updates
- health and readiness endpoints
- seed data for local development

### Frontend
- login flow
- tenant dashboard
- admin dashboard
- token usage progress card
- tenant event submission form
- admin tenant selection for event creation
- audit trail display

### Tests
- backend pytest coverage for business rules
- frontend Vitest / React Testing Library component tests

---
### Backend tests
From server:
```pytest -q```


Frontend tests
From client:
```npm test```

API summary

### Auth
- POST /v1/auth/login

### Health
- GET /health
- GET /ready

### Usage
- GET /v1/usage/events
- POST /v1/usage/events

### Tenants
- GET /v1/tenants
- PUT /v1/tenants/{tenant_id}/quota
- GET /v1/tenants/{tenant_id}/usage

### Audit
- GET /v1/audit
This assumes usage can be expressed in whole units.
If fractional units were needed later, I would switch to a fixed-precision numeric type.
