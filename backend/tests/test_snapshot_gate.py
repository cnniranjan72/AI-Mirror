"""Identity snapshot gate — Eq.2 threshold behaviour.

Regression cover for a real production failure: `test_user_001` reached
identity v4 with confidence 0.48 while its only stored snapshot was v1 at
0.462, and no second snapshot was ever written.

The cause was the baseline, not the threshold. The gate diffed each identity
against its immediately preceding state, so it only ever asked "how much did
THIS ingest change things". An identity moving ~0.05 per ingest never trips a
0.15 threshold, so it can drift arbitrarily far while the stored history still
shows nothing but its first snapshot. Measuring against the last PERSISTED
snapshot makes that drift accumulate until it genuinely warrants a new row.

These tests run entirely in-process — no database, no network.
"""
from datetime import datetime

import pytest

from backend.identity.identity_engine import (
    Identity, BehaviorProfile, InterestGraph, CreatorGraph, LearningStyle,
    AttentionProfile, ExplorationProfile, ConsistencyProfile, HabitProfile,
    MotivationSignals,
)
from backend.identity.identity_evolution import IdentityEvolutionEngine
from backend.identity.identity_snapshot import IdentitySnapshot


def _zeroed(model_cls):
    """Instantiate a profile model with every required field at its zero value.

    Built by introspection rather than by listing fields: these nine profile
    models carry ~40 required numeric fields between them, and enumerating them
    here would make this file break every time an unrelated field is added.
    All that matters for these tests is that the profiles are *identical*
    across fixtures, so the only dimension that moves is the one set explicitly.
    """
    zeros = {"float": 0.0, "int": 0, "str": "", "bool": False, "list": [], "dict": {}}
    values = {}
    for name, field in model_cls.model_fields.items():
        if not field.is_required():
            continue
        annotation = getattr(field.annotation, "__name__", "float")
        values[name] = zeros.get(annotation, 0.0)
    return model_cls(**values)


def _identity(confidence: float, completeness: float = 0.6) -> Identity:
    """A minimal identity. Every sub-profile is zeroed identically, so
    `overall_confidence` is the only dimension that varies between fixtures —
    which keeps the expected L2 distances to arithmetic anyone can check by
    hand (a 0.02 confidence step is a 0.02 shift)."""
    return Identity(
        identity_id="identity_test",
        user_id="test_user",
        behavior_profile=_zeroed(BehaviorProfile),
        interest_graph=_zeroed(InterestGraph),
        creator_graph=_zeroed(CreatorGraph),
        learning_style=_zeroed(LearningStyle),
        attention_profile=_zeroed(AttentionProfile),
        exploration_profile=_zeroed(ExplorationProfile),
        consistency_profile=_zeroed(ConsistencyProfile),
        habit_profile=_zeroed(HabitProfile),
        motivation_signals=_zeroed(MotivationSignals),
        overall_confidence=confidence,
        identity_completeness=completeness,
        # Fixed rather than now(): from_identity serialises these into snapshot
        # metadata, and a moving clock would make otherwise-identical fixtures
        # differ.
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )


def _snapshot_of(identity: Identity) -> IdentitySnapshot:
    return IdentitySnapshot.from_identity(identity, validity_hours=24)


class TestIdentityVector:
    def test_vector_is_extractable_from_both_identity_and_snapshot(self):
        """The baseline may be a stored snapshot rather than a live identity,
        so the same 17 dimensions have to come off either type."""
        identity = _identity(0.5)
        snapshot = _snapshot_of(identity)

        v_identity = IdentityEvolutionEngine._identity_vector(identity)
        v_snapshot = IdentityEvolutionEngine._identity_vector(snapshot)

        assert len(v_identity) == 17
        assert v_identity == v_snapshot

    def test_shift_is_zero_between_identical_states(self):
        engine = IdentityEvolutionEngine()
        a, b = _identity(0.5), _identity(0.5)
        assert engine._compute_identity_shift(a, b) == pytest.approx(0.0)

    def test_shift_grows_with_distance(self):
        engine = IdentityEvolutionEngine()
        base = _identity(0.40)
        near = _identity(0.45)
        far = _identity(0.90)
        assert engine._compute_identity_shift(base, near) < engine._compute_identity_shift(base, far)

    def test_shift_measured_against_snapshot_matches_identity(self):
        """A snapshot baseline must produce the same number as the identity it
        was taken from — otherwise switching the baseline would silently
        re-scale the threshold."""
        engine = IdentityEvolutionEngine()
        old = _identity(0.40)
        new = _identity(0.60)
        assert engine._compute_identity_shift(_snapshot_of(old), new) == pytest.approx(
            engine._compute_identity_shift(old, new)
        )


