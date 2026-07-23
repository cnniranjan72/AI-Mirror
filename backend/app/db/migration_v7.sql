-- Migration V7: persistent chat conversation memory.
-- Each turn (user + assistant) is one row, grouped by conversation_id, so the
-- character can recall earlier turns within a conversation. Idempotent.

CREATE TABLE IF NOT EXISTS chat_messages (
    id              BIGSERIAL PRIMARY KEY,
    user_id         TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL,          -- 'user' | 'assistant'
    content         TEXT NOT NULL,
    trace_id        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_convo
    ON chat_messages (user_id, conversation_id, created_at);
