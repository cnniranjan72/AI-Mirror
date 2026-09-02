-- AIMirror V20: make claim_key impossible to get wrong.
--
-- V19 added inferences.claim_key as an ordinary column that every INSERT had
-- to remember to populate. Two failure modes followed immediately:
--
--   * list_open_claims requires claim_key IS NOT NULL, so a row inserted
--     without it is silently invisible to the ledger — the claim is never
--     offered for review and nothing errors. A test fixture that predated the
--     column caught this; a new code path would not have.
--   * the value had to be computed identically in Python (for new rows) and
--     in SQL (for the V19 backfill). Two expressions that must agree forever,
--     where drift produces no error and just quietly stops corrections from
--     binding.
--
-- A generated column removes both. Postgres computes it from the row, so no
-- insert can omit it and there is only one definition of what a claim_key is.
--
-- claim_verdicts.claim_key stays an ORDINARY column on purpose: it records the
-- key as it was when the user answered, and the inference row it came from may
-- since have been regenerated or deleted. That one is history, not a
-- derivation.

ALTER TABLE inferences DROP COLUMN IF EXISTS claim_key;

ALTER TABLE inferences
    ADD COLUMN claim_key TEXT
    GENERATED ALWAYS AS (
        md5(lower(btrim(coalesce(rule_name, ''))) || '|' ||
            lower(btrim(coalesce(label, ''))))
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_inferences_claim_key
    ON inferences (user_id, claim_key);
