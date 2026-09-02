"""The system claimed to weigh evidence against counter-evidence and never did.

Four fields existed on the Evidence model for it - counter_evidence_ids,
conflicting_observations, conflict_resolution, net_confidence - along with
database columns, a GIN index, a write path, a read path, an API field and a
self-model consumer. Every layer was built except the one that produces the
values, so across 341 stored rows in the deployed instance all four were
populated exactly zero times, and every belief the system held came out with a
net evidence strength of precisely 1.0.

The gap had a second half. The collectors filtered events by topic and put all
of them into supporting_events, so an account shown four hundred cooking reels
that scrolled past every one produced strong evidence of interest in cooking.
Skipping was recorded as support.

These tests hold the produced values to the properties that make them worth
recording: that a skip is not support, that an account which skips nothing
reports no counter-evidence rather than a manufactured share, and that the
figures survive merging and reach a belief in the same unit they left in.
"""
from datetime import datetime, timedelta, timezone

import pytest

from reasoning.evidence_engine import (
    EvidenceEngine,
    MIN_EVENTS_FOR_BASELINE,
    MIN_OBSERVATIONS_FOR_NET,
    SKIP_FRACTION_OF_MEDIAN,
    attention_baseline,
    net_confidence_from,
    partition_by_attention,
)
from shared.contracts import BehaviorEvent, ContentType, EventSource

BASE = datetime.now(timezone.utc) - timedelta(days=3)


def event(idx, topic, watch, creator="someone", **flags):
    return BehaviorEvent(
        event_id=str(idx),
        source=EventSource.CHROME_EXTENSION,
        timestamp=BASE + timedelta(minutes=idx),
        session_id="s1",
        content_id=f"reel_{idx}",
        content_type=ContentType.REEL,
        creator=creator,
        caption=f"a video about {topic}",
        hashtags=[topic],
        watch_time=float(watch),
        **flags,
    )


def history(spec):
    """spec: list of (topic, count, watch_time)."""
    events, idx = [], 0
    for topic, count, watch in spec:
        for _ in range(count):
            idx += 1
            events.append(event(idx, topic, watch, creator=f"creator_{topic}"))
    return events


class TestASkipIsNotSupport:
    def test_skipped_events_are_not_filed_as_supporting(self):
        """The defect that made the rest of it moot."""
        events = history([("cooking", 20, 60.0), ("crypto", 20, 4.0)])
        ev = EvidenceEngine().collect_topical_evidence(events=events, topic="crypto")

        assert ev is not None
        assert ev.supporting_events == [], (
            "every crypto reel was scrolled past; none of them support interest"
        )
        assert len(ev.conflicting_observations) == 20

    def test_the_same_events_still_count_as_observed(self):
        """Confidence is a statement about how much was seen, so it must not
        fall just because what was seen pointed the other way. The two
        questions are reported separately on purpose."""
        events = history([("cooking", 20, 60.0), ("crypto", 20, 4.0)])
        ev = EvidenceEngine().collect_topical_evidence(events=events, topic="crypto")

        assert ev.confidence == 1.0
        assert ev.key_metrics["occurrence_count"] == 20
        assert ev.net_confidence == 0.0


class TestEveryCollectorActuallyRuns:
    """Each collector wraps its body in `except Exception: return None`, so a
    collector that raises is indistinguishable from one that found nothing.
    A NameError introduced into the behavioural collector survived the whole
    suite this way - it is never called by the pipeline, and the one caller
    that might have noticed treats None as "no evidence here".
    """

    def test_all_five_return_evidence_for_a_history_that_has_it(self):
        events = history([("cooking", 20, 60.0), ("crypto", 20, 4.0)])
        engine = EvidenceEngine()

        produced = {
            "behavioral": engine.collect_behavioral_evidence(
                events=events, topic="cooking"),
            "topical": engine.collect_topical_evidence(
                events=events, topic="cooking"),
            "creator": engine.collect_creator_evidence(
                events=events, creator="creator_cooking"),
            "temporal": engine.collect_temporal_evidence(
                events=events, pattern_description="evening viewing"),
            "interaction": engine.collect_interaction_evidence(events=events),
        }

        empty = sorted(name for name, ev in produced.items() if ev is None)
        assert not empty, f"collectors returned nothing (likely raising): {empty}"

    def test_the_subject_collectors_all_weigh_attention(self):
        """Whichever collector is wired up next should already do this."""
        events = history([("cooking", 20, 60.0), ("crypto", 20, 4.0)])
        engine = EvidenceEngine()

        for ev in (
            engine.collect_behavioral_evidence(events=events, topic="crypto"),
            engine.collect_topical_evidence(events=events, topic="crypto"),
            engine.collect_creator_evidence(events=events, creator="creator_crypto"),
        ):
            assert ev.conflicting_observations, ev.evidence_type
            assert ev.net_confidence == 0.0


