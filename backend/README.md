# Virtual Twins Backend (Phase 1 Scaffold)

This folder contains the initial implementation scaffold for Phase 1 from `PROJECT_PLAN.md`.

## Chosen stack (initial lock)

- Runtime: Python 3.11+
- API: FastAPI
- Validation: Pydantic v2
- Queue/worker: pluggable queue with Redis or in-memory backend
- Database target: PostgreSQL (with in-memory option for fast iteration)
- Migrations: Alembic baseline included

## Implemented in this step

- Architecture lock document at `docs/ARCHITECTURE_LOCK.md`
- Initial schema draft at `backend/schema_v1.sql`
- Job state machine and run event model
- Worker skeleton with queued job execution hook
- First API endpoints:
  - `POST /v1/jobs`
  - `POST /v1/jobs/{job_id}/approvals/clip-1`
  - `GET /v1/jobs/{job_id}/events`

## Run locally

From repository root:

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Install development tools:

```bash
pip install -r backend/requirements-dev.txt
```

Then open:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## Storage backends

- Default: in-memory (`VT_STORAGE_BACKEND=memory`)
- PostgreSQL: set `VT_STORAGE_BACKEND=postgres` and `DATABASE_URL`

Example:

```bash
set VT_STORAGE_BACKEND=postgres
set DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/virtual_twins
```

## Migrations

From `backend` directory:

```bash
alembic upgrade head
```

## Queue backends

- Default: in-memory (`VT_QUEUE_BACKEND=memory`)
- Redis: set `VT_QUEUE_BACKEND=redis` and `REDIS_URL`

Example:

```bash
set VT_QUEUE_BACKEND=redis
set REDIS_URL=redis://localhost:6379/0
set VT_RETRY_MAX_ATTEMPTS=3
set VT_RETRY_BASE_SECONDS=2
```

Start API:

```bash
uvicorn backend.app.main:app --reload
```

Start worker loop in another terminal:

```bash
python -m backend.app.worker_runner
```

## Notes

This is still a delivery scaffold, not production-hardening yet.

- Retry/DLQ baseline is implemented in `backend/app/worker_runner.py`.
- Connector persistence baseline is implemented in `backend/app/connector_store.py`.

## Google Drive connector POC

Configured endpoints:

- `POST /v1/connectors/google-drive/oauth/start`
- `GET /v1/connectors/google-drive/oauth/callback`
- `POST /v1/connectors/google-drive/sync`
- `GET /v1/connectors/google-drive/sync/{sync_job_id}`

Required env values for real OAuth integration (stubbed in this POC):

```bash
set GOOGLE_CLIENT_ID=your_google_client_id
set GOOGLE_CLIENT_SECRET=your_google_client_secret
set GOOGLE_REDIRECT_URI=http://localhost:8000/v1/connectors/google-drive/oauth/callback
```

Current behavior:

- OAuth token exchange uses Google token endpoint.
- Drive folder scan uses Drive Files API with pagination token passthrough.
- On `401/403`, connector attempts refresh-token flow and retries once.
- When `VT_STORAGE_BACKEND=postgres`, connector state is persisted in:
  - `connector_oauth_states`
  - `asset_sources`
  - `asset_sync_jobs`
  - `connector_assets`

Additional migration:

- `0003_source_refresh_tokens` adds `refresh_token` and `access_token_expires_at` to `asset_sources`.

## Internal pilot harness

Run the scripted 20s + 30s internal pilot:

```bash
python -m backend.scripts.run_internal_pilot
```

Pilot run instructions and criteria:

- `docs/PILOT_RUNBOOK.md`

Batch pilot for Phase 1 exit criteria:

```bash
python -m backend.scripts.run_phase1_pilot_batch
```

Latest sign-off artifact:

- `docs/PHASE1_SIGNOFF_REPORT_2026-04-22.json`

## Observability baseline

New endpoints:

- `GET /metrics` for counters, gauges, and average timers.
- `GET /v1/ops/alerts` for threshold-based alert checks.

Configured alert thresholds (defaults shown):

```bash
set VT_ALERT_TERMINAL_FAILURES=1
set VT_ALERT_RETRIES=5
set VT_ALERT_API_5XX=1
```

Telemetry currently tracks:

- API request count, status buckets, latency
- Worker task count, success/failure, retries, terminal failures, latency

## CI and quality gates

Run local CI checks:

```bash
python -m backend.scripts.run_ci_checks
```

GitHub Actions workflow:

- `.github/workflows/backend-ci.yml`
- Runs lint (`ruff`) and unit tests on backend changes.

## API hardening baseline

- Error responses use a standard envelope:
  - `{"error": {"code": "...", "message": "...", "details": {...}}}`
- `POST /v1/jobs` idempotency behavior:
  - First request with key returns `201` and `idempotency_replayed=false`
  - Replay with same `(team_id, idempotency_key)` returns `200` and `idempotency_replayed=true`

## Phase 2 auth and RBAC

Auth endpoints:

- `POST /v1/auth/signup`
- `POST /v1/auth/login`
- `POST /v1/auth/refresh`
- `POST /v1/auth/logout`

Roles supported:

- `owner`
- `admin`
- `operator`
- `viewer`

Protected endpoint behavior:

- Job creation and clip approval require `owner|admin|operator`.
- Job event history and connector sync status allow `viewer` read access.
- Cross-team access is blocked even with valid tokens.

Auth env vars:

```bash
set VT_AUTH_JWT_SECRET=change-me
set VT_AUTH_ACCESS_TTL_MINUTES=30
set VT_AUTH_REFRESH_TTL_DAYS=14
```

CORS env var (for browser frontend):

```bash
set VT_CORS_ORIGINS=http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:3000,http://localhost:3000
```

Migration:

- `0004_auth_phase2` adds `teams`, `users`, `team_memberships`, `auth_refresh_tokens`.
