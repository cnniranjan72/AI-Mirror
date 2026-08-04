"""Pure unit tests for _compute_alignment — no DB needed."""
from app.api.goals import _compute_alignment


def _obj(importance, lifecycle, topic="test_topic"):
    return {"importance_score": importance, "lifecycle_state": lifecycle, "topic": topic}


def test_no_matching_behavior_returns_zero():
    score, supporting, explanation = _compute_alignment("increase", [])
    assert score == 0.0
    assert supporting == []
    assert "no behavior yet" in explanation.lower()


def test_increase_goal_rewards_growing_high_importance():
    matching = [_obj(0.8, "growing"), _obj(0.7, "emerging")]
    score, _, _ = _compute_alignment("increase", matching)
    assert score > 0.7


def test_increase_goal_penalizes_declining_low_importance():
    matching = [_obj(0.1, "declining"), _obj(0.05, "dormant")]
    score, _, _ = _compute_alignment("increase", matching)
    assert score < 0.2


def test_decrease_goal_rewards_declining_low_importance():
    matching = [_obj(0.1, "declining"), _obj(0.05, "archived")]
    score, _, _ = _compute_alignment("decrease", matching)
    assert score > 0.8


def test_decrease_goal_penalizes_growing_high_importance():
    matching = [_obj(0.9, "growing"), _obj(0.8, "emerging")]
    score, _, _ = _compute_alignment("decrease", matching)
    assert score < 0.2


def test_maintain_goal_tracks_raw_importance():
    matching = [_obj(0.6, "growing"), _obj(0.4, "declining")]
    score, _, _ = _compute_alignment("maintain", matching)
    assert score == 0.5


def test_score_always_bounded_0_to_1():
    matching = [_obj(1.5, "growing")]  # out-of-range input shouldn't blow the bound
    score, _, _ = _compute_alignment("increase", matching)
    assert 0.0 <= score <= 1.0
