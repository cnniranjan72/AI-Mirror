-- AIMirror V10: multi-platform source tagging on raw events.
-- Idempotent -- safe to run on every startup.

ALTER TABLE events ADD COLUMN IF NOT EXISTS platform TEXT DEFAULT 'instagram';
ALTER TABLE events ADD COLUMN IF NOT EXISTS surface  TEXT DEFAULT '';

-- Backfill: everything captured before V10 came from the Instagram extension.
UPDATE events SET platform = 'instagram' WHERE platform IS NULL;

CREATE INDEX IF NOT EXISTS idx_events_user_platform ON events (user_id, platform);
