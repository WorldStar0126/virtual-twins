# Virtual Twins - Senior Technical Delivery Plan

## Executive Goal

Convert the current prototype into a production internal platform first, then a secure multi-tenant SaaS with authentication, permission management, and usage-based billing.

## Priority Order (Client-Aligned)

1. Complete internal backend system (core workflow engine).
2. Add authentication and permission management.
3. Add subscription and usage-based billing.
4. Expand client-facing features and automation.

---

## Phase 0 - Discovery and Architecture Lock

### Objective

Lock decisions once to avoid rework during implementation.

### Decisions to finalize

- Backend stack and runtime.
- Database choice and migration tool.
- Queue/worker technology.
- Cloud storage provider for media assets.
- Identity model (team/workspace + role model).
- Billing provider and pricing model.

### Deliverable

Signed-off architecture and execution scope document.

---

## Phase 1 - Internal Backend System (Highest Priority)

### Objective

Build the internal production engine the client requested: reliable job orchestration for 20s/30s generation with approval gate, retries, and run observability.

### Functional scope

- Job creation for:
  - 20s mode = 2 clips + end card
  - 30s mode = 3 clips + end card
- Enforce clip 1 approval gate before clip 2/3 processing.
- End card selection from reusable pools (per client/sponsor).
- Retry policy with capped attempts and failure states.
- Deterministic run logs and event history.
- Downloadable outputs and asset references.

### Backend architecture scope

- API service:
  - Jobs, clips, approvals, end cards, run events, assets.
- Worker service:
  - Async clip generation, retries, status transitions.
- Queue:
  - Priority + delayed retry support.
- Storage:
  - Uploads, generated clips, final assembled output.
- Asset management service:
  - Connector-based ingestion (Google Drive first, then Dropbox/S3/local).
  - Asset metadata indexing (owner, client, campaign, tags, duration, format).
  - Versioning and deduplication (hash-based).
  - Folder mapping rules (drive folders to internal clients/campaigns).
  - Sync jobs (scheduled + on-demand) with failure retry.
  - Access policy enforcement by workspace/role.
- State tracking:
  - Job state machine and audit history.

### Minimum data model (v1)

- `teams`
- `users` (created now even if auth UI comes later)
- `clients`
- `jobs`
- `job_clips`
- `approvals`
- `end_cards`
- `assets`
- `asset_sources` (Google Drive, S3, etc.)
- `asset_versions`
- `asset_sync_jobs`
- `run_events`
- `usage_events` (foundation for billing phase)

### Non-functional requirements

- Idempotent job processing.
- Structured logging with trace/job IDs.
- Metrics:
  - generation success rate
  - average processing latency
  - retry and failure rates
- Basic alerting on worker failures and stuck jobs.
- Connector resilience:
  - OAuth token refresh handling.
  - API rate-limit backoff.
  - Partial-sync recovery without duplication.

### Deliverable

Internal backend system is production-capable for operator use, with API + workers + queue + storage + full run tracking.

### Asset management deliverable (client request)

- Google Drive integration for ingesting and syncing source assets.
- Unified internal asset library with searchable metadata and version history.
- Reliable sync observability (last sync status, errors, retries).

### Exit criteria

- 95%+ job completion in controlled pilot.
- Clip 1 approval gate enforced 100% of runs.
- All retries/failures fully visible in run events.
- Google Drive asset sync works with deterministic mapping and retry-safe behavior.

---

## Phase 2 - Authentication and Permission Management

### Objective

Secure the platform for multiple users with controlled access by role and workspace.

### Functional scope

- Login, signup, password reset.
- Session/token management.
- Workspace/team membership model.
- Role-based access control (RBAC):
  - `owner`
  - `admin`
  - `operator`
  - `viewer` (optional, read-only)

### Security scope

- Password hashing (argon2 or bcrypt with strong params).
- Short-lived access token + refresh token strategy.
- Rate limiting on auth endpoints.
- Email verification (recommended for production).
- Audit trail for sensitive actions:
  - login attempts
  - role changes
  - approval decisions
  - billing-impacting actions

### Permission matrix (minimum)

