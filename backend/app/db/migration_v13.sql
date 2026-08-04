-- Migration V13: organizations — a seat/roster grouping layer above
-- individual user accounts (workspaces, in Slack/Notion terms).
--
-- Deliberate privacy boundary: this schema gives an org owner NO path to
-- another member's cognitive data. Every table an org endpoint touches is
-- users/organizations/org_invites only — never behavior_objects, evidence,
-- inferences, reflections, self_models, or identity_snapshots. Those stay
-- scoped by user_id exactly as before, enforced the same way (enforce_
-- user_match/enforce_write_match). An org only groups accounts for shared
-- billing/roster/invite management, the same way a Slack workspace admin
-- manages seats without reading your DMs.
CREATE TABLE IF NOT EXISTS organizations (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    owner_username TEXT NOT NULL REFERENCES users(username),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS org_invites (
    code TEXT PRIMARY KEY,
    org_id BIGINT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    max_uses INTEGER,
    use_count INTEGER NOT NULL DEFAULT 0
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS org_id BIGINT REFERENCES organizations(id);
ALTER TABLE users ADD COLUMN IF NOT EXISTS org_role TEXT;  -- 'owner' | 'member', NULL when unaffiliated

CREATE INDEX IF NOT EXISTS idx_users_org_id ON users(org_id);
CREATE INDEX IF NOT EXISTS idx_org_invites_org_id ON org_invites(org_id);
