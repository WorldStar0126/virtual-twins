# Architecture Lock (Phase 0)

This document locks initial technical decisions so implementation can proceed without repeated rework.

## Locked decisions

## 1) Backend stack and runtime

- Python 3.11+
- FastAPI for HTTP APIs
- Pydantic v2 for request/response validation
- Uvicorn as ASGI server

Rationale: rapid API delivery, strong typing, good async support, clear OpenAPI docs.

## 2) Database and migration tool

- PostgreSQL 16 (target)
- Alembic for schema migrations (target)

Rationale: transactional consistency for workflow state and run events, mature ecosystem, reliable migration story.

## 3) Queue/worker technology

- Immediate scaffold: in-process queue abstraction (development bootstrap)
- Production target: Redis-backed queue with delayed retry and dead-letter support

Rationale: unblock workflow implementation now while preserving a clear migration path.

## 4) Media storage

- Target: object storage (S3-compatible)
- Naming convention: `workspace/{workspace_id}/jobs/{job_id}/...`

Rationale: durable media storage for uploads, generated clips, and final outputs.

## 5) Identity model

- Multi-tenant workspace model (`teams` as workspace boundary)
- User membership per team with role (`owner`, `admin`, `operator`, `viewer`)

Rationale: aligns with Phase 2 RBAC requirements and future SaaS isolation.

## 6) Billing provider and pricing model

- Stripe (target)
- Subscription + usage metering

Rationale: fits Phase 3 goals and supports lifecycle + usage ledger patterns.

## API standards

- Version prefix required: `/v1`
- Error envelope: `{"error": {"code": "...", "message": "...", "details": {...}}}`
- Traceability fields for workflow events: `job_id`, `event_type`, `trace_id`, `created_at`

## Change control

Any decision change in this document requires:

1. Updated rationale
2. Migration impact notes
3. Approval in sprint planning

