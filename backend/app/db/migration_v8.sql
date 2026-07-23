-- Migration V8: user accounts for authentication + multi-user isolation.
-- Additive only — existing user_id-keyed data is untouched; a user's user_id is
-- simply their username. Idempotent.

CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    email         TEXT,
    password_hash TEXT NOT NULL,   -- pbkdf2 hash
    salt          TEXT NOT NULL,
    display_name  TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
