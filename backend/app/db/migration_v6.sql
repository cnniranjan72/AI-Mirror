-- Migration V6: reinforcement-learning policy store (contextual bandit).
-- One row per (context, action) holding the learned action-value Q and its
-- sample count. Idempotent.

CREATE TABLE IF NOT EXISTS rl_policy (
    context_key TEXT    NOT NULL,
    action_id   TEXT    NOT NULL,
    q_value     DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    n           INTEGER NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (context_key, action_id)
);

CREATE INDEX IF NOT EXISTS idx_rl_policy_context ON rl_policy (context_key);
