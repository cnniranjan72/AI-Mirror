-- AIMirror V23: make the rollback the architecture claims actually exist.
--
-- The paper lists "identity snapshots with rollback" as a core contribution and
-- says a snapshot "can be rolled back if later evidence invalidates the drift".
-- IdentityEvolutionEngine.rollback_to_snapshot logs "Rolled back to snapshot X",
-- returns None, and carries the comment "Placeholder - would return
-- reconstructed identity". Nothing calls it. Across 35 stored snapshots
-- is_active was TRUE on every one; the column, its partial index and
-- valid_until had never been used to supersede anything.
--
-- Restoring by rewriting the identities row would not work and would be worse
-- than not offering it. Identity construction is from scratch on every ingest:
-- existing_identity supplies only the id and the version counter, and every
-- sub-profile is recomputed from the behaviour objects. A restored row would be
-- silently overwritten the next time the user sent anything, so the button
-- would appear to work and then quietly undo itself.
--
-- What does hold is a pin. Architectural invariant 2 is that user-facing reads
-- come from frozen snapshots rather than the live identity, so choosing which
-- snapshot is the frozen one is a real and durable answer to "the model has
-- drifted somewhere I do not recognise". The live identity carries on evolving
-- underneath, untouched, and unpinning returns to it.
--
-- A separate table rather than reusing is_active, for two reasons. is_active
-- defaults TRUE on every row, so its meaning would have to be inverted for
-- existing data, and a pin is per-user state while is_active reads as a
-- property of the snapshot. Keying on user_id also covers the unauthenticated
-- demo_* accounts that have no users row, as collection_settings does.

CREATE TABLE IF NOT EXISTS identity_pins (
    user_id      TEXT PRIMARY KEY,

    -- No foreign key. cleanup_old_snapshots deletes all but the newest twenty,
    -- and a cascade would silently discard the pin along with the snapshot.
    -- The reader resolves a dangling pin by falling back to the latest and
    -- saying so, which is recoverable; a vanished pin is not.
    snapshot_id  TEXT NOT NULL,

    pinned_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Why the person went back. Their words, shown beside the pin, because a
    -- restore point with no reason is impossible to review later.
    reason       TEXT,

    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_identity_pins_snapshot
    ON identity_pins (snapshot_id);
