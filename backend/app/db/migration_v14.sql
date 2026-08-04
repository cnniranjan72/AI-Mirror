-- Migration V14: research_opt_in — a user-controlled flag gating inclusion
-- in the de-identified bulk research export (GET /research/export). Off by
-- default: no one's behavioral data is exportable until they explicitly
-- turn this on from Settings.
ALTER TABLE users ADD COLUMN IF NOT EXISTS research_opt_in BOOLEAN NOT NULL DEFAULT FALSE;
