"""Every claim turns on a line. The user should be able to see where it is.

Each rule fires on a threshold over a measurable quantity, and nothing ever
told the user what that line was — a claim about them arrived as a verdict
with no visible basis, which is the complaint this product makes about
platforms.

Two kinds, kept apart on purpose. A share-based condition ("your top 3
creators are 62% of your watching; below 50% this stops") describes something
a person can recognise. A count-based one ("you have at least 2 recurring
topics") is not a lever: it is the amount of data the claim needs to exist,
and phrasing it as advice would be nonsense.

Not framed as instructions for changing a profile. The honest claim is
narrower: this is the whole of what was measured.
"""
import json

import pytest

from app.services import calibration as cal
from backend.reasoning.rules import RuleEngine


class _Stats:
    def __init__(self, count): self.occurrence_count = count


class _Watch:
    completion_rate = 0.7


class _Engagement:
    engagement_quality_score = 0.5
    overall_engagement_rate = 0.5
    total_interactions = 3


class FakeBehavior:
    def __init__(self, unique_id, topic, creators, occurrences):
        self.unique_id = unique_id
        self.topic = topic
        self.creators = creators
        self.subtopics = []
        self.keywords = []
        self.temporal_statistics = _Stats(occurrences)
        self.watch_statistics = _Watch()
        self.engagement_statistics = _Engagement()


def _concentrated():
    """Top 3 creators carry 90 of 120 occurrences (0.75), against a 0.50 line.

    The tail matters: with only three creators in the corpus "top 3" is
    everything and the share is trivially 1.0, which tests nothing.
    """
    return [
        FakeBehavior("bo_1", "space", ["natgeo"], 50),
        FakeBehavior("bo_2", "cooking", ["chefjohn"], 25),
        FakeBehavior("bo_3", "chess", ["gm_hikaru"], 15),
        FakeBehavior("bo_4", "music", ["someband"], 10),
        FakeBehavior("bo_5", "travel", ["wanderer"], 10),
        FakeBehavior("bo_6", "design", ["studio"], 10),
    ]


class TestEveryRuleCanStateItsLine:
    def test_no_rule_is_silent_about_its_threshold(self):
        """A rule that cannot say what it measures leaves the user with a bare
        assertion."""
        silent = [r.name for r in RuleEngine().rules
                  if "exit_condition" not in type(r).__dict__]
        assert not silent, f"rules with no exit condition: {silent}"

    @pytest.mark.parametrize("rule", RuleEngine().rules, ids=lambda r: r.name)
    def test_a_declared_condition_is_well_formed(self, rule):
        condition = rule.exit_condition(_concentrated(), [], [])
        if condition is None:
            return  # allowed: the rule cannot express it on this input
        assert set(condition) >= {"measure", "current", "threshold", "direction", "kind"}
        assert condition["kind"] in ("behavioural", "structural")
        assert condition["direction"] in ("below", "above")
        assert condition["measure"] and not condition["measure"].endswith(".")

    @pytest.mark.parametrize("rule", RuleEngine().rules, ids=lambda r: r.name)
    def test_no_behaviours_does_not_raise(self, rule):
        rule.exit_condition([], [], [])


class TestTheNumbersAreReal:
    def test_creator_dependence_reports_the_actual_share(self):
        """Top 3 carry 90 of 120 occurrences, so the share is 0.75 against a
        0.50 line."""
        condition = None
        for rule in RuleEngine().rules:
            if rule.name == "CreatorDependenceRule":
                condition = rule.exit_condition(_concentrated(), [], [])
        assert condition["current"] == pytest.approx(0.75, abs=0.01)
        assert condition["threshold"] == 0.5
        assert condition["direction"] == "below"
        assert condition["kind"] == "behavioural"

    def test_diversity_is_the_mirror_image_of_dependence(self):
        """Same measured quantity, opposite side of the same line."""
        by_name = {r.name: r for r in RuleEngine().rules}
        dep = by_name["CreatorDependenceRule"].exit_condition(_concentrated(), [], [])
        div = by_name["CreatorDiversityRule"].exit_condition(_concentrated(), [], [])
        assert dep["current"] == div["current"]
        assert dep["threshold"] == div["threshold"]
        assert dep["direction"] != div["direction"]

    def test_count_based_rules_are_marked_structural(self):
        """"Have fewer than two recurring topics" is not advice."""
        by_name = {r.name: r for r in RuleEngine().rules}
        for name in ("PrimaryInterestRule", "TemporalHabitRule", "EngagementDepthRule"):
            condition = by_name[name].exit_condition(_concentrated(), [], [])
            assert condition["kind"] == "structural", name
            assert condition["unit"] == "count", name


class TestThePhrasing:
    BEHAVIOURAL = {
        "measure": "share of your watching that comes from your top 3 creators",
        "current": 0.62, "threshold": 0.5,
        "direction": "below", "kind": "behavioural", "unit": "share",
    }
    STRUCTURAL = {
        "measure": "topics you return to more than once",
        "current": 7, "threshold": 2,
        "direction": "below", "kind": "structural", "unit": "count",
    }

    def _basis_for(self, condition):
        return cal._basis({
            "rule_name": "R", "description": "d",
            "metadata": json.dumps({"basis_version": 2, "exit_condition": condition}),
        })["exit_condition"]

    def test_a_behavioural_condition_states_both_numbers(self):
        sentence = self._basis_for(self.BEHAVIOURAL)["sentence"]
        assert "62%" in sentence and "50%" in sentence
        assert "below" in sentence

    def test_a_structural_condition_says_it_is_not_actionable(self):
        """Otherwise it reads as advice to have fewer interests."""
        sentence = self._basis_for(self.STRUCTURAL)["sentence"]
        assert "not something to act on" in sentence
        assert "%" not in sentence, "a count must not be rendered as a percentage"

    def test_shares_render_as_percentages_and_counts_do_not(self):
        assert "%" in self._basis_for(self.BEHAVIOURAL)["sentence"]

    def test_a_malformed_condition_is_dropped_rather_than_half_rendered(self):
        for broken in ({"measure": "x"}, {"current": 1}, "not a dict", None, []):
            basis = cal._basis({
                "rule_name": "R",
                "metadata": json.dumps({"basis_version": 2, "exit_condition": broken}),
            })
            assert basis["exit_condition"] is None, broken

    def test_older_claims_simply_have_none(self):
        basis = cal._basis({"rule_name": "R", "metadata": json.dumps({"rule_score": 0.5})})
        assert basis["exit_condition"] is None
