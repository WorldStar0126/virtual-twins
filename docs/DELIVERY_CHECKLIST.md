# Delivery Checklist (Live)

This checklist tracks immediate execution from `PROJECT_PLAN.md`.

## Immediate actions

- Finalize architecture and stack decisions
- Define database schema draft
- Implement job lifecycle state machine + run event model
- Stand up queue/worker skeleton
- Build first API endpoints
  - `POST /v1/jobs`
  - `POST /v1/jobs/{job_id}/approvals/clip-1`
  - `GET /v1/jobs/{job_id}/events`
- Build Google Drive connector POC
  - OAuth connection
  - Folder scan
  - Asset metadata ingestion
  - Incremental sync job
- Run first internal pilot (20s then 30s)
  - Pilot harness added (`backend/scripts/run_internal_pilot.py`)
  - Pilot runbook added (`docs/PILOT_RUNBOOK.md`)
  - Execute pilot and attach report evidence (`docs/PILOT_REPORT_2026-04-22.json`)

## Next implementation slice

1. [x] Swap in persistent database access (PostgreSQL-ready repository + env selection).
2. [x] Add Alembic migration baseline.
3. [x] Replace in-process queue with Redis-backed queue (plus in-memory fallback).
4. [x] Add connector abstraction and Google Drive POC.

## Phase 1 hardening

1. [x] Retry policy with exponential backoff in worker runner.
2. [x] Dead-letter queue path for terminal task failures.
3. [x] Idempotent clip-1 worker behavior for duplicate deliveries.
4. [x] Add automated tests for retry + DLQ scenarios.

## Step 2: persistent connector state

1. [x] Add connector persistence tables and migration (`0002_connector_persistence`).
2. [x] Add connector store abstraction (memory/postgres implementations).
3. [x] Persist OAuth state, sources, sync jobs, and synced asset metadata.
4. [x] Wire API connector service to pluggable connector store.

## Step 3: real Google integration

1. [x] Real OAuth token exchange implementation (Google token endpoint).
2. [x] Persist refresh token and access token expiry on sources.
3. [x] Real Drive file listing with pagination token support.
4. [x] Refresh access token and retry scan on auth failure.

## Step 4: observability and alerts baseline

1. [x] Add API request metrics (count, status buckets, latency).
2. [x] Add worker metrics (task totals, retries, terminal failures, latency).
3. [x] Add metrics endpoint (`GET /metrics`).
4. [x] Add basic alert evaluation endpoint (`GET /v1/ops/alerts`).
5. [x] Add baseline observability tests.

## Step 5: API/security hardening baseline

1. [x] Standardize error envelope for API/validation/unhandled errors.
2. [x] Add idempotency replay semantics for `POST /v1/jobs` (`200` + replay flag).
3. [x] Add repository-level idempotency lookup helper.
4. [x] Add API contract tests (error envelope + idempotency replay).

## Step 6: CI and test pipeline baseline

1. [x] Add lint configuration (`ruff`) for backend code.
2. [x] Add local CI command runner script (`backend/scripts/run_ci_checks.py`).
3. [x] Add GitHub Actions backend CI workflow.
4. [x] Keep test/lint gates documented in backend README.

## Phase 1 completion evidence

1. [x] End-to-end 20s and 30s internal pilot reaches final `done` state.
2. [x] Controlled batch pilot run validates completion rate >= 95%.
3. [x] Clip-1 gate enforcement validated at 100%.
4. [x] Retry/failure visibility criteria validated.
5. [x] Sign-off report captured (`docs/PHASE1_SIGNOFF_REPORT_2026-04-22.json`).

## Phase 2: authentication and RBAC

1. [x] Add auth persistence tables and migration (`0004_auth_phase2`).
2. [x] Implement signup/login/refresh/logout endpoints.
3. [x] Add access + refresh token lifecycle with refresh-token revocation.
4. [x] Implement team membership roles (`owner`, `admin`, `operator`, `viewer`).
5. [x] Enforce role checks on protected job and connector endpoints.
6. [x] Add auth/RBAC tests.

