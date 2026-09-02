"""A behaviour has to be able to end.

Six lifecycle states are declared, named in the paper, and stored in a column.
Measured against the deployed instance, 226 of 226 behaviour objects were in
one of two: 217 growing, 9 emerging. Stable, declining, dormant and archived
had never occurred in the product's history.

Two structural causes.

State was written only when a topic appeared in an ingest batch. A topic
someone has abandoned never appears in a batch again, so the single code path
that could retire it was unreachable for exactly the behaviours needing it.
Ninety-six objects unseen for over thirty days were still labelled growing; the
oldest had last been seen 600 days earlier.

And the quantity it thresholded, `growth_rate`, is `occurrence_count` divided
by days elapsed - occurrences per day, necessarily positive, averaging 3.08 and
reaching 60 on real data. So `> 0.5` caught almost everything, and DECLINING,
defined as `growth_rate < 0`, could not fire at all.

These tests hold the two properties that fix implies: that silence eventually
retires a behaviour, and that every declared state is reachable.
"""
from datetime import datetime, timedelta, timezone

import pytest

from reasoning.lifecycle import (
    ARCHIVED_AFTER_DAYS,
    DORMANCY_RATIO,
    DORMANT_AFTER_DAYS,
    STATES,
    evaluate_lifecycle,
    recent_share,
)

NOW = datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc)


def temporal(last_seen_days_ago, first_seen_days_ago=None, occurrences=20,
             per_day=1.0, consistency=0.6):
    first = first_seen_days_ago
    if first is None:
        first = last_seen_days_ago + 30
    return {
        "last_seen": (NOW - timedelta(days=last_seen_days_ago)).isoformat(),
        "first_seen": (NOW - timedelta(days=first)).isoformat(),
        "occurrence_count": occurrences,
        "daily_frequency": per_day,
        "consistency_score": consistency,
        "days_active": max(1, int(first - last_seen_days_ago)),
    }


class TestSilenceRetiresABehaviour:
    def test_a_long_abandoned_behaviour_is_archived(self):
        """The case that motivated all of this: last seen 600 days ago and
        still, officially, growing."""
        state, why = evaluate_lifecycle(temporal(600), {}, NOW)
        assert state == "archived"
        assert "600" in why["basis"]

    def test_a_recently_abandoned_behaviour_is_dormant(self):
        state, _ = evaluate_lifecycle(temporal(40, per_day=3.0), {}, NOW)
        assert state == "dormant"

    def test_a_current_behaviour_is_not_retired(self):
        state, _ = evaluate_lifecycle(temporal(1, first_seen_days_ago=90), {}, NOW)
        assert state not in ("dormant", "archived")


class TestSilenceIsJudgedAgainstItsOwnRhythm:
    def test_a_daily_habit_gone_a_month_is_dormant(self):
        state, _ = evaluate_lifecycle(temporal(30, per_day=2.0), {}, NOW)
        assert state == "dormant"

    def test_an_occasional_interest_is_not_dormant_at_the_same_gap(self):
        """A topic that surfaces every six weeks has not gone anywhere after
        thirty days. An absolute threshold would retire both alike."""
        state, _ = evaluate_lifecycle(
            temporal(30, first_seen_days_ago=400, per_day=1.0 / 42.0), {}, NOW)
        assert state != "dormant"

    def test_a_burst_yesterday_is_not_abandoned_today(self):
        """Ten views yesterday gives a typical gap measured in hours, so
        without an absolute floor any ordinary pause trips the ratio."""
        state, _ = evaluate_lifecycle(
            temporal(2, first_seen_days_ago=3, occurrences=10, per_day=10.0), {}, NOW)
        assert state != "dormant"

    def test_the_floor_is_what_stops_it(self):
        assert DORMANT_AFTER_DAYS >= 7
        assert DORMANCY_RATIO > 1.0

    def test_too_few_occurrences_falls_back_to_the_plain_gap(self):
        """With one or two sightings there is no rhythm to be absent from, so
        the absolute line is used rather than a ratio built on nothing."""
        state, why = evaluate_lifecycle(
            temporal(40, occurrences=2, per_day=0.0), {}, NOW)
        assert state == "dormant"
        assert "rhythm" in why["basis"]


