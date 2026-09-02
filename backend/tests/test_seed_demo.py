"""The one-click demo has to demonstrate the product.

Two problems, both found by running /seed and reading the result rather than
the code.

The pipeline produced ZERO behaviour objects from 800 events. recency_score is
computed as 1.0 - (now - last_seen).days / 30.0, timedelta.days floors toward
negative infinity, and the seed generated timestamps up to an hour in the
future - so a single future-dated event gave -1 days, a score of 1.0333, and
BehaviorObject bounds it at le=1. Construction raised, the whole consolidation
step was caught by one try/except returning [], and the user ended up with no
behaviours, no inferences and an empty Report. Logged, but indistinguishable
from "no data yet". Clock skew on a real client produces the same thing.

And the demo seeded no platform-side data at all, so the Algorithmic Mirror had
nothing to audit and Interest Provenance could not tell a chosen interest from
a fed one - the three features the product is actually about were blank in its
own demo.
"""
import pytest


class TestRecencyScoreIsBounded:
    """The arithmetic that discarded every behaviour object."""

    @staticmethod
    def _recency(days_since):
        return min(1.0, max(0.0, 1.0 - days_since / 30.0))

    def test_a_future_timestamp_does_not_exceed_one(self):
        """timedelta.days is -1 for anything under a day ahead, which produced
        1.0333 - outside BehaviorObject's le=1 bound."""
        assert self._recency(-1) == 1.0
        assert self._recency(-400) == 1.0

    def test_an_old_timestamp_does_not_go_negative(self):
        assert self._recency(9999) == 0.0

    def test_ordinary_values_are_untouched(self):
        assert self._recency(0) == 1.0
        assert self._recency(15) == 0.5
        assert self._recency(30) == 0.0

    def test_the_orchestrator_clamps_both_ends(self):
        import inspect

        from pipeline.orchestrator import V3Pipeline

        source = inspect.getsource(V3Pipeline)
        assert "min(1.0, max(0.0, 1.0 - (now - cluster.last_seen).days / 30.0))" in source


class TestOneBadClusterIsNotFatal:
    def test_consolidation_isolates_each_cluster(self):
        """It used to sit under a single try/except returning [], so one
        malformed cluster cost every behaviour object for the run."""
        import inspect

        from pipeline.orchestrator import V3Pipeline

        source = inspect.getsource(V3Pipeline._consolidate_events)
        assert "skipped" in source, "failures must be counted, not swallowed whole"
        # The per-cluster handler sits inside the loop.
        assert source.index("for cluster in clusters:") < source.index("except Exception as e:")


class TestSeedTimestamps:
    def test_generated_events_are_all_in_the_past(self):
        from datetime import datetime

        from app.api.seed import _generate_events

        now = datetime.now()
        events = _generate_events("demo_test", 400)
        future = [e for e in events if datetime.fromisoformat(e["timestamp"]) > now]
        assert not future, f"{len(future)} seeded events are in the future"


class TestSeedShapesAProfile:
    """Uniformly random interests are no interests: every rule sees a flat
    distribution and the twin has nothing to say."""

    def test_core_topics_dominate(self):
        from collections import Counter

        from app.api.seed import CORE_TOPICS, _generate_events

        events = _generate_events("demo_test", 600)
        counts = Counter()
        for event in events:
            for topic in CORE_TOPICS:
                if topic.lower() in event["caption"].lower():
                    counts[topic] += 1
        core_share = sum(counts.values()) / len(events)
        assert core_share > 0.25, f"core topics only {core_share:.0%} of events"


class TestTheDemoSeedsThePlatformSide:
    """Without these the Mirror has nothing to audit and Provenance cannot
    distinguish a chosen interest from a fed one."""

    def test_claims_cover_every_verdict_the_mirror_can_reach(self):
        from app.api.seed import DEMO_CLAIMS
        from app.services.algorithmic_mirror import _is_non_testable

        labels = [label for _platform, label in DEMO_CLAIMS]
        assert len(labels) >= 6
        non_testable = [l for l in labels if _is_non_testable(l.lower())]
        assert non_testable, "nothing lands in not_comparable, so that bucket is never shown"
        assert len(non_testable) < len(labels), "everything is non-testable"

    def test_searches_exist_for_provenance_to_use(self):
        from app.api.seed import DEMO_SEARCHES
        from app.services.interest_provenance import MIN_DELIBERATE_SIGNALS

        assert len(DEMO_SEARCHES) >= MIN_DELIBERATE_SIGNALS

    def test_verdicts_are_never_seeded(self):
        """The Accuracy Ledger's whole claim is that its score comes from what
        a real person said. Fabricating verdicts would make the one number that
        measures honesty dishonest."""
        import inspect

        from app.api import seed

        assert "claim_verdicts" not in inspect.getsource(seed)
