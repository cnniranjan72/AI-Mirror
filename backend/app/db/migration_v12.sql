-- Migration V12: error_events — server-side record of unhandled exceptions
-- and extension extraction failures, so failures are visible (queryable via
-- GET /admin/errors) instead of only living in a stdout log no one is
-- watching.
CREATE TABLE IF NOT EXISTS error_events (
    id SERIAL PRIMARY KEY,
    trace_id TEXT,
    user_id TEXT,
    path TEXT,
    method TEXT,
    error_type TEXT NOT NULL,
    message TEXT,
    stack TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_error_events_created ON error_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_error_events_type ON error_events(error_type);