class TestEveryDeclaredStateIsReachable:
    """The original scheme could produce two of six. A state that cannot occur
    is not a state, and four of these were being claimed in the paper."""

    def _states_produced(self):
        cases = [
            (temporal(1, first_seen_days_ago=5, occurrences=6), {}),
            (temporal(1, first_seen_days_ago=200), {"recent_share": 0.8}),
            (temporal(1, first_seen_days_ago=200), {"recent_share": 0.5}),
            (temporal(1, first_seen_days_ago=200), {"recent_share": 0.2}),
            (temporal(40, per_day=3.0), {}),
            (temporal(400), {}),
        ]
        return {evaluate_lifecycle(t, tr, NOW)[0] for t, tr in cases}

    def test_all_six_states_occur(self):
        produced = self._states_produced()
        missing = sorted(set(STATES) - produced)
        assert not missing, f"unreachable states: {missing}"

    def test_declining_is_reachable(self):
        """It was defined as growth_rate < 0, and growth_rate is a count over
        days: never negative, so the state could not exist."""
        state, why = evaluate_lifecycle(
            temporal(1, first_seen_days_ago=200), {"recent_share": 0.2}, NOW)
        assert state == "declining"
        assert "tailing off" in why["basis"]

    def test_growing_needs_activity_concentrated_recently(self):
        state, _ = evaluate_lifecycle(
            temporal(1, first_seen_days_ago=200), {"recent_share": 0.9}, NOW)
        assert state == "growing"


class TestTheTrajectory:
    def _times(self, offsets):
        return [(NOW - timedelta(days=d)).isoformat() for d in offsets]

    def test_front_loaded_activity_scores_low(self):
        # Five sightings early, one much later: the midpoint of the span
        # falls after the cluster, so the recent half holds almost nothing.
        share = recent_share(self._times([100, 99, 98, 97, 96, 50]))
        assert share is not None and share < 0.5

    def test_back_loaded_activity_scores_high(self):
        share = recent_share(self._times([100, 5, 4, 3, 2, 1]))
        assert share is not None and share > 0.5

    def test_even_activity_scores_near_half(self):
        share = recent_share(self._times([100, 80, 60, 40, 20, 1]))
        assert share == pytest.approx(0.5, abs=0.2)

    def test_too_few_points_is_declined(self):
        assert recent_share(self._times([10, 5])) is None
        assert recent_share([]) is None

    def test_a_single_instant_has_no_trajectory(self):
        """Everything at one timestamp gives a zero-length span, which must not
        divide by zero or report a direction."""
        same = [NOW.isoformat()] * 8
        assert recent_share(same) is None


class TestEveryLabelExplainsItself:
    def test_a_reason_accompanies_every_state(self):
        for days in (1, 20, 40, 400):
            _state, why = evaluate_lifecycle(temporal(days), {}, NOW)
            assert why.get("basis"), days
            assert why["days_since_last_seen"] is not None

    def test_missing_timestamps_do_not_produce_a_confident_label(self):
        state, why = evaluate_lifecycle({}, {}, NOW)
        assert state == "emerging"
        assert "no judgement" in why["basis"]


class TestTheProducerNoLongerReadsTheBatch:
    def test_the_orchestrator_refreshes_every_behaviour(self):
        """The fix is the sweep, not the formula. Without it an abandoned topic
        is never re-examined, because it is never in a batch again."""
        import inspect
        from pipeline.orchestrator import V3Pipeline

        source = inspect.getsource(V3Pipeline.run)
        assert "_refresh_lifecycles" in source

        sweep = inspect.getsource(V3Pipeline._refresh_lifecycles)
        assert "WHERE user_id = $1" in sweep

    def test_the_old_growth_rate_threshold_is_gone(self):
        import inspect
        from pipeline import orchestrator

        source = inspect.getsource(orchestrator)
        assert "_lifecycle_from_cluster" not in source
        assert "cluster.growth_rate > 0.5" not in source
