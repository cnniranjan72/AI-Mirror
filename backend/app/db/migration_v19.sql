-- AIMirror V19: a stable identity for a claim, so corrections survive.
--
-- inference_id is minted as
--     inference_{rule_name}_{context_id}_{utcnow().timestamp()}
-- and context_id is itself ctx_{timestamp}, so NOTHING in it is stable. Every
-- ingest that produces inferences runs `DELETE FROM inferences WHERE user_id`
-- and re-inserts the whole set (pipeline/orchestrator.py) with fresh ids.
--
-- The Accuracy Ledger keyed verdicts on inference_id, which meant a user could
-- answer a claim, the pipeline could re-run, and the identical claim would come
-- back as unanswered - forever. Demonstrated end to end before this migration:
-- same rule, same label, new id, and /calibration/open asks again.
--
-- claim_key is the claim's CONTENT instead: its rule plus what it asserts.
-- Checked against production data first - 44 inference rows collapse to 7
-- distinct (rule_name, label) pairs, and no label contains a digit, so counts
-- cannot churn the key. rule_name alone would be too coarse: EngagementDepthRule
-- emits both "Engagement style is deep, attentive" and "... quick, scanning",
-- and denying one must not silently deny the other.
--
-- md5 is a fingerprint here, not a security primitive - it only needs to be
-- deterministic and identical in Postgres and Python.

ALTER TABLE inferences      ADD COLUMN IF NOT EXISTS claim_key TEXT;
ALTER TABLE claim_verdicts  ADD COLUMN IF NOT EXISTS claim_key TEXT;

-- Superseded by migration_v20, which makes inferences.claim_key a GENERATED
-- column. run_schema() replays every migration on every startup, and this
-- UPDATE then fails with "column can only be updated to DEFAULT" — aborting
-- the whole schema run. Guarded so both orderings work: on a fresh database
-- this backfills the plain column V19 just added, and once V20 has converted
-- it Postgres maintains the value and this is correctly a no-op.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'inferences'
           AND column_name = 'claim_key'
           AND is_generated = 'ALWAYS'
    ) THEN
        -- Must match app/services/calibration.py:claim_key() exactly.
        UPDATE inferences
           SET claim_key = md5(lower(btrim(coalesce(rule_name, ''))) || '|' ||
                               lower(btrim(coalesce(label, ''))))
         WHERE claim_key IS NULL;
    END IF;
END $$;

-- Backfill existing verdicts by joining back to the row they were recorded
-- against, where it still exists. Verdicts whose inference has already been
-- regenerated away cannot be recovered - they keep scoring (the ledger stores
-- confidence and label at verdict time) but will not suppress a future claim.
UPDATE claim_verdicts v
   SET claim_key = i.claim_key
  FROM inferences i
 WHERE v.claim_key IS NULL
   AND v.claim_type = 'inference'
   AND v.claim_id = i.inference_id
   AND v.user_id = i.user_id;

CREATE INDEX IF NOT EXISTS idx_inferences_claim_key
    ON inferences (user_id, claim_key);
CREATE INDEX IF NOT EXISTS idx_claim_verdicts_claim_key
    ON claim_verdicts (user_id, claim_key);
