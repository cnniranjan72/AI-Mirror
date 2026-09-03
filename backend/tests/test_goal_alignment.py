"""Goal alignment read a lifecycle column that only updates on ingest.

Half of an alignment score is the balance of growing against declining matches.
That balance was taken from behavior_objects.lifecycle_state, which the ingest
sweep writes - so it is only as fresh as the last time the account sent
anything. On the deployed instance every one of the 226 behaviour objects
disagreed with a fresh evaluation: the column still said "growing" for 217 of
them while the behaviours had gone dormant or been abandoned outright. Goals
were scored against an account frozen at its last ingest.

Fixing that surfaced a second defect underneath. `stable` belongs to neither
GROWING_STATES nor DECLINING_STATES, which is right - a steady interest is not
moving either way - but the ratio was `growing / max(1, growing + declining)`,
so a wholly stable match scored 0: identical to one that is entirely declining.
A steady habit read as a collapsing one, and a "decrease" goal was credited for
a topic that had not budged. It could not surface before, because every
behaviour was labelled growing and the denominator was never zero.
"""
import inspect

import pytest

from app.api.goals import (
    DECLINING_STATES,
    GROWING_STATES,
    _compute_alignment,
)


def match(state, importance=0.8, topic="cooking"):
    return {"topic": topic, "lifecycle_state": state, "importance_score": importance}


class TestTheStateIsEvaluatedNotRead:
    def test_scoring_does_not_trust_the_stored_column(self):
        from app.api.goals import _score_goal

        source = inspect.getsource(_score_goal)
        assert "_current_lifecycle" in source

    def test_the_statistics_needed_to_evaluate_are_selected(self):
        """Re-evaluating needs the JSONB the evaluator reads; selecting only
        lifecycle_state would leave nothing to evaluate from."""
        from app.api.goals import _score_goal

        source = inspect.getsource(_score_goal)
        assert "temporal_statistics" in source
        assert "trend_information" in source

    def test_a_broken_evaluation_falls_back_rather_than_failing(self):
        from app.api.goals import _current_lifecycle

        assert _current_lifecycle({"lifecycle_state": "growing"}) in (
            "growing", "emerging", "stable", "declining", "dormant", "archived")


class TestStableIsNotDecline:
    def test_a_wholly_stable_match_is_not_scored_as_declining(self):
        steady = _compute_alignment("increase", [match("stable"), match("stable")])[0]
        falling = _compute_alignment(
            "increase", [match("declining"), match("dormant")])[0]
        assert steady > falling, (steady, falling)

    def test_decrease_is_not_credited_for_a_habit_that_has_not_moved(self):
        """The user-visible consequence: "spend less time on gaming" scored the
        same for an untouched habit as for one genuinely abandoned."""
        steady = _compute_alignment("decrease", [match("stable")])[0]
        abandoned = _compute_alignment("decrease", [match("dormant")])[0]
        assert abandoned > steady, (abandoned, steady)

    def test_the_explanation_does_not_claim_a_direction_it_lacks(self):
        _score, _supporting, note = _compute_alignment("increase", [match("stable")])
        assert "holding steady" in note
        assert "not yet trending up" not in note

    def test_growing_still_reads_as_growing(self):
        _s, _sup, note = _compute_alignment("increase", [match("growing")])
        assert "growing" in note

    def test_declining_still_reads_as_declining(self):
        _s, _sup, note = _compute_alignment("decrease", [match("declining")])
        assert "declining" in note


class TestTheStateSetsCoverTheLifecycle:
    def test_every_state_is_either_moving_or_deliberately_neutral(self):
        """A state in neither set is treated as neutral, so a new one added to
        the lifecycle without a decision here silently becomes neutral. Listed
        explicitly so that is a choice rather than an oversight."""
        from reasoning.lifecycle import STATES

        neutral = set(STATES) - set(GROWING_STATES) - set(DECLINING_STATES)
        assert neutral == {"stable"}, neutral

    def test_the_sets_do_not_overlap(self):
        assert not (set(GROWING_STATES) & set(DECLINING_STATES))


class TestNoMatchesIsStillReportedHonestly:
    def test_an_unmatched_goal_scores_zero_and_says_why(self):
        score, supporting, note = _compute_alignment("increase", [])
        assert score == 0.0
        assert supporting == []
        assert "No behavior yet matches" in note
