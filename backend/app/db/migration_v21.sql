-- AIMirror V21: one verdict per logical claim, not per inference row.
--
-- claim_verdicts was UNIQUE on (user_id, claim_type, claim_id) and
-- record_verdict used that as its ON CONFLICT target. claim_id is an
-- inference_id, and the pipeline regenerates every inference_id on every
-- ingest, so changing your mind about a claim AFTER a re-run did not update
-- the existing verdict — it inserted a second one against the new id.
--
-- Two consequences, both silent:
--   * contested_claim_keys asks whether ANY verdict for the key says "wrong",
--     so the stale row kept suppressing a claim the user had just restored.
--     The reverse button returned 200 and did nothing.
--   * the same logical claim then contributed two scored answers to the
--     calibration report, quietly double-counting it.
--
-- The logical identity is claim_key, so that is what must be unique. claim_id
-- is kept as a record of which row was on screen when they answered.
--
-- NULL claim_key rows are left alone: those are verdicts whose inference had
-- already been regenerated away before V19 backfilled, so there is nothing to
-- match them on. Postgres allows repeated NULLs in a unique index, which is
-- the behaviour wanted here.

-- Deduplicate before constraining: keep the most recently updated verdict for
-- each logical claim, which is the user's current answer.
DELETE FROM claim_verdicts a
 USING claim_verdicts b
 WHERE a.claim_key IS NOT NULL
   AND a.user_id    = b.user_id
   AND a.claim_type = b.claim_type
   AND a.claim_key  = b.claim_key
   AND (a.updated_at, a.id) < (b.updated_at, b.id);

ALTER TABLE claim_verdicts
    DROP CONSTRAINT IF EXISTS claim_verdicts_user_id_claim_type_claim_id_key;

CREATE UNIQUE INDEX IF NOT EXISTS idx_claim_verdicts_logical_claim
    ON claim_verdicts (user_id, claim_type, claim_key)
 WHERE claim_key IS NOT NULL;