class TestAbsenceIsReportable:
    def test_a_history_with_no_skips_produces_no_counter_evidence(self):
        """The property that makes the number worth printing. Taking the bottom
        quartile of each history instead would manufacture counter-evidence for
        everyone and could never report its absence."""
        events = history([("cooking", 30, 60.0)])
        ev = EvidenceEngine().collect_topical_evidence(events=events, topic="cooking")

        assert ev.conflicting_observations == []
        assert ev.conflict_resolution is None
        assert ev.net_confidence == pytest.approx(ev.confidence)


class TestTheLineIsPersonal:
    def test_the_baseline_is_the_viewers_own_median(self):
        """A watch of 20s is a skip for someone who normally watches 90s and
        ordinary for someone who normally watches 30s. An absolute threshold in
        seconds would call both the same."""
        slow = history([("x", 30, 90.0)])
        quick = history([("x", 30, 30.0)])

        assert attention_baseline(slow) == 90.0
        assert attention_baseline(quick) == 30.0

        probe = [event(999, "x", 20.0)]
        assert partition_by_attention(probe, attention_baseline(slow))[1] != []
        assert partition_by_attention(probe, attention_baseline(quick))[1] == []

    def test_a_median_is_used_rather_than_a_mean(self):
        """A handful of very long watches would drag a mean upward and
        reclassify ordinary viewing as skipping."""
        events = history([("x", 20, 10.0), ("x", 2, 1000.0)])
        assert attention_baseline(events) == 10.0

    def test_too_thin_a_history_names_no_skips(self):
        events = history([("x", MIN_EVENTS_FOR_BASELINE - 1, 50.0)])
        assert attention_baseline(events) is None

        attended, skipped = partition_by_attention(
            [event(1, "x", 0.5)], attention_baseline(events)
        )
        assert skipped == [] and len(attended) == 1

    def test_an_interaction_outranks_a_short_watch(self):
        """Someone who saves a reel two seconds in has not skipped it."""
        saved = event(1, "x", 1.0, saved=True)
        ignored = event(2, "x", 1.0)
        attended, skipped = partition_by_attention([saved, ignored], 60.0)

        assert attended == [saved]
        assert skipped == [ignored]


class TestNetConfidence:
    def test_it_is_withheld_when_there_is_too_little_to_judge(self):
        """A balance computed from three observations swings from +1 to -1 on a
        single skip."""
        assert net_confidence_from(1.0, MIN_OBSERVATIONS_FOR_NET - 1, 0) is None

    def test_it_never_goes_below_zero(self):
        """The field is bounded [0, 1]; evidence that is entirely offset is
        offset, not negative."""
        assert net_confidence_from(1.0, 1, 40) == 0.0

    def test_it_falls_as_contradiction_rises(self):
        strong = net_confidence_from(1.0, 40, 0)
        mixed = net_confidence_from(1.0, 30, 10)
        even = net_confidence_from(1.0, 20, 20)

        assert strong > mixed > even
        assert even == 0.0

    def test_it_is_bounded_by_confidence(self):
        """Net confidence discounts confidence, so it can never exceed it."""
        for support in (10, 50, 200):
            assert net_confidence_from(0.4, support, 0) <= 0.4


class TestMergingPreservesTheFindings:
    def test_conflicts_survive_a_merge(self):
        """Two pieces of evidence that each recorded contradictions must not
        combine into one that records none."""
        events = history([("cooking", 20, 60.0), ("crypto", 20, 4.0)])
        engine = EvidenceEngine()
        collected = [
            engine.collect_topical_evidence(events=events, topic=t)
            for t in ("cooking", "crypto")
        ]

        merged = engine.merge_similar_evidence(collected)
        assert sum(len(e.conflicting_observations) for e in merged) == 20

    def test_distinct_creators_are_not_collapsed_into_one_row(self):
        """Grouping keyed on metadata["topic"] alone, and creator evidence
        carries no topic, so every creator was filed under "unknown" and merged
        into a single row whose metadata no longer said which creator it was
        about - averaging an attentively watched creator together with a
        skipped one."""
        events = history([("cooking", 20, 60.0), ("crypto", 20, 4.0)])
        engine = EvidenceEngine()
        collected = [
            engine.collect_creator_evidence(events=events, creator=c)
            for c in ("creator_cooking", "creator_crypto")
        ]
        assert all(e is not None for e in collected)

        merged = engine.merge_similar_evidence(collected)
        creators = sorted(e.metadata.get("creator") for e in merged)

        assert creators == ["creator_cooking", "creator_crypto"]
        by_creator = {e.metadata["creator"]: e.net_confidence for e in merged}
        assert by_creator["creator_crypto"] == 0.0
        assert by_creator["creator_cooking"] > 0.0

    def test_a_merged_row_still_says_what_it_is_about(self):
        events = history([("cooking", 24, 60.0)])
        engine = EvidenceEngine()
        pair = [
            engine.collect_topical_evidence(events=events, topic="cooking"),
            engine.collect_topical_evidence(events=events, topic="cooking"),
        ]
        merged = engine.merge_similar_evidence(pair)

        assert len(merged) == 1
        assert merged[0].metadata["topic"] == "cooking"
        assert merged[0].metadata["merged_count"] == 2


