-- Per-user quota tracking for ai-api. Without this, cost/abuse exposure on
-- the Gemini-facing endpoints scales with active users x sessions with no
-- ceiling -- one of The Fool's findings against v2.

CREATE TABLE api_quota_usage (
    user_email      TEXT NOT NULL,
    endpoint        TEXT NOT NULL,           -- 'match' | 'generate'
    window_start    TIMESTAMPTZ NOT NULL,    -- truncated to the hour (match) or day (generate)
    request_count   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_email, endpoint, window_start)
);
