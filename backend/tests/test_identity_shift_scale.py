"""Eq. 2 has to measure identity, not seconds.

The identity vector holds seventeen dimensions. Sixteen are scores declared
ge=0.0/le=1.0. The seventeenth, avg_attention_span, is a raw count of seconds
with no bounds, and it entered the L2 norm unscaled.

So the norm was dominated by one term ranging over hundreds while the sixteen
scores could contribute at most 1.0 each. It did not measure identity shift; it
measured a change in watch seconds. A drift experiment through the real
pipeline - deep technical viewing at 120-240s replaced by shallow
entertainment at 3-12s - recorded a shift of 118.2. Against a 0.30 threshold a
snapshot was warranted whenever average attention moved by a third of a second,
which is how one account accumulated fifteen consecutive snapshots with
identical contents.

A min(1.0, ...) clamp sat on the result, which hid the magnitude and left the
cause in place: with everything above 1.0 flattened, a moderate shift and a
total inversion were indistinguishable.
"""
import math

import pytest

from backend.identity.identity_evolution import IdentityEvolutionEngine


class _Profile:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def _identity(confidence=0.5, attention_seconds=60.0, dependence=0.4):
    """Only the dimensions these tests vary need real values."""
    return _Profile(
        overall_confidence=confidence,
        identity_completeness=0.6,
        behavior_profile=_Profile(avg_engagement_rate=0.5, behavior_diversity=0.5,
                                  behavior_stability=0.5),
        interest_graph=_Profile(diversity_score=0.5),
        creator_graph=_Profile(creator_diversity_score=0.5, dependence_score=dependence),
        learning_style=_Profile(confidence=0.5),
        attention_profile=_Profile(avg_attention_span=attention_seconds),
        exploration_profile=_Profile(novelty_seeking_score=0.5, exploration_rate=0.5),
        consistency_profile=_Profile(overall_consistency=0.5),
        habit_profile=_Profile(routine_strength=0.5),
        motivation_signals=_Profile(learning_motivation=0.5, entertainment_seeking=0.5,
                                    skill_building_intent=0.5),
    )


def test_the_fixture_covers_every_dimension():
    """_compute_identity_shift swallows exceptions and returns 0.0, so an
    incomplete fixture makes the distance tests pass for the wrong reason.
    This asserts the fixture is actually complete."""
    engine = IdentityEvolutionEngine()
    vector = engine._identity_vector(_identity())
    assert len(vector) == 17
    assert all(isinstance(v, float) for v in vector)


@pytest.fixture
def engine():
    return IdentityEvolutionEngine()


class TestEveryDimensionIsCommensurable:
    def test_the_vector_is_bounded(self, engine):
        """Any dimension outside [0,1] silently outweighs all the others."""
        extreme = _identity(confidence=1.0, attention_seconds=100000.0, dependence=1.0)
        vector = engine._identity_vector(extreme)
        assert len(vector) == 17
        for i, value in enumerate(vector):
            assert 0.0 <= value <= 1.0, f"dimension {i} is {value}, outside [0,1]"

    def test_attention_span_is_scaled_not_raw_seconds(self, engine):
        """The bug: seconds entered the norm directly."""
        span = 150.0
        vector = engine._identity_vector(_identity(attention_seconds=span))
        assert span not in vector, "raw seconds are still in the vector"
        assert pytest.approx(span / engine.ATTENTION_SPAN_CAP_SECONDS, abs=1e-9) in vector

    def test_an_absurd_span_saturates_rather_than_dominating(self, engine):
        vector = engine._identity_vector(_identity(attention_seconds=99999.0))
        assert max(vector) <= 1.0


class TestTheShiftIsInterpretable:
    def test_a_total_change_stays_within_the_geometric_bound(self, engine):
        """With every dimension in [0,1], the largest possible L2 over 17 of
        them is sqrt(17). A value above that means something is unscaled."""
        low = _identity(confidence=0.0, attention_seconds=0.0, dependence=0.0)
        high = _identity(confidence=1.0, attention_seconds=100000.0, dependence=1.0)
        shift = engine._compute_identity_shift(low, high)
        assert shift <= math.sqrt(17) + 1e-9, f"shift {shift} exceeds the bound"

    def test_the_recorded_shift_of_118_can_no_longer_occur(self, engine):
        """The measured value from the drift experiment, before the fix."""
        before = _identity(attention_seconds=180.0)
        after = _identity(attention_seconds=7.0)
        assert engine._compute_identity_shift(before, after) < 1.0

    def test_a_sub_second_wobble_no_longer_warrants_a_snapshot(self, engine):
        """This is what produced fifteen identical snapshots."""
        threshold = engine.config.get("snapshot_threshold", 0.30)
        before = _identity(attention_seconds=60.0)
        after = _identity(attention_seconds=60.4)
        assert engine._compute_identity_shift(before, after) < threshold

    def test_a_real_change_in_attention_still_registers(self, engine):
        """Two minutes of viewing collapsing to five seconds is a genuine
        change and must still cross."""
        threshold = engine.config.get("snapshot_threshold", 0.30)
        before = _identity(attention_seconds=180.0)
        after = _identity(attention_seconds=5.0)
        assert engine._compute_identity_shift(before, after) > threshold

    def test_one_sub_profile_moving_a_lot_still_counts(self, engine):
        """RMS normalisation was the other candidate fix and would divide this
        by sqrt(17), averaging away a real change in one trait."""
        threshold = engine.config.get("snapshot_threshold", 0.30)
        before = _identity(dependence=0.30)
        after = _identity(dependence=0.95)
        assert engine._compute_identity_shift(before, after) > threshold

    def test_the_result_is_not_clamped_to_one(self, engine):
        """Clamping made a moderate shift and a total inversion identical, and
        left the recorded value useless for showing how far someone moved."""
        low = _identity(confidence=0.0, attention_seconds=0.0, dependence=0.0)
        high = _identity(confidence=1.0, attention_seconds=100000.0, dependence=1.0)
        assert engine._compute_identity_shift(low, high) > 1.0


class TestTheThresholdMeansSomething:
    def test_identical_identities_do_not_move(self, engine):
        assert engine._compute_identity_shift(_identity(), _identity()) == pytest.approx(0.0)

    def test_the_default_threshold_matches_the_documented_design(self, engine):
        """The code defaulted to 0.15 while the specification said 0.30."""
        assert engine.config.get("snapshot_threshold", 0.30) == 0.30
