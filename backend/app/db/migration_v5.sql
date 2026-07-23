-- Migration V5: persist richer engagement signal captured by the extension.
-- Idempotent — safe to run on every startup.

ALTER TABLE events ADD COLUMN IF NOT EXISTS liked       BOOLEAN DEFAULT FALSE;
ALTER TABLE events ADD COLUMN IF NOT EXISTS saved       BOOLEAN DEFAULT FALSE;
ALTER TABLE events ADD COLUMN IF NOT EXISTS shared      BOOLEAN DEFAULT FALSE;
ALTER TABLE events ADD COLUMN IF NOT EXISTS commented   BOOLEAN DEFAULT FALSE;
ALTER TABLE events ADD COLUMN IF NOT EXISTS following   BOOLEAN DEFAULT TRUE;
ALTER TABLE events ADD COLUMN IF NOT EXISTS audio_id    TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN IF NOT EXISTS profile_url TEXT DEFAULT '';

-- Common analytics filters over the new signal.
CREATE INDEX IF NOT EXISTS idx_events_user_liked ON events (user_id, liked);
