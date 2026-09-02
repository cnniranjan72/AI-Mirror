-- AIMirror V22: let a person stop the collection.
--
-- The product could already export everything it held and delete it, and could
-- opt out of research sharing. It could not be told to stop watching. For a
-- system whose entire argument is that people should have authority over
-- behavioural data collected about them, that is the one control that had to
-- exist: withdrawing consent is supposed to be as easy as giving it
-- (GDPR Art. 7(3)), and there was no way to withdraw it at all.
--
-- Kept in its own table rather than as a column on `users`, because most of
-- the accounts that send events have no `users` row: the extension posts
-- unauthenticated for demo_* ids, and those users need the switch just as
-- much. Keying on user_id covers both.
--
-- Pausing is not deleting. Events already stored stay stored, and the UI says
-- so - a control that silently discarded history would be a worse surprise
-- than one that does nothing.

CREATE TABLE IF NOT EXISTS collection_settings (
    user_id     TEXT PRIMARY KEY,
    paused      BOOLEAN NOT NULL DEFAULT FALSE,
    -- When the current pause began. Null whenever paused is false, so the UI
    -- can say "paused since 3 March" rather than just "paused".
    paused_at   TIMESTAMPTZ,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_collection_settings_paused
    ON collection_settings (user_id) WHERE paused;
