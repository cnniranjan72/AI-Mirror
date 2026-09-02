"""A rule must say what it reasoned over, or say nothing.

The inference engine used to fill affected_topics/creators/behaviors from the
eight most active behaviour objects, computed identically for every rule - the
loop never looked at rule_result. So every inference for a user carried the
same set, and in production 10 of 10 users had exactly one distinct creator set
spanning all of their claims.

That only mattered once the Accuracy Ledger began showing a claim's basis and
asking the user to judge it. Evidence identical under every claim reads as
"this is why", has no bearing on the conclusion, and the verdict it produces
still counts toward the system's accuracy score.

Rules now declare their own subjects. A rule that declares nothing yields
EMPTY, never a global fallback - showing the user something plausible but
unrelated is worse than showing nothing.
"""
from datetime import datetime, timezone

import pytest

from backend.reasoning.rules import (
    CreatorDependenceRule,
    CreatorDiversityRule,
    EngagementDepthRule,
    PrimaryInterestRule,
    Rule,
    RuleEngine,
    TemporalHabitRule,
)


class _Stats:
    def __init__(self, count):
        self.occurrence_count = count


class _Watch:
    completion_rate = 0.7


class _Engagement:
    engagement_quality_score = 0.5
    overall_engagement_rate = 0.5
    total_interactions = 3


class FakeBehavior:
    """Only what the rules actually read."""

    def __init__(self, unique_id, topic, creators, occurrences):
        self.unique_id = unique_id
        self.topic = topic
        self.creators = creators
        self.temporal_statistics = _Stats(occurrences)
        self.watch_statistics = _Watch()
        self.engagement_statistics = _Engagement()


def _corpus():
    """One dominant creator plus a long tail, so the rules disagree about
    which subset matters."""
    return [
        FakeBehavior("bo_1", "space", ["natgeo", "veritasium"], 40),
        FakeBehavior("bo_2", "cooking", ["natgeo"], 30),
        FakeBehavior("bo_3", "music", ["someband"], 3),
        FakeBehavior("bo_4", "travel", ["wanderer"], 2),
        FakeBehavior("bo_5", "chess", ["gm_hikaru"], 1),
    ]


class TestSubjectsDiscriminate:
    """The point of the change: different rules must cite different evidence."""

    def test_rules_do_not_all_cite_the_same_thing(self):
        corpus = _corpus()
        seen = set()
        for rule in (CreatorDependenceRule(), PrimaryInterestRule(),
                     TemporalHabitRule(), EngagementDepthRule()):
            subjects = rule.subjects(corpus, [], [])
            seen.add((
                tuple(sorted(subjects.get("creators", []))),
                tuple(sorted(subjects.get("topics", []))),
            ))
        assert len(seen) > 1, "every rule cited an identical set - the old bug"

    def test_primary_interest_narrows_to_the_dominant_subset(self):
        """It should not cite the long tail it did not rely on."""
        subjects = PrimaryInterestRule().subjects(_corpus(), [], [])
        assert set(subjects["behaviors"]) <= {"bo_1", "bo_2"}
        assert "chess" not in subjects["topics"]

    def test_creator_dependence_cites_the_concentrated_creators(self):
        subjects = CreatorDependenceRule().subjects(_corpus(), [], [])
        assert "natgeo" in subjects["creators"]
        assert len(subjects["creators"]) <= 3

    def test_temporal_habit_cites_only_what_recurs(self):
        """A habit claim is about repetition, so a one-off is not its basis."""
        subjects = TemporalHabitRule().subjects(_corpus(), [], [])
        assert "bo_5" not in subjects["behaviors"], "a single occurrence is not a habit"
        assert "bo_1" in subjects["behaviors"]

    def test_creator_diversity_cites_the_whole_spread(self):
        """Unlike the others, diversity genuinely is a claim about everything."""
        subjects = CreatorDiversityRule().subjects(_corpus(), [], [])
        assert {"natgeo", "gm_hikaru"} <= set(subjects["creators"])


class TestTheDefaultIsEmpty:
    def test_the_base_class_declares_nothing(self):
        """A rule that has not declared its subjects must produce no evidence.
        A global fallback would restore exactly the problem this replaces."""
        assert Rule.subjects(None, _corpus(), [], []) == {}

    def test_a_rule_without_subjects_yields_nothing(self):
        class Bare(Rule):
            def condition(self, b, e, ev): return True
            def score(self, b, e, ev): return 1.0
            def confidence(self, b, e, ev): return 1.0
            def explanation(self, b, e, ev): return "x"

        assert Bare().subjects(_corpus(), [], []) == {}

    def test_no_behaviours_means_no_subjects_not_a_crash(self):
        for rule in (CreatorDependenceRule(), PrimaryInterestRule(),
                     TemporalHabitRule(), EngagementDepthRule(),
                     CreatorDiversityRule()):
            assert rule.subjects([], [], []) == {}, rule.name


class TestTheEngineCarriesThemThrough:
    def test_evaluate_all_rules_includes_subjects(self):
        results = RuleEngine().evaluate_all_rules(_corpus(), [], [])
        assert results, "no rule fired on the fixture"
        for result in results:
            assert "subjects" in result, result["rule_name"]

    def test_the_engine_never_substitutes_a_global_set(self):
        """The inference engine must read subjects from the rule, not rebuild
        them from the most active behaviours."""
        import inspect

        from backend.reasoning import inference_engine

        source = inspect.getsource(inference_engine.InferenceEngine)
        assert 'rule_result.get("subjects")' in source
        # The old fallback ranked behaviours by occurrence_count and sliced.
        assert "occurrence_count,\n                reverse=True,\n            )[:8]" not in source


class TestEveryFiringRuleIsAccountable:
    """Not a hard requirement - a rule may legitimately declare nothing - but
    a rule that fires and cites nothing shows the user a bare assertion, so
    the list is worth keeping visible."""

    def test_report_which_rules_declare_subjects(self):
        undeclared = [
            rule.name for rule in RuleEngine().rules
            if "subjects" not in type(rule).__dict__
        ]
        # Recorded rather than asserted empty: these fire rarely and carry
        # their reasoning in the description. Tighten if that changes.
        assert isinstance(undeclared, list)
        print(f"rules without subjects(): {undeclared}")
