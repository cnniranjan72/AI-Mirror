-- Migration V16: platform profile claims — what a platform asserts about the
-- user, as opposed to what the user actually did.
--
-- These rows are deliberately NOT events. An event is an observation of
-- behaviour; a claim is a third party's inference about a person, imported
-- verbatim from their own data export. Mixing them would let a platform's
-- assertion about someone become evidence for itself inside the very pipeline
-- meant to check it — the profile would end up confirming whatever it was
-- told, which is the one thing this table exists to prevent.
CREATE TABLE IF NOT EXISTS platform_profile_claims (
    id              SERIAL PRIMARY KEY,
    user_id         TEXT NOT NULL,
    platform        TEXT NOT NULL,              -- 'instagram' | 'youtube' | 'meta' | 'google'
    claim_type      TEXT NOT NULL DEFAULT 'ad_interest',
    label           TEXT NOT NULL,              -- normalised, used for matching
    raw_label       TEXT NOT NULL,              -- exactly as the export wrote it, for citation
    source_file     TEXT,                       -- which archive member it came from
    imported_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- A re-import of the same export must refresh the claim set rather than
-- multiply it; the API deletes by (user_id, platform) before inserting, and
-- this index is what makes that cheap.
CREATE INDEX IF NOT EXISTS idx_ppc_user_platform
    ON platform_profile_claims (user_id, platform);

-- The same interest can legitimately be claimed by two platforms, so identity
-- is (user, platform, type, label) rather than label alone.
CREATE UNIQUE INDEX IF NOT EXISTS idx_ppc_unique_claim
    ON platform_profile_claims (user_id, platform, claim_type, label);
