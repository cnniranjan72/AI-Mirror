"""The drift view has to describe the same movement the system acts on.

The architecture stores versioned snapshots and measures the distance between
them to decide when a new one is warranted. That figure only ever appeared in a
log line, which is a strange omission for a product arguing that people should
see what is being built out of their behaviour.

The risk in showing it is a chart that disagrees with the system. So the vector
is read through IdentityEvolutionEngine._identity_vector rather than rebuilt
here, and these tests pin that: if the definition moves, the chart moves with
it, and the axis labels stay in step with the values they name.
"""
import pytest

from app.services import identity_drift
from backend.identity.identity_evolution import IdentityEvolutionEngine


class TestItUsesOneDefinitionOfTheVector:
    def test_label_count_matches_the_vector(self):
        """A mismatch silently mislabels every axis after the missing one."""
        sample = identity_drift._Shim({
            "overall_confidence": 0.5, "identity_completeness": 0.5,
            "behavior_profile": {"avg_engagement_rate": 0.5, "behavior_diversity": 0.5,
                                 "behavior_stability": 0.5},
            "interest_graph": {"diversity_score": 0.5},
            "creator_graph": {"creator_diversity_score": 0.5, "dependence_score": 0.5},
            "learning_style": {"confidence": 0.5},
            "attention_profile": {"avg_attention_span": 60.0},
            "exploration_profile": {"novelty_seeking_score": 0.5, "exploration_rate": 0.5},
            "consistency_profile": {"overall_consistency": 0.5},
            "habit_profile": {"routine_strength": 0.5},
            "motivation_signals": {"learning_motivation": 0.5, "entertainment_seeking": 0.5,
                                   "skill_building_intent": 0.5},
        })
        assert len(identity_drift._vector(sample)) == len(identity_drift.DIMENSIONS)

    def test_it_does_not_rebuild_the_vector_locally(self):
        """Two definitions would let the picture and the threshold disagree."""
        import inspect
        source = inspect.getsource(identity_drift._vector)
        assert "_identity_vector" in source

    def test_attention_is_the_scaled_dimension(self):
        """Raw seconds here would reproduce the bug the scaling fixed."""
        span = 150.0
        sample = identity_drift._Shim({"attention_profile": {"avg_attention_span": span}})
        vector = identity_drift._vector(sample)
        assert span not in vector
        assert pytest.approx(
            span / IdentityEvolutionEngine.ATTENTION_SPAN_CAP_SECONDS, abs=1e-9) in vector


class TestTheShim:
    def test_a_missing_dimension_reads_as_zero_rather_than_raising(self):
        """An older snapshot should still plot, with its gaps visible as zeroes
        instead of taking the whole view down."""
        vector = identity_drift._vector(identity_drift._Shim({"overall_confidence": 0.8}))
        assert len(vector) == len(identity_drift.DIMENSIONS)
        assert vector[0] == 0.8
        assert vector[1] == 0.0

    def test_nested_profiles_are_reachable(self):
        shim = identity_drift._Shim({"creator_graph": {"dependence_score": 0.42}})
        assert shim.creator_graph.dependence_score == 0.42


class TestDistance:
    def test_identical_points_are_zero_apart(self):
        assert identity_drift._distance([0.5] * 17, [0.5] * 17) == 0.0

    def test_it_matches_the_euclidean_norm(self):
        assert identity_drift._distance([0.0, 0.0], [3.0, 4.0]) == 5.0

    def test_mismatched_lengths_return_none_rather_than_a_wrong_number(self):
        assert identity_drift._distance([0.1, 0.2], [0.1]) is None
        assert identity_drift._distance([], []) is None


class TestWhatIsReported:
    def test_the_bound_is_stated_so_the_axis_can_be_sized_honestly(self):
        """Without it a client normalises against whatever it has seen, and a
        small movement fills the chart."""
        import math
        expected = round(math.sqrt(len(identity_drift.DIMENSIONS)), 4)
        assert expected == pytest.approx(4.1231, abs=1e-4)

    def test_every_dimension_carries_a_plain_language_meaning(self):
        for name, meaning in identity_drift.DIMENSIONS:
            assert name and meaning
            assert "_" not in name, f"{name} reads as a schema field, not a description"
