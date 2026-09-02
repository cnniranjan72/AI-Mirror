"""A claim that fires for everyone says nothing about anyone.

LearningMotivationRule asserts "strong learning orientation". It classified a
behaviour object as educational by substring-matching keywords against the
topic PLUS its subtopics AND its keywords, so a cluster was classified by the
company it kept: on real production data `#cooking` and `#fitness` counted as
educational because neighbouring topics mentioned coding, and 45% of all 195
behaviour objects qualified against a 10% threshold.

Surfaced by the exit-condition feature, which put the share on screen. A number
nobody could see was a number nobody questioned.

Matching the topic alone brings it to 9%, and the rule now fires for 3 of 10
users with enough data rather than nearly all of them.
"""
import pytest

from backend.reasoning.rules import LearningMotivationRule


class _Stats:
    def __init__(self, count): self.occurrence_count = count


class FakeBehavior:
    def __init__(self, topic, subtopics=None, keywords=None, occurrences=10):
        self.topic = topic
        self.subtopics = subtopics or []
        self.keywords = keywords or []
        self.temporal_statistics = _Stats(occurrences)
        self.unique_id = f"bo_{topic}"
        self.creators = []


@pytest.fixture
def rule():
    return LearningMotivationRule()


class TestNeighboursDoNotClassify:
    """The bug this file exists for."""

    def test_a_cooking_topic_is_not_educational_because_of_its_neighbours(self, rule):
        behaviour = FakeBehavior("#cooking", subtopics=["coding", "tech"])
        assert rule._educational([behaviour]) == []

    def test_nor_because_of_its_own_keywords(self, rule):
        """Keywords are extracted from surrounding content, not a statement
        about what the topic is."""
        behaviour = FakeBehavior("#fitness", keywords=["tech tips", "science"])
        assert rule._educational([behaviour]) == []

    def test_a_genuinely_technical_topic_still_counts(self, rule):
        for topic in ("#coding", "#tech", "Content by creative_coding"):
            assert rule._educational([FakeBehavior(topic)]), topic


class TestWholeWordMatching:
    def test_tech_does_not_fire_inside_a_longer_word(self, rule):
        """Substring matching classified anything containing those letters."""
        assert rule._educational([FakeBehavior("biotechnology")]) == []
        assert rule._educational([FakeBehavior("architecture")]) == []

    def test_multi_word_phrases_still_match_as_phrases(self, rule):
        """"how to" cannot be a single token, so it keeps a substring test."""
        assert rule._educational([FakeBehavior("how to bake sourdough")])


class TestTheShare:
    def test_share_is_weighted_by_activity_not_topic_count(self, rule):
        """One heavily-watched educational topic outweighs several glanced-at
        ones."""
        behaviours = [
            FakeBehavior("#coding", occurrences=90),
            FakeBehavior("#cooking", occurrences=5),
            FakeBehavior("#fitness", occurrences=5),
        ]
        share = rule._edu_share(behaviours, rule._educational(behaviours))
        assert share == pytest.approx(0.9, abs=0.01)

    def test_no_educational_content_is_zero_not_an_error(self, rule):
        behaviours = [FakeBehavior("#cooking"), FakeBehavior("#fitness")]
        assert rule._edu_share(behaviours, rule._educational(behaviours)) == 0.0

    def test_an_empty_corpus_does_not_divide_by_zero(self, rule):
        assert rule._edu_share([], []) == 0.0


class TestItIsSelective:
    def test_a_non_technical_user_does_not_get_the_claim(self, rule):
        """Before this, neighbouring subtopics were enough to fire it."""
        behaviours = [
            FakeBehavior("#cooking", subtopics=["tech", "coding"], occurrences=50),
            FakeBehavior("#fitness", subtopics=["science"], occurrences=50),
            FakeBehavior("#travel", keywords=["guide"], occurrences=50),
        ]
        assert rule.condition(behaviours, [], []) is False

    def test_a_technical_user_still_gets_it(self, rule):
        behaviours = [
            FakeBehavior("#coding", occurrences=40),
            FakeBehavior("#cooking", occurrences=30),
            FakeBehavior("#travel", occurrences=30),
        ]
        assert rule.condition(behaviours, [], []) is True

    def test_the_exit_condition_reports_the_same_share(self, rule):
        """The number shown to the user must be the number the rule used."""
        behaviours = [
            FakeBehavior("#coding", occurrences=40),
            FakeBehavior("#cooking", occurrences=60),
        ]
        condition = rule.exit_condition(behaviours, [], [])
        assert condition["current"] == pytest.approx(0.4, abs=0.01)
        assert condition["threshold"] == 0.10


class TestTheKnownLimitationIsRecorded:
    def test_the_docstring_names_the_subject_versus_intent_gap(self):
        """This measures subject matter, not instructional intent. Left in
        place deliberately, so the reasoning has to survive in the code."""
        doc = LearningMotivationRule._educational.__doc__
        assert "instructional intent" in doc
        assert "caption" in doc
