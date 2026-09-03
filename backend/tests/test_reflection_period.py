"""A reflection has to cover a period.

The architecture says the Reflection Engine "synthesises daily, weekly and
monthly journals for longitudinal analysis". On the deployed instance all 29
stored reflections were of one type, "periodic", and every one had
period_start == period_end: a window of zero seconds.

Both defaults were `now` and no caller passed either, so the row recorded the
moment it was written rather than the stretch of behaviour it described. The
diary endpoint already documents the consequence in its own docstring - it
aggregates from events directly because using this table "would silently
mislabel per-batch snapshots as 'this week'".

The span was always in hand: the earliest and latest the summarised behaviours
were seen. Labelling by measured length rather than by an assumed schedule also
means the type cannot claim a cadence the writes do not have.
"""
from datetime import datetime, timedelta, timezone

import pytest

from reasoning.reflection_engine import (
    ReflectionEngine,
    _as_aware,
    _observed_span,
    _period_label,
)

NOW = datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc)


class Stats:
    def __init__(self, first, last, count=5):
        self.first_seen = first
        self.last_seen = last
        self.occurrence_count = count


class Behaviour:
    def __init__(self, topic, first, last, stability=0.6):
        self.topic = topic
        self.creators = []
        self.stability_score = stability
        self.unique_id = "bo_" + topic
        self.temporal_statistics = Stats(first, last)


def ago(days):
    return NOW - timedelta(days=days)


class TestTheSpanIsMeasured:
    def test_it_runs_from_earliest_to_latest_observed(self):
        span = _observed_span([
            Behaviour("a", ago(10), ago(8)),
            Behaviour("b", ago(30), ago(1)),
        ])
        assert span == (ago(30), ago(1))

    def test_no_timestamps_yields_no_span(self):
        assert _observed_span([]) is None
        assert _observed_span([Behaviour("a", None, None)]) is None

    def test_naive_and_aware_timestamps_mix_without_raising(self):
        """This codebase carries both, and comparing them raises."""
        naive = datetime(2026, 8, 1, 9, 0, 0)
        span = _observed_span([
            Behaviour("a", naive, naive + timedelta(days=2)),
            Behaviour("b", ago(5), ago(1)),
        ])
        assert span is not None
        assert span[0] < span[1]

    def test_a_reversed_pair_is_ordered(self):
        span = _observed_span([Behaviour("a", ago(1), ago(9))])
        assert span[0] <= span[1]


class TestTheLabelDescribesTheWindow:
    def test_an_afternoon_is_daily(self):
        assert _period_label(NOW - timedelta(hours=5), NOW) == "daily"

    def test_a_few_days_is_weekly(self):
        assert _period_label(ago(4), NOW) == "weekly"

    def test_six_weeks_is_monthly(self):
        assert _period_label(ago(42), NOW) == "monthly"

    def test_the_boundaries_are_where_they_claim(self):
        assert _period_label(ago(1), NOW) == "daily"
        assert _period_label(ago(7), NOW) == "weekly"
        assert _period_label(ago(8), NOW) == "monthly"

    def test_missing_bounds_do_not_raise(self):
        assert _period_label(None, NOW) == "daily"
        assert _period_label(NOW, None) == "daily"

    def test_all_three_labels_are_reachable(self):
        """Only one of them ever occurred before, and it was not one of these."""
        produced = {
            _period_label(NOW - timedelta(hours=2), NOW),
            _period_label(ago(3), NOW),
            _period_label(ago(60), NOW),
        }
        assert produced == {"daily", "weekly", "monthly"}


class TestTheEngineUsesThem:
    def _reflection(self, behaviours):
        return ReflectionEngine().generate_reflection(
            user_id="u", behavior_objects=behaviours,
            evidence_list=[], inferences=[],
        )

    def test_a_reflection_covers_a_real_window(self):
        ref = self._reflection([
            Behaviour("cooking", ago(9), ago(2)),
            Behaviour("travel", ago(6), ago(1)),
        ])
        assert ref is not None
        start = _as_aware(ref.period_start)
        end = _as_aware(ref.period_end)
        assert end > start, "period_start == period_end was the whole defect"
        assert (end - start).days >= 7

    def test_the_type_matches_the_window(self):
        weekly = self._reflection([Behaviour("a", ago(5), ago(1))])
        monthly = self._reflection([Behaviour("a", ago(60), ago(1))])
        assert weekly.reflection_type == "weekly"
        assert monthly.reflection_type == "monthly"

    def test_periodic_is_no_longer_written(self):
        import inspect
        from reasoning import reflection_engine

        source = inspect.getsource(reflection_engine)
        assert 'reflection_type="periodic"' not in source

    def test_behaviours_without_timestamps_still_produce_a_reflection(self):
        """Falling back to `now` for both is what produced the zero-length
        window, but it must remain a fallback rather than an exception."""
        ref = self._reflection([Behaviour("a", None, None)])
        assert ref is not None
        assert ref.reflection_type in ("daily", "weekly", "monthly")


class TestTheVectorTermIsCosine:
    def test_hybrid_search_uses_the_cosine_operator(self):
        """<-> is L2, <=> is cosine. Both rank identically for the unit-length
        vectors all-MiniLM-L6-v2 produces - measured, no reordering on the
        deployed corpus - but 1 - L2 reaches zero at cosine 0.5 and goes
        negative below it, so the vector term is on a different scale from the
        fixed-scale keyword term it is blended with."""
        import inspect
        from app.services import vector_store

        source = inspect.getsource(vector_store.hybrid_search)
        assert "embedding <=> $2::vector" in source
        assert "1 - (embedding <-> $2::vector)" not in source

    def test_the_weights_are_still_the_documented_ones(self):
        import inspect
        from app.services import vector_store

        sig = inspect.signature(vector_store.hybrid_search)
        assert sig.parameters["vector_weight"].default == 0.7
        assert sig.parameters["keyword_weight"].default == 0.3
