-- Core schema for Code Kitchen v3.
-- Dedup guarantee for ingested jobs lives here (unique constraint), not in a
-- separate cache -- see ADR-03 in the architecture report.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto; -- for gen_random_uuid()

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT NOT NULL UNIQUE,
    display_name    TEXT,
    profile         JSONB NOT NULL DEFAULT '{}'::jsonb, -- skills, experience, location, preferences
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Embedding dimension matches Vertex AI text-embedding-004 / Gemini embedding-001 (768).
CREATE TABLE jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source          TEXT NOT NULL,           -- 'indeed' | 'linkedin'
    external_id     TEXT NOT NULL,           -- id from the source platform
    title           TEXT NOT NULL,
    company         TEXT NOT NULL,
    location        TEXT,
    description     TEXT NOT NULL,
    url             TEXT,
    posted_at       TIMESTAMPTZ,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    embedding       vector(768),
    raw_ref         TEXT,                    -- pointer to the raw payload (GCS path or local file)
    UNIQUE (source, external_id)
);

-- No ANN index (ivfflat/hnsw) yet -- pgvector does exact nearest-neighbor
-- scans just fine at this scale, and an ivfflat index built on a handful of
-- rows actively hurts recall (too many empty lists for `probes=1` to find
-- real neighbors). Add one once the ADR-02 migration trigger is close
-- (jobs approaching 5M rows or p95 query latency approaching 300ms) --
-- until then it's premature index tuning for data that doesn't exist yet.
CREATE INDEX jobs_ingested_at_idx ON jobs (ingested_at DESC);

CREATE TABLE matches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    similarity      REAL NOT NULL,
    rationale       TEXT,                    -- Gemini Flash explanation of the fit
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, job_id)
);

CREATE TABLE applications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    resume_text     TEXT,
    resume_ref      TEXT,                    -- storage path for the generated resume file
    status          TEXT NOT NULL DEFAULT 'draft', -- draft | applied | responded | rejected | offer
    applied_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE outreach (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id          UUID REFERENCES jobs(id) ON DELETE SET NULL,
    contact_id      UUID, -- references referral_contacts(id), no FK across schemas by design
    message         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending_review', -- pending_review | approved | sent | declined
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at     TIMESTAMPTZ,
    sent_at         TIMESTAMPTZ
);

CREATE TABLE jobs_raw_dlq (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source          TEXT NOT NULL,
    payload         JSONB NOT NULL,
    error           TEXT NOT NULL,
    failed_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ingestion_heartbeats (
    source          TEXT PRIMARY KEY,
    last_success_at TIMESTAMPTZ,
    last_record_count INTEGER,
    consecutive_empty_runs INTEGER NOT NULL DEFAULT 0
);
