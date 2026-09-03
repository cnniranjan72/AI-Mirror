"""The recall index, and the identity write that was silently failing beside it.

The `memories` table has existed since the original schema with five indexes on
it, including one on importance and one on (user_id, memory_type). It held zero
rows and had no writer anywhere in the system - a fact two other modules had
already discovered and worked around in comments of their own:
cognitive_pipeline/pipeline.py populates the character's memory references from
identities.source_behavior_objects instead, and app/api/timeline.py queries the
table on every request and has always received nothing.

The `memory/` package declares five memory types across six modules. Each
stores to `self._memory_store: Dict[str, MemoryRecord]` under the comment
"In-memory storage (in production, use database)", and none of the five classes
is referenced outside its own singleton getter. The paper says "AIMirror uses
five memory types and, unlike these systems, selects among them with a planner
that never calls a language model"; the planner half is true.

It mattered on the live answer path: for the memory_question intent the
retrieval planner requests RetrievalTarget.MEMORY at priority 0.8 with
required=True, the highest-priority mandatory source for that intent, and it
resolved to an empty table.

Two defects surfaced while testing the writer, both in the identity persistence
beside it, and both of the same shape as the swallowed snapshot insert fixed
earlier.
"""
import inspect

import pytest

from app.services import memory_store


class TestWhatItStores:
    def test_unimportant_material_is_not_kept(self):
        """A recall index that stores everything is the table it is built
        from."""
        assert memory_store.MIN_IMPORTANCE > 0

    def test_the_write_is_bounded_per_type(self):
        assert 0 < memory_store.MAX_PER_TYPE <= 100

    def test_the_five_types_are_the_declared_ones(self):
        from shared.contracts import MemoryType

        assert set(memory_store.VALID_TYPES) == {t.value for t in MemoryType}

    def test_each_type_is_drawn_from_different_material(self):
        """Writing the same row five times under five labels would satisfy
        "five memory types" while saying nothing."""
        source = inspect.getsource(memory_store.write_from_pipeline)
        assert '"semantic"' in source and "behavior_objects" in source
        assert '"behavioral"' in source and "inferences" in source
        assert '"reflection"' in source and "reflection" in source


class TestIdempotence:
    def test_the_id_is_derived_from_the_subject(self):
        """Keyed on what the memory is about, not when it was written: the same
        conclusion drawn twice is one memory reinforced, not two memories. The
        reflections table came to hold 29 unusable rows the other way."""
        a = memory_store.memory_id("u", "semantic", "cooking")
        b = memory_store.memory_id("u", "semantic", "cooking")
        assert a == b

    def test_different_subjects_differ(self):
        a = memory_store.memory_id("u", "semantic", "cooking")
        b = memory_store.memory_id("u", "semantic", "travel")
        assert a != b

    def test_different_users_do_not_collide(self):
        a = memory_store.memory_id("alice", "semantic", "cooking")
        b = memory_store.memory_id("bob", "semantic", "cooking")
        assert a != b

    def test_different_types_do_not_collide(self):
        a = memory_store.memory_id("u", "semantic", "x")
        b = memory_store.memory_id("u", "episodic", "x")
        assert a != b

    def test_the_write_upserts_rather_than_appends(self):
        source = inspect.getsource(memory_store.remember)
        assert "ON CONFLICT (memory_id) DO UPDATE" in source


class TestRecallRecordsItself:
    def test_reading_increments_the_access_count(self):
        """access_count and last_accessed were in the schema and never
        written, so nothing could tell a memory consulted daily from one never
        looked at."""
        source = inspect.getsource(memory_store.recall)
        assert "access_count = access_count + 1" in source
        assert "last_accessed = NOW()" in source

    def test_a_failed_write_does_not_fail_the_read(self):
        source = inspect.getsource(memory_store.recall)
        assert "Could not record memory access" in source

    def test_recall_is_ordered_by_importance(self):
        source = inspect.getsource(memory_store.recall)
        assert "ORDER BY importance_score DESC" in source

    def test_type_filtering_is_restricted_to_known_types(self):
        """The filter reaches SQL, so an unknown value must not."""
        source = inspect.getsource(memory_store.recall)
        assert "if t in VALID_TYPES" in source


class TestIdentityIsKeyedOnTheRightColumn:
    def test_the_upsert_matches_on_user_id(self):
        """identities is unique on identity_id AND user_id - one row per
        person. The lookup used identity_id, and the pipeline mints a fresh one
        whenever it could not load the existing identity, so the lookup missed,
        the INSERT violated identities_user_id_key, and the error was
        swallowed. The identity then sat frozen at its previous contents while
        every later snapshot failed its foreign key. Seen on a live second
        ingest."""
        from pipeline.orchestrator import V3Pipeline

        source = inspect.getsource(V3Pipeline._upsert_identity)
        assert "FROM identities WHERE user_id = $1" in source
        assert "WHERE identity_id = $1" not in source

    def test_the_stored_id_wins_over_a_freshly_minted_one(self):
        """Snapshots and traces already reference the stored id; overwriting it
        would strand them."""
        from pipeline.orchestrator import V3Pipeline

        source = inspect.getsource(V3Pipeline._upsert_identity)
        assert 'identity.identity_id = existing["identity_id"]' in source


class TestTheSnapshotFollowsTheReconciledIdentity:
    def test_the_id_is_passed_not_assigned(self):
        """IdentitySnapshot is frozen, which is the point of a snapshot.
        Assigning to it raises, and the raise aborted the whole persistence
        step - no snapshot and no self model for that ingest."""
        from pipeline.orchestrator import V3Pipeline

        source = inspect.getsource(V3Pipeline._persist_all)
        assert "result.snapshot.identity_id = " not in source
        assert "identity_id=persisted_identity_id" in source

    def test_the_insert_accepts_an_override(self):
        from pipeline.orchestrator import V3Pipeline

        sig = inspect.signature(V3Pipeline._insert_snapshot)
        assert "identity_id" in sig.parameters
        assert sig.parameters["identity_id"].default is None

    def test_the_snapshot_model_is_still_frozen(self):
        """If this stops being true the bug above stops being prevented by the
        type system, and the assignment becomes tempting again."""
        from identity.identity_snapshot import IdentitySnapshot

        config = getattr(IdentitySnapshot, "model_config", None) or {}
        frozen = config.get("frozen") if isinstance(config, dict) else None
        if frozen is None:
            inner = getattr(IdentitySnapshot, "Config", None)
            frozen = getattr(inner, "frozen", None) or getattr(inner, "allow_mutation", True) is False
        assert frozen, "IdentitySnapshot is expected to be immutable"