- Owner/Admin: manage users, plans, all jobs.
- Operator: create and operate jobs, approve clip gates.
- Viewer: read-only visibility for status and outputs.

### Deliverable

Secure user authentication and role-based permission system integrated with backend APIs.

### Exit criteria

- Unauthorized access blocked for all protected endpoints.
- Role constraints enforced in API and UI.

---

## Phase 3 - Subscription and Usage Billing

### Objective

Enable monetization with subscription + controlled usage accounting.

### Functional scope

- Payment provider integration (Stripe recommended).
- Subscription lifecycle:
  - trial
  - active
  - past_due
  - canceled
- Checkout and customer portal.
- Plan model:
  - monthly base allowance
  - overage pricing or credit packs

### Usage metering scope

- Track billable events:
  - clip generation attempts
  - successful outputs
  - retries (billable or non-billable rule explicit)
- Monthly usage aggregation.
- Soft limit warnings and hard limit enforcement.
- Billing ledger for disputes and reconciliation.

### Compliance and reliability

- Webhook signature verification.
- Idempotent webhook handlers.
- Invoice and payment status sync jobs.

### Deliverable

Each workspace can subscribe, consume usage, and be billed with transparent usage records.

### Exit criteria

- End-to-end paid flow validated in staging and production pilot.
- Billing ledger matches provider invoices.

---

## Phase 4 - Client Portal and Product Expansion

### Objective

Expose controlled client-facing workflows and performance visibility.

### Scope

- Client portal for job status, approvals, and asset downloads.
- Asset library UI:
  - browse/search/filter synced assets
  - connect/disconnect source connectors
  - manual re-sync and sync status visibility
- Notifications (email/Slack) for stage transitions and failures.
- Analytics baseline:
  - success/failure trends
  - turnaround time
  - cost per output
  - sponsor/end card performance
- Optional first social publishing integrations.

### Deliverable

Revenue-ready external experience for clients with operational transparency.

---

## Cross-Cutting Engineering Standards (apply from Phase 1)

- API versioning from day one (`/v1`).
- DB migrations with rollback support.
- Environment isolation: dev/staging/prod.
- Error taxonomy and standardized API responses.
- CI/CD:
  - test + lint gates
  - staged deployment
- Observability:
  - logs, metrics, alerts, dashboards
- Backups and restore drill for critical data.

---

## Risks and Mitigation

- Workflow instability from async complexity:
  - mitigate with state machine, idempotency keys, dead-letter queue.
- Billing disputes:
  - mitigate with immutable usage events and clear billable rules.
- Permission bugs:
  - mitigate with server-side authorization checks and permission tests.
- External connector failures or quota limits:
  - mitigate with connector abstraction, retry/backoff, and fallback ingestion path.
- Scope creep:
  - mitigate with strict phase gates and acceptance criteria per phase.

---

## Delivery Sequence

- Phase 0: Discovery and architecture lock
- Phase 1: Internal backend system
- Phase 2: Authentication and permission management
- Phase 3: Subscription and usage billing
- Phase 4: Client portal and product expansion

---

## What Starts Immediately (Action Plan for This Week)

1. Finalize architecture and stack decisions.
2. Define database schema and create initial migrations.
3. Implement job lifecycle state machine and run event model.
4. Stand up queue + worker service skeleton.
5. Build first API endpoints:
  - create job
  - submit clip 1 approval
  - fetch run event history
6. Build Google Drive connector POC:
  - OAuth connection
  - folder scan
  - asset metadata ingestion
  - incremental sync job
7. Run first internal pilot with 20s flow, then 30s flow.

---

## Client Communication Summary

The delivery will proceed in strict priority order:
backend internal system first, then auth/permissions, then billing/usage, then client-facing expansion. This minimizes risk, enables immediate operational value, and creates a stable foundation for monetization.

---

## Combined Monorepo Execution Plan (Web + API)

### Why this section exists

The phased plan above is directionally correct, but the current monorepo implementation is in an in-between state:

- `apps/web` is a static React prototype currently driven by mock data.
- `apps/api` contains real fal pipeline tools plus an `api_server.py` FastAPI scaffold that is not yet the full production architecture in Phase 1.

This section translates the strategy into executable work against this repository as it exists today.

### Current baseline in this repo

