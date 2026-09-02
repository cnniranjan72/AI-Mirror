-- AIMirror V18: the accuracy ledger.
--
-- The product's argument is that a system which profiles people should be
-- accountable for whether it is right. That argument only holds if AIMirror
-- submits to it, so this table records the user's verdict on each claim the
-- system made about them.
--
-- confidence_at_verdict is stored ON PURPOSE rather than joined from the
-- source row. Calibration asks "when this system said 0.8, was it right 80%
-- of the time?", which is a question about what it claimed AT THE TIME. The
-- pipeline recomputes inferences and their confidences on every run, so a
-- join would silently rewrite history and make the system look better (or
-- worse) than it was. Copying the value freezes the claim being scored.

CREATE TABLE IF NOT EXISTS claim_verdicts (
    id                    BIGSERIAL PRIMARY KEY,
    user_id               TEXT NOT NULL,

    -- Which claim. claim_type says which table claim_id points into; the
    -- source row may be regenerated or deleted later, which is fine — the
    -- ledger is a record of what was said and what the user answered.
    claim_type            TEXT NOT NULL CHECK (claim_type IN ('inference', 'reflection')),
    claim_id              TEXT NOT NULL,

    -- The user's answer. 'unsure' is recorded but excluded from scoring: it
    -- is a real answer ("I can't tell"), not a missing one, and dropping it
    -- silently would overstate how often people engaged.
    verdict               TEXT NOT NULL CHECK (verdict IN ('right', 'wrong', 'unsure')),

    confidence_at_verdict DOUBLE PRECISION NOT NULL
                            CHECK (confidence_at_verdict >= 0 AND confidence_at_verdict <= 1),

    -- What the claim actually said, frozen. Lets the ledger stay readable
    -- after the pipeline regenerates or drops the source row.
    claim_label           TEXT,

    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One standing verdict per claim per user. Changing your mind updates the
    -- row rather than stacking a second vote, so nobody can inflate the
    -- sample by clicking repeatedly.
    UNIQUE (user_id, claim_type, claim_id)
);

CREATE INDEX IF NOT EXISTS idx_claim_verdicts_user ON claim_verdicts (user_id);
CREATE INDEX IF NOT EXISTS idx_claim_verdicts_user_created
    ON claim_verdicts (user_id, created_at DESC);
