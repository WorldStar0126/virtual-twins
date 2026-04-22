-- Virtual Twins schema draft (Phase 1 minimum model)
-- Target database: PostgreSQL

CREATE TABLE teams (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
  id UUID PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE clients (
  id UUID PRIMARY KEY,
  team_id UUID NOT NULL REFERENCES teams(id),
  slug TEXT NOT NULL,
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(team_id, slug)
);

CREATE TABLE jobs (
  id UUID PRIMARY KEY,
  team_id UUID NOT NULL REFERENCES teams(id),
  client_id UUID NOT NULL REFERENCES clients(id),
  format_seconds INT NOT NULL CHECK (format_seconds IN (20, 30)),
  status TEXT NOT NULL,
  stage TEXT NOT NULL,
  idempotency_key TEXT,
  created_by_user_id UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(team_id, idempotency_key)
);

CREATE TABLE job_clips (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES jobs(id),
  clip_index INT NOT NULL,
  status TEXT NOT NULL,
  output_uri TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(job_id, clip_index)
);

CREATE TABLE approvals (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES jobs(id),
  clip_index INT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
  reviewer_user_id UUID REFERENCES users(id),
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE end_cards (
  id UUID PRIMARY KEY,
  team_id UUID NOT NULL REFERENCES teams(id),
  client_id UUID REFERENCES clients(id),
  name TEXT NOT NULL,
  asset_uri TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE assets (
  id UUID PRIMARY KEY,
  team_id UUID NOT NULL REFERENCES teams(id),
  client_id UUID REFERENCES clients(id),
  asset_type TEXT NOT NULL,
  source_uri TEXT,
  storage_uri TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE asset_sources (
  id UUID PRIMARY KEY,
  team_id UUID NOT NULL REFERENCES teams(id),
  provider TEXT NOT NULL,
  external_account_id TEXT,
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE asset_versions (
  id UUID PRIMARY KEY,
  asset_id UUID NOT NULL REFERENCES assets(id),
  content_hash TEXT NOT NULL,
  storage_uri TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE asset_sync_jobs (
  id UUID PRIMARY KEY,
  asset_source_id UUID NOT NULL REFERENCES asset_sources(id),
  status TEXT NOT NULL,
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  error_message TEXT
);

CREATE TABLE run_events (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES jobs(id),
  event_type TEXT NOT NULL,
  trace_id TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE usage_events (
  id UUID PRIMARY KEY,
  team_id UUID NOT NULL REFERENCES teams(id),
  job_id UUID REFERENCES jobs(id),
  event_type TEXT NOT NULL,
  quantity NUMERIC(12, 4) NOT NULL,
  billable BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