class TestDriftAccumulation:
    """The actual bug: many small steps, each below threshold."""

    def test_stepwise_baseline_never_trips_threshold(self):
        """Documents the OLD behaviour and why it silently lost history: eight
        consecutive 0.02 steps move confidence 0.40 -> 0.56, and not one of
        them exceeds 0.15 when compared against the step before it."""
        engine = IdentityEvolutionEngine()
        threshold = engine.config.get("snapshot_threshold", 0.15)

        confidence = 0.40
        for _ in range(8):
            previous = _identity(confidence)
            confidence += 0.02
            current = _identity(confidence)
            assert engine._compute_identity_shift(previous, current) <= threshold

    def test_snapshot_baseline_eventually_trips_threshold(self):
        """Same drift, measured against a fixed snapshot baseline, accumulates
        and does cross the threshold — which is the fix."""
        engine = IdentityEvolutionEngine()
        threshold = engine.config.get("snapshot_threshold", 0.15)
        baseline = _snapshot_of(_identity(0.40))

        confidence = 0.40
        crossed_at = None
        for step in range(1, 9):
            confidence += 0.02
            if engine._compute_identity_shift(baseline, _identity(confidence)) > threshold:
                crossed_at = step
                break

        assert crossed_at is not None, "cumulative drift must eventually warrant a snapshot"
        # 0.02/step against a 0.15 threshold => the 8th step is the first to clear it.
        assert crossed_at == 8


class TestEvolveGate:
    """The flag `_persist_all` actually reads is on the SNAPSHOT's metadata."""

    def _evolve(self, engine, identity, **kwargs):
        return engine.evolve_identity(
            identity=identity, new_behaviors=[], new_inferences=[], new_evidence=[], **kwargs
        )

    def test_flag_reaches_snapshot_metadata(self):
        """from_identity copies identity.metadata onto the snapshot; the
        persistence layer reads it from there, so a break in that copy would
        silently make every snapshot persist (default True)."""
        engine = IdentityEvolutionEngine()
        _, snapshot, _ = self._evolve(engine, _identity(0.5))

        assert "snapshot_threshold_exceeded" in snapshot.metadata
        assert "identity_shift" in snapshot.metadata
        assert snapshot.metadata["shift_baseline"] in ("last_snapshot", "previous_identity")

    def test_baseline_is_reported_as_previous_identity_without_a_snapshot(self):
        engine = IdentityEvolutionEngine()
        _, snapshot, _ = self._evolve(engine, _identity(0.5))
        assert snapshot.metadata["shift_baseline"] == "previous_identity"

    def test_baseline_is_reported_as_last_snapshot_when_one_is_supplied(self):
        engine = IdentityEvolutionEngine()
        baseline = _snapshot_of(_identity(0.20))
        _, snapshot, _ = self._evolve(engine, _identity(0.5), baseline_snapshot=baseline)
        assert snapshot.metadata["shift_baseline"] == "last_snapshot"

    def test_force_snapshot_overrides_a_below_threshold_shift(self):
        """The time-based floor: a stable identity still gets periodic anchors,
        and the reason is recorded so a forced row is distinguishable from a
        genuine shift.

        The identity has to be evolved once first. `construct_identity`
        recomputes every field from the inputs, so an identity that has never
        been through it is not yet at a steady state — snapshotting it directly
        and then evolving would show a large shift caused purely by that
        recompute, not by any real drift.
        """
        engine = IdentityEvolutionEngine()

        settled, _, _ = self._evolve(engine, _identity(0.5))
        baseline = _snapshot_of(settled)

        # Second pass over the same empty inputs: genuinely no drift.
        _, snapshot, _ = self._evolve(
            engine, settled, baseline_snapshot=baseline, force_snapshot=True
        )

        assert snapshot.metadata["identity_shift"] == pytest.approx(0.0, abs=1e-6)
        assert snapshot.metadata["snapshot_threshold_exceeded"] is True
        assert snapshot.metadata["snapshot_forced_by_age"] is True

    def test_below_threshold_shift_is_not_persisted_without_a_force(self):
        """The complement of the test above — the gate must still suppress
        no-op snapshots, or the fix would just trade a missing history for a
        row per ingest."""
        engine = IdentityEvolutionEngine()

        settled, _, _ = self._evolve(engine, _identity(0.5))
        baseline = _snapshot_of(settled)

        _, snapshot, _ = self._evolve(engine, settled, baseline_snapshot=baseline)

        assert snapshot.metadata["snapshot_threshold_exceeded"] is False
        assert snapshot.metadata["snapshot_forced_by_age"] is False

    def test_forced_flag_is_false_when_the_shift_stands_on_its_own(self):
        engine = IdentityEvolutionEngine()
        baseline = _snapshot_of(_identity(0.10))
        _, snapshot, _ = self._evolve(
            engine, _identity(0.90), baseline_snapshot=baseline, force_snapshot=True
        )
        assert snapshot.metadata["snapshot_threshold_exceeded"] is True
        assert snapshot.metadata["snapshot_forced_by_age"] is False
