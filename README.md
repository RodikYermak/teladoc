# Teladoc Usage Dashboard

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

## How to run locally

From the project root, run:

```bash
docker compose up --build

That starts:
	•	frontend on http://localhost:5173
	•	backend on http://localhost:8000
	•	postgres on localhost:5432

Demo credentials

admin / password123
tenant1 / password123
tenant2 / password123
tenant3 / password123


Backend tests
From server/:
```pytest -q```


Frontend tests
From client/:
```npm test```

API summary

Auth
	•	POST /v1/auth/login

Health
	•	GET /health
	•	GET /ready

Usage
	•	GET /v1/usage/events
	•	POST /v1/usage/events

Tenants
	•	GET /v1/tenants
	•	PUT /v1/tenants/{tenant_id}/quota
	•	GET /v1/tenants/{tenant_id}/usage

Audit
	•	GET /v1/audit

⸻

Design decisions and tradeoffs

1. Authentication model

Decision

Authentication is implemented with a simple in-memory FAKE_USERS list and JWT tokens.

Why

This keeps the project focused on the assignment’s core business logic:
	•	tenant scoping
	•	event ingestion
	•	quotas
	•	auditability

Tradeoff

This is not production-grade identity management.
In a real system, I would move users into a database and likely integrate with:
	•	SSO / OAuth
	•	a dedicated auth provider
	•	password hashing and reset flows

⸻

2. Schema design

tenants

Stores tenant-level configuration.

Fields:
	•	tenant_id as UUID string primary key
	•	configured_monthly_quota as integer

events

Stores usage events.

Fields:
	•	event_id as UUID string primary key
	•	tenant_id
	•	event_type
	•	amount
	•	idempotency_key
	•	payload_hash
	•	timestamp

audit_logs

Stores quota update history.

Fields:
	•	audit_id as UUID string primary key
	•	tenant_id
	•	action
	•	old_value
	•	new_value
	•	reason
	•	actor
	•	timestamp

Why this schema

It separates:
	•	tenant configuration
	•	immutable event ingestion records
	•	immutable audit records

That makes the business rules easier to reason about and test.

Tradeoff

I kept the schema intentionally small and direct rather than introducing:
	•	normalized user tables
	•	foreign key chains everywhere
	•	extra lookup/reference tables

That reduces complexity for the exercise, but a production system would likely add stronger relational guarantees and richer metadata.

⸻

3. Integer usage amounts

Decision

Usage amounts are stored as integers.

Why

This avoids rounding issues and keeps quota math deterministic for:
	•	tokens
	•	inference seconds
	•	sums
	•	comparisons

Tradeoff

This assumes usage can be expressed in whole units.
If fractional units were needed later, I would switch to a fixed-precision numeric type.
