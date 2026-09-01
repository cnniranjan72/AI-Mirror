"""Topic taxonomy — what may become an "interest".

Two defects visible in production, both of which reached the dashboard, the
chat answers and the exported report:

1. The single highest-importance behaviour object was `topic: "uncategorized"`
   at importance 0.9, outranking every real interest. Every event that could
   not be classified was filed into one catch-all bucket, so the union of
   "things we don't understand" reliably became the largest cluster.

2. `dominant_topics` read ["#ai", "Content by lex_fridman_clips", ...].
   Creator clusters were being consumed as topics — a category error, not a
   ranking problem.

No database, no network.
"""
import uuid
from datetime import datetime, timezone

import pytest

from backend.shared.contracts import BehaviorEvent
from backend.engines.knowledge_consolidation import (
    KnowledgeConsolidationEngine, _normalize_topic_token, _candidate_topics,
)
from backend.reasoning.behavior_object import is_creator_behavior


def _event(caption="", hashtags=None, creator="someone", watch=30.0):
    return BehaviorEvent(
        event_id=f"evt_{uuid.uuid4().hex[:10]}",
        user_id="test_user",
        platform="instagram",
        content_id=f"reel_{uuid.uuid4().hex[:8]}",
        caption=caption,
        hashtags=hashtags or [],
        creator=creator,
        watch_time=watch,
        timestamp=datetime.now(timezone.utc),
        source="chrome_extension",
        session_id="taxonomy_session",
    )


class TestTokenNormalisation:
    @pytest.mark.parametrize("raw,expected", [
        ("#AI", None),          # below the minimum length once '#' is stripped
        ("#travel", "travel"),
        ("Travel", "travel"),
        ("#machinelearning", "machinelearning"),
        ("cooking!", "cooking"),
    ])
    def test_normalises_usable_tokens(self, raw, expected):
        assert _normalize_topic_token(raw) == expected

    @pytest.mark.parametrize("raw", [
        "", "  ", "#", "a", "of", "#2024", "1000", "####",
        # Long enough to survive a naive length filter, but meaningless as a
        # subject — these are exactly what polluted the interest graph.
        "because", "through", "already", "perfection", "awesome", "subscribe",
    ])
    def test_rejects_noise(self, raw):
        assert _normalize_topic_token(raw) is None


class TestCandidateExtraction:
    def test_prefers_hashtags(self):
        event = _event(caption="some caption about cooking", hashtags=["#travel"])
        assert _candidate_topics(event) == ["travel"]

    def test_falls_back_to_caption_only_without_hashtags(self):
        event = _event(caption="Deep dive into robotics research")
        candidates = _candidate_topics(event)
        assert "robotics" in candidates
        assert "research" in candidates

    def test_yields_nothing_when_there_is_no_signal(self):
        assert _candidate_topics(_event()) == []
        assert _candidate_topics(_event(caption="it is on the go")) == []


class TestNoCatchAllBucket:
    """Defect 1."""

    def test_unclassifiable_events_do_not_form_a_topic(self):
        engine = KnowledgeConsolidationEngine()
        # Ten events with nothing topical to say. Under the old behaviour these
        # became a single "uncategorized" cluster of size 10 — bigger, and so
        # more "important", than any genuine interest.
        events = [_event(creator=f"creator_{i}") for i in range(10)]

        clusters, unclustered = engine.consolidate_events(events)

        topics = [c.primary_topic for c in clusters if c.cluster_type == "topic"]
        assert topics == []
        assert "uncategorized" not in [c.primary_topic for c in clusters]
        # They are still reported, not silently dropped.
        assert len(unclustered) == 10

    def test_a_real_topic_still_clusters(self):
        engine = KnowledgeConsolidationEngine()
        events = [_event(hashtags=["#robotics"]) for _ in range(5)]

        clusters, _ = engine.consolidate_events(events)

        topics = [c.primary_topic for c in clusters if c.cluster_type == "topic"]
        assert topics == ["robotics"]

    def test_noise_does_not_outrank_a_real_interest(self):
        """The regression in one assertion: unclassifiable volume must not
        produce a cluster that beats a smaller, genuine one."""
        engine = KnowledgeConsolidationEngine()
        events = [_event(creator=f"noise_{i}") for i in range(20)]
        events += [_event(hashtags=["#robotics"]) for _ in range(4)]

        clusters, _ = engine.consolidate_events(events)
        topic_clusters = [c for c in clusters if c.cluster_type == "topic"]

        assert [c.primary_topic for c in topic_clusters] == ["robotics"]


class TestFrequencyChoosesThePrimaryTopic:
    def test_batch_frequency_beats_hashtag_order(self):
        """A tag the creator happened to type first should not outrank the tag
        that actually recurs across the batch."""
        engine = KnowledgeConsolidationEngine()
        # "gardening" is first on every event but appears once each; "robotics"
        # is second but is the shared thread.
        events = [_event(hashtags=[f"#gardening{i}", "#robotics"]) for i in range(4)]

        clusters, _ = engine.consolidate_events(events)
        topics = [c.primary_topic for c in clusters if c.cluster_type == "topic"]

        assert topics == ["robotics"]


class TestUbiquitousTokensLose:
    """Found by running a real demo, not by reasoning about the code.

    Ranking candidates by raw batch frequency meant a token present in EVERY
    item won by definition: 118 events titled "<hobby> clip number N" all
    collapsed into the single topic "clip". Frequency rewards ubiquity, and
    ubiquity is exactly what carries no information about the subject.
    """

    def test_boilerplate_common_to_every_event_never_wins(self):
        engine = KnowledgeConsolidationEngine()
        events = []
        for topic in ("robotics", "pottery", "astronomy"):
            for i in range(5):
                events.append(_event(caption=f"{topic} clip number {i}"))

        clusters, _ = engine.consolidate_events(events)
        topics = {c.primary_topic for c in clusters if c.cluster_type == "topic"}

        assert "clip" not in topics
        assert "number" not in topics
        assert topics == {"robotics", "pottery", "astronomy"}

    def test_a_single_subject_account_still_gets_its_topic(self):
        """The guard on the fix: if someone watches nothing but robotics,
        "robotics" appears in 100% of events and its idf is zero — but it is
        still the correct topic, so the ranking falls back to frequency."""
        engine = KnowledgeConsolidationEngine()
        events = [_event(hashtags=["#robotics"]) for _ in range(6)]

        clusters, _ = engine.consolidate_events(events)
        topics = [c.primary_topic for c in clusters if c.cluster_type == "topic"]

        assert topics == ["robotics"]


class TestCreatorsAreNotTopics:
    """Defect 2."""

    def test_creator_clusters_are_identified(self):
        engine = KnowledgeConsolidationEngine()
        events = [_event(hashtags=["#robotics"], creator="lex_fridman_clips") for _ in range(4)]

        clusters, _ = engine.consolidate_events(events)
        creator_clusters = [c for c in clusters if c.cluster_type == "creator"]

        assert creator_clusters, "a repeated creator should still be tracked"
        assert creator_clusters[0].primary_topic.startswith("Content by ")

    @pytest.mark.parametrize("behavior,expected", [
        (type("B", (), {"metadata": {"cluster_type": "creator"}, "topic": "Content by x"})(), True),
        # Legacy rows predate the marker; the label is the fallback.
        (type("B", (), {"metadata": {}, "topic": "Content by lex_fridman_clips"})(), True),
        (type("B", (), {"metadata": {"cluster_type": "topic"}, "topic": "robotics"})(), False),
        (type("B", (), {"metadata": None, "topic": "robotics"})(), False),
        # A genuine subject that merely mentions content is not a creator.
        (type("B", (), {"metadata": {}, "topic": "content marketing"})(), False),
    ])
    def test_creator_predicate(self, behavior, expected):
        assert is_creator_behavior(behavior) is expected
