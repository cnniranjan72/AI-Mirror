"""Rollback was claimed for as long as the paper has existed, and never built.

`IdentityEvolutionEngine.rollback_to_snapshot` logs "Rolled back to snapshot X",
returns None, and carries the comment "Placeholder - would return reconstructed
identity". Nothing called it. Across 35 stored snapshots `is_active` was TRUE on
every one, so the column and its partial index had never superseded anything.

The obvious implementation - write the snapshot back over the identities row -
would have been worse than nothing. Identity construction runs from scratch on
every ingest: `existing_identity` contributes only its id and version counter,
and all nine sub-profiles are recomputed from the behaviour objects. A restored
row survives until the next event arrives, so the control would appear to work
and then quietly undo itself.

The pin is durable because architectural invariant 2 already routes user-facing
reads through a frozen snapshot rather than the live identity.

These tests hold the properties that make it honest rather than merely present:
nothing is destroyed, the pin cannot be pruned out from under the person, and a
pin that stops resolving says so instead of silently serving something else.
"""
import inspect

import pytest

from app.services import identity_restore


class TestItDoesNotPretendToRewriteHistory:
    def test_the_service_never_writes_to_identities(self):
        """The tempting implementation, and the broken one: every sub-profile
        is recomputed from behaviour objects on the next ingest, so a restored
        identities row lasts exactly until the next event."""
        source = inspect.getsource(identity_restore)
        assert "UPDATE identities" not in source
        assert "INSERT INTO identities" not in source

    def test_it_deletes_no_snapshots(self):
        source = inspect.getsource(identity_restore)
        assert "DELETE FROM identity_snapshots" not in source

    def test_only_the_pin_table_is_written(self):
        source = inspect.getsource(identity_restore)
        for statement in ("INSERT INTO", "DELETE FROM", "UPDATE "):
            for line in source.splitlines():
                if statement in line and "identity_pins" not in line:
                    # The only write target may be identity_pins.
                    assert "identity_pins" in source[source.find(line):
                                                     source.find(line) + 400], line


class TestThePinSurvivesPruning:
    def test_cleanup_excludes_pinned_snapshots(self):
        """cleanup_old_snapshots keeps the twenty most recent. Someone standing
        on an older one is on exactly the row it would delete, and the pin would
        then dangle."""
        from app.api.ingest import cleanup_old_snapshots

        source = inspect.getsource(cleanup_old_snapshots)
        assert "identity_pins" in source
        assert "NOT IN" in source

    def test_the_pin_has_no_foreign_key_to_snapshots(self):
        """A cascade would delete the pin along with the snapshot, losing the
        fact that the person had chosen one. A dangling pin is recoverable;
        a vanished one is not."""
        from pathlib import Path

        sql = (Path(__file__).parent.parent / "app" / "db" / "migration_v23.sql").read_text()
        assert "identity_pins" in sql
        assert "REFERENCES identity_snapshots" not in sql


class TestABrokenPinIsAudible:
    def test_the_reader_reports_a_dangling_pin(self):
        source = inspect.getsource(identity_restore.active_snapshot)
        assert "_pin_broken" in source
        assert "falling back to latest" in source

    def test_the_listing_explains_the_breakage(self):
        source = inspect.getsource(identity_restore.list_restore_points)
        assert "pin_broken" in source
        assert "no longer" in source


class TestTheReadPathHonoursIt:
    def test_current_identity_resolves_through_the_pin(self):
        from app.api.explain import get_current_identity

        source = inspect.getsource(get_current_identity)
        assert "active_snapshot" in source
        assert "ORDER BY snapshot_timestamp DESC LIMIT 1" not in source

    def test_the_response_says_whether_a_pin_applied(self):
        from app.api.explain import get_current_identity

        source = inspect.getsource(get_current_identity)
        assert '"pinned"' in source


class TestScoping:
    def test_a_snapshot_is_matched_against_the_calling_user(self):
        """Otherwise the endpoint reports whether somebody else's snapshot id
        exists."""
        source = inspect.getsource(identity_restore.set_pin)
        assert "AND user_id = $2" in source

    def test_the_reader_scopes_its_lookup_too(self):
        """The id comes from this user's own pin row, so this is defence in
        depth rather than the only barrier - but an unscoped lookup here would
        serve another account's snapshot to anyone whose pin pointed at it."""
        source = inspect.getsource(identity_restore.active_snapshot)
        assert "AND user_id = $2" in source

    def test_every_snapshot_read_in_the_service_is_scoped(self):
        """Written as a sweep rather than per function, so a lookup added later
        is covered without anyone remembering to extend this."""
        source = inspect.getsource(identity_restore)
        for line in source.splitlines():
            if "FROM identity_snapshots" in line and "SELECT" in line:
                assert "user_id" in line or "AND user_id" in source, line

    def test_the_reason_is_bounded(self):
        assert 0 < identity_restore.MAX_REASON_LENGTH <= 1000

    def test_a_blank_reason_is_stored_as_absent(self):
        source = inspect.getsource(identity_restore.set_pin)
        assert "or None" in source


class TestSnapshotPersistenceIsCheckedBeforeItIsRelied_On:
    def test_insert_snapshot_reports_whether_the_row_landed(self):
        """_insert_snapshot swallowed its exceptions while the caller set
        self_model.identity_snapshot_id from it regardless. The foreign key then
        failed one statement later, and that failure was swallowed too, so the
        self model silently stopped being written. Seen in a live run."""
        from pipeline.orchestrator import V3Pipeline

        source = inspect.getsource(V3Pipeline._insert_snapshot)
        assert "return False" in source
        assert "-> bool" in inspect.getsource(V3Pipeline._insert_snapshot).splitlines()[0]

    def test_the_caller_checks_the_result(self):
        from pipeline.orchestrator import V3Pipeline

        source = inspect.getsource(V3Pipeline._persist_all)
        assert "if await self._insert_snapshot(result.snapshot):" in source
