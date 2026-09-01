-- Migration V17: search signals — evidence that the user went LOOKING for
-- something, as opposed to being shown it.
--
-- Stored separately from events on purpose. A search is not a content view: it
-- has a query string but no creator, no watch time and no engagement. Filing
-- searches as events would inflate event counts, manufacture behaviour objects
-- out of query text, and quietly corrupt every watch statistic the identity is
-- built from.
--
-- This is the only strong deliberate-intent signal available. Of the flags
-- already on events, `following` defaults to true (so it is a default, not an
-- observation), and liked/saved/shared/commented are present on ~1% of real
-- rows. Without search history, "did you choose this?" is unanswerable.
CREATE TABLE IF NOT EXISTS search_signals (
    id           SERIAL PRIMARY KEY,
    user_id      TEXT NOT NULL,
    platform     TEXT NOT NULL,             -- 'youtube' | 'google' | 'instagram'
    query        TEXT NOT NULL,             -- normalised, used for matching
    raw_query    TEXT NOT NULL,             -- as the export wrote it, for citation
    searched_at  TIMESTAMPTZ,
    source_file  TEXT,
    imported_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_search_signals_user
    ON search_signals (user_id, platform);

-- Re-importing an export must not multiply the same search. The timestamp is
-- part of identity because searching the same term twice is two real signals.
CREATE UNIQUE INDEX IF NOT EXISTS idx_search_signals_unique
    ON search_signals (user_id, platform, query, searched_at);