class TestItReachesABelief:
    def _evidence(self, engine, events, topic):
        return engine.collect_topical_evidence(events=events, topic=topic)

    def test_a_belief_counts_observations_against_observations(self):
        """The units have to match. Supporting was a count of evidence objects
        and contradicting a count of individual events, so three pieces of
        evidence carrying thirty skips between them would read as -0.82 and
        bury a belief that is merely mixed."""
        from identity.self_model import SelfModelEngine
        from reasoning.inference_engine import Inference

        events = history([("cooking", 20, 60.0), ("crypto", 20, 4.0)])
        engine = EvidenceEngine()
        evidence = [self._evidence(engine, events, t) for t in ("cooking", "crypto")]

        inference = Inference(
            inference_id="inf_1",
            inference_type="pattern",
            label="mixed",
            description="mixed interests",
            confidence=0.9,
            importance=0.5,
            strength=0.8,
            supporting_evidence=[e.evidence_id for e in evidence],
            evidence_summary="2 pieces",
            inferred_at=datetime.utcnow(),
            valid_from=datetime.utcnow(),
            rule_name="TestRule",
            context_id="ctx",
        )

        beliefs = SelfModelEngine()._generate_beliefs_from_inferences(
            [inference], evidence
        )
        assert len(beliefs) == 1
        belief = beliefs[0]

        # 20 cooking observations support, 20 crypto observations contradict.
        assert belief.counter_evidence_count == 20
        assert belief.net_evidence_strength == pytest.approx(0.0)
        assert -1.0 <= belief.net_evidence_strength <= 1.0

    def test_an_evenly_split_belief_is_reported_as_uncertain(self):
        """Uncertainty used to be 1 - confidence and nothing else, so a belief
        resting on evidence that contradicted itself as often as it supported
        it was still reported as settled."""
        from identity.self_model import Belief, BeliefType, CONTESTED_NET_STRENGTH

        def belief_with(net):
            return Belief(
                belief_id="b",
                belief_type=BeliefType.PATTERN,
                statement="s",
                description="d",
                confidence=0.95,
                uncertainty=0.05,
                strength=0.9,
                net_evidence_strength=net,
                formed_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

        assert belief_with(0.0).is_uncertain()
        assert belief_with(CONTESTED_NET_STRENGTH).is_uncertain()
        assert not belief_with(0.9).is_uncertain()

    def test_strong_and_uncertain_exclude_each_other(self):
        """They were independent predicates, so a belief could be reported as
        settled and as open at the same time. "STRONG, UNCERTAIN otherwise" is
        only a classification if the two cannot both hold."""
        from identity.self_model import Belief, BeliefType

        def belief_with(net):
            return Belief(
                belief_id="b",
                belief_type=BeliefType.PATTERN,
                statement="s",
                description="d",
                confidence=0.95,
                uncertainty=0.05,
                strength=0.9,
                net_evidence_strength=net,
                formed_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

        for net in (-1.0, 0.0, 0.2, 0.34, 0.7, 1.0):
            belief = belief_with(net)
            assert not (belief.is_strong() and belief.is_uncertain()), net

    def test_a_contested_belief_is_not_strong_however_confident(self):
        from identity.self_model import Belief, BeliefType

        contested = Belief(
            belief_id="b", belief_type=BeliefType.PATTERN, statement="s",
            description="d", confidence=1.0, uncertainty=0.0, strength=1.0,
            net_evidence_strength=0.1,
            formed_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        assert not contested.is_strong()


class TestTheThresholdIsDeclaredNotBuried:
    def test_the_skip_fraction_is_a_named_constant(self):
        assert 0.0 < SKIP_FRACTION_OF_MEDIAN < 1.0

    def test_the_reading_does_not_balance_on_the_exact_value(self):
        """Measured on the deployed corpus, 0.25 marks 13-15% of events as
        skips, 0.40 marks 19-20% and 0.50 marks 22-23%. A threshold whose
        neighbours give wildly different answers would not be reportable."""
        events = history([("x", 40, 50.0), ("x", 20, 8.0)])
        baseline = attention_baseline(events)

        shares = []
        for fraction in (0.25, 0.40, 0.50):
            threshold = baseline * fraction
            skipped = sum(1 for e in events if e.watch_time < threshold)
            shares.append(skipped / len(events))

        assert shares[0] <= shares[1] <= shares[2]
        assert max(shares) - min(shares) < 0.25