#### Backend (`apps/api`)

- Existing:
  - CLI pipeline tools (`upload_assets.py`, `generate_video.py`, `download_video.py`, etc.)
  - FastAPI scaffold (`api_server.py`) with:
    - `v1` style endpoints for clients/jobs/events/approval
    - clip-1 approval gate behavior
    - simple event logging and local JSON persistence in `.tmp/operator_db.json`
- Gaps vs target Phase 1:
  - No real DB migrations or persistent relational schema
  - No queue + worker separation (thread-based async only)
  - No cloud object storage abstraction
  - No auth/RBAC enforcement
  - No robust retry orchestration and alerting

#### Frontend (`apps/web`)

- Existing:
  - Operator UI shell and screens (`dashboard`, `job-new`, `clip-approve`, `assembly`, etc.)
  - Mock data source in `data.jsx`
- Gaps vs target Phase 1/2:
  - No API client layer to consume backend endpoints
  - No auth/session/role-aware UX
  - No real run-event streaming or durable state handling

---

## Combined Delivery Map (Start Here)

### Combined Phase A - Local integration hardening (immediate)

Objective: make the current UI and API run together reliably and demonstrate the full 20s/30s operator flow locally.

Backend tasks:
- Add run command docs for `api_server.py` and align env requirements in `requirements.txt`.
- Normalize API contract for:
  - create job
  - list jobs
  - fetch events
  - approval decision
  - final assembly confirmation
- Add predictable error envelope and status code conventions.

Frontend tasks:
- Replace `data.jsx` mocks with a thin API service layer (toggleable mock mode).
- Wire screens to real endpoints:
  - dashboard/job history -> `/v1/jobs`
  - new job -> `POST /v1/jobs`
  - clip approval -> `POST /v1/jobs/{id}/approval`
  - timeline -> `/v1/jobs/{id}/events`
- Add polling + retry UX for long-running generation states.

Exit criteria:
- Operator can run a full job in local env using UI + API with real state changes.
- Clip 1 approval gate is enforced and visible in UI.
- Event timeline reflects backend run history for each job.

### Combined Phase B - Production backend foundation (maps to Phase 1)

Objective: evolve the scaffold into a true production internal backend.

Backend tasks:
- Introduce relational DB + migrations for:
  - teams, users, clients, jobs, job_clips, approvals, end_cards, assets, run_events, usage_events
- Split API and worker responsibilities; adopt queue for retries/delay.
- Implement deterministic job state machine with idempotency keys.
- Add object storage abstraction for generated artifacts.
- Build connector abstraction for asset ingestion (Google Drive first).

Frontend tasks:
- Introduce typed API contracts and stricter state management around job transitions.
- Add operator controls for retry, failure inspection, and stuck-job escalation.
- Surface asset-source status (sync state, last error, last successful sync).

Exit criteria:
- Controlled pilot reaches target completion SLO.
- Full run/event observability exists for every state transition.

### Combined Phase C - Auth/RBAC + billing + portal (maps to Phases 2-4)

Objective: layer security, monetization, and client-facing workflows on the stable core.

- Add auth/session and role checks in API and frontend route guards.
- Add usage metering and billing provider integration.
- Add external client portal surfaces once internal reliability goals are met.

---

## Runbook for Parallel Development (2 processes at once)

### Terminal 1 - Frontend

```bash
cd E:\_HC\_pylyp\virtual-twins-monorepo
npm install
npm run dev:web
```

### Terminal 2 - Backend

```bash
cd E:\_HC\_pylyp\virtual-twins-monorepo\apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Then run either:
- pipeline tools directly (`python tools/...`) for generation workflows, or
- API server (`uvicorn api_server:app --reload --port 8000`) when wiring frontend to backend.

---

## First Combined Sprint Backlog (implementation order)

1. Backend API contract freeze for jobs/events/approval.
2. Frontend API client module and environment-based base URL.
3. Replace dashboard/job/history/approval screens with live API data.
4. Add backend event/status normalization for reliable UI rendering.
5. Add smoke tests for:
   - create -> approve -> complete path
   - rejection path
   - failed job path and cleanup behavior
6. Demo end-to-end operator run using real assets in local environment.