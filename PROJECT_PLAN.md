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