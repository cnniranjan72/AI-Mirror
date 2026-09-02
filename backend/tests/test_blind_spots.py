"""Not knowing something and being unsure about it are different claims.

The uncertainty map gave both the same shape. A topic the system had reasoned
about and found itself unsure of got a measured uncertainty; a topic no belief
addressed at all got a flat 0.8 and went into the same dictionary, in the same
scale, under the same key. Across the deployed instance 19 of 50 domain values
were that constant.

Nothing downstream could tell them apart, and three things read that field: the
character runtime, the decision engine, and the context builder that assembles
what the language model is shown. So "I have never considered this" arrived at
the model as "I am highly uncertain about this" - a confident statement of
doubt about a subject nothing had ever been concluded about.

These tests hold the separation in place: that a placeholder is never written,
that a topic nobody has an opinion on is named rather than scored, and that the
matching which decides "no belief addresses this" does not fire on a substring.
"""
from datetime import datetime, timedelta, timezone

import pytest

from identity.self_model import (
    Belief,
    BeliefType,
    UncertaintyMap,
    _mentions,
)


def belief(description, uncertainty=0.2, statement=None):
    return Belief(
        belief_id="b_" + description[:8],
        belief_type=BeliefType.PATTERN,
        statement=statement or description,
        description=description,
        confidence=1.0 - uncertainty,
        uncertainty=uncertainty,
        strength=0.8,
        net_evidence_strength=1.0,
        formed_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestTheMatchingNamesTheTopic:
    def test_a_substring_of_a_longer_word_is_not_a_mention(self):
        """The failure a plain `in` test makes: "art" inside "particle"."""
        assert not _mentions("art", "Primary interests: particle physics")
        assert not _mentions("ai", "Consistent viewing habit detained")

    def test_a_real_mention_is_found(self):
        assert _mentions("travel", "Primary interests: travel, cooking")
        assert _mentions("art", "Primary interests: art, design")

    def test_hashtags_are_matched(self):
        """The usual fix, a \\b word boundary, silently fails for every topic in
        this system: '#' is itself a non-word character, so there is no
        boundary before it and `\\b#ai\\b` never matches anything."""
        assert _mentions("#ai", "Primary interests: #ai, #tech account for 68%")
        assert _mentions("#tech", "Strong learning orientation (#tech, #ai)")

    def test_a_hashtag_is_not_matched_inside_a_longer_tag(self):
        assert not _mentions("#ai", "Primary interests: #ai_research only")

    def test_empty_input_is_not_a_match(self):
        assert not _mentions("", "anything at all")
        assert not _mentions("travel", "")
        assert not _mentions(None, None)


class TestAPlaceholderIsNeverWritten:
    def test_an_unmeasured_domain_gets_no_number(self):
        """The whole point. A domain with nothing behind it must not appear in
        domain_uncertainties at any value, because every consumer of that field
        treats what it finds there as a measurement."""
        umap = UncertaintyMap(
            overall_uncertainty=0.5,
            last_updated=datetime.now(timezone.utc),
        )
        umap.unexamined_domains = ["fitness", "astronomy"]

        assert "fitness" not in umap.domain_uncertainties
        assert "astronomy" not in umap.domain_uncertainties

    def test_unexamined_domains_do_not_reach_the_language_model(self):
        """high_uncertainty_domains is injected into the context the LLM sees
        (rag/context_builder.py). A topic nobody formed a view about must not
        arrive there as a subject the system is uncertain about."""
        umap = UncertaintyMap(
            overall_uncertainty=0.5,
            last_updated=datetime.now(timezone.utc),
        )
        umap.add_domain_uncertainty("crypto", 0.9)
        umap.unexamined_domains = ["fitness"]

        assert "crypto" in umap.high_uncertainty_domains
        assert "fitness" not in umap.high_uncertainty_domains

    def test_lookup_returns_none_rather_than_a_quiet_half(self):
        """It used to return 0.5 for anything absent, which is a made-up
        measurement wearing the same type as a real one."""
        umap = UncertaintyMap(
            overall_uncertainty=0.5,
            last_updated=datetime.now(timezone.utc),
        )
        umap.add_domain_uncertainty("crypto", 0.9)

        assert umap.get_domain_uncertainty("crypto") == 0.9
        assert umap.get_domain_uncertainty("never_seen") is None


class TestTheProducer:
    def _snapshot(self, dominant, emerging=()):
        class Snap:
            dominant_topics = list(dominant)
            emerging_topics = list(emerging)
        return Snap()

    def _build(self, dominant, beliefs, emerging=()):
        from identity.self_model import SelfModelEngine
        return SelfModelEngine()._build_uncertainty_map(
            self._snapshot(dominant, emerging), beliefs
        )

    def test_a_topic_no_belief_mentions_is_reported_as_unexamined(self):
        umap = self._build(
            ["travel", "fitness"],
            [belief("Primary interests: travel, cooking", uncertainty=0.1)],
        )

        assert "travel" in umap.domain_uncertainties
        assert umap.unexamined_domains == ["fitness"]
        assert "fitness" not in umap.domain_uncertainties

    def test_the_producer_uses_token_matching_not_a_bare_substring(self):
        """Reverting _mentions to `topic in description` passes every matcher
        unit test above while still corrupting the producer, so the producer
        needs its own case: "art" occurs inside "particle", and a substring
        test would call the topic assessed and attach someone else's
        uncertainty to it."""
        umap = self._build(
            ["art"],
            [belief("Primary interests: particle physics", uncertainty=0.15)],
        )

        assert umap.unexamined_domains == ["art"]
        assert "art" not in umap.domain_uncertainties

    def test_a_measured_domain_carries_the_belief_uncertainty(self):
        umap = self._build(
            ["travel"],
            [
                belief("Primary interests: travel", uncertainty=0.4),
                belief("Habit covers travel weekly", uncertainty=0.2),
            ],
        )
        assert umap.domain_uncertainties["travel"] == pytest.approx(0.3)

    def test_emerging_topics_are_unexamined_not_scored_at_a_flat_value(self):
        """They were given 0.7 for exactly the reason the 0.8 was wrong: being
        new is a statement about data, not about confidence."""
        umap = self._build(["travel"], [belief("interests: travel")], emerging=["astronomy"])

        assert "astronomy" not in umap.domain_uncertainties
        assert "astronomy" in umap.unexamined_domains

    def test_a_topic_both_dominant_and_emerging_is_listed_once(self):
        umap = self._build(["fitness"], [], emerging=["fitness"])
        assert umap.unexamined_domains == ["fitness"]

    def test_a_measured_topic_is_not_also_listed_as_unexamined(self):
        umap = self._build(
            ["travel"], [belief("interests: travel")], emerging=["travel"]
        )
        assert "travel" in umap.domain_uncertainties
        assert "travel" not in umap.unexamined_domains


class TestTheSurfaceSeparatesThem:
    def test_the_service_reports_the_two_categories_apart(self):
        import inspect
        from app.services import blind_spots

        source = inspect.getsource(blind_spots.build_blind_spots)
        assert '"assessed"' in source
        assert '"unexamined"' in source

    def test_a_model_predating_the_split_is_flagged_rather_than_trusted(self):
        """Rows written before this cannot be repaired: which of their values
        was the 0.8 placeholder is unrecoverable. Saying so beats guessing."""
        import inspect
        from app.services import blind_spots

        source = inspect.getsource(blind_spots.build_blind_spots)
        assert 'stale = "unexamined_domains" not in umap' in source
        assert '"stale_model": stale' in source
