"""Nine sub-profiles, nine confidences, computed from nine different inputs.

The architecture describes nine sub-profiles "each with an independently
computed confidence, aggregated by evidence volume and recency". Measured
against the deployed instance, seven of the nine had no confidence field at
all. The two that did were binary constants:

    confidence = 0.7 if learning_inferences else 0.5     # LearningStyle
    confidence = 0.7 if inferences else 0.5              # MotivationSignals

Across twelve accounts those two fields took three values between them, and
neither depended on volume or on recency.

The point of a per-profile figure is that the profiles do not rest on the same
evidence. An account can carry plenty of topic observations and almost no
timing data, and a single identity-wide number cannot say so - nine copies of
it say it nine times over.

A related defect sat next to it. Overall identity confidence substituted a flat
0.5 for each absent component, which is 40% of the weight asserting moderate
confidence about evidence and inferences that do not exist: an account with two
behaviour objects and nothing else reported 0.700 overall while every one of
its sub-profiles independently reported about 0.10.
"""
from datetime import datetime, timedelta, timezone

import pytest

from identity.profile_confidence import (
    CEILING,
    RECENCY_HALF_LIFE_DAYS,
    VOLUME_SATURATION,
    newest,
    profile_confidence,
)

NOW = datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc)


def ago(days):
    return NOW - timedelta(days=days)


class TestVolume:
    def test_nothing_supporting_gives_no_confidence(self):
        result = profile_confidence(0, ago(1), now=NOW)
        assert result["confidence"] == 0.0
        assert "nothing supports" in result["basis"]

    def test_confidence_rises_with_observations(self):
        few = profile_confidence(2, ago(1), now=NOW)["confidence"]
        some = profile_confidence(10, ago(1), now=NOW)["confidence"]
        many = profile_confidence(20, ago(1), now=NOW)["confidence"]
        assert few < some < many

    def test_volume_saturates(self):
        at = profile_confidence(int(VOLUME_SATURATION), ago(0), now=NOW)
        beyond = profile_confidence(int(VOLUME_SATURATION) * 5, ago(0), now=NOW)
        assert at["volume"] == 1.0
        assert beyond["volume"] == 1.0

    def test_the_saturation_point_can_differ_per_profile(self):
        """Exploration is a claim about breadth, so it saturates on distinct
        topics rather than on observation count."""
        wide = profile_confidence(10, ago(0), saturation=10.0, now=NOW)
        narrow = profile_confidence(10, ago(0), saturation=20.0, now=NOW)
        assert wide["volume"] > narrow["volume"]


class TestRecency:
    def test_old_support_is_worth_less(self):
        fresh = profile_confidence(20, ago(0), now=NOW)["confidence"]
        stale = profile_confidence(20, ago(90), now=NOW)["confidence"]
        assert fresh > stale

    def test_the_half_life_is_what_it_says(self):
        one = profile_confidence(20, ago(RECENCY_HALF_LIFE_DAYS), now=NOW)
        assert one["recency"] == pytest.approx(0.5, abs=0.01)

    def test_volume_and_recency_combine_rather_than_average(self):
        """Plenty of year-old observations do not make a half-confident
        profile; they describe somebody who may no longer exist."""
        result = profile_confidence(40, ago(365), now=NOW)
        assert result["volume"] == 1.0
        assert result["confidence"] < 0.05

    def test_a_missing_timestamp_is_not_read_as_current(self):
        """Assuming freshness would be the most flattering reading available."""
        unknown = profile_confidence(20, None, now=NOW)
        current = profile_confidence(20, ago(0), now=NOW)
        assert unknown["confidence"] < current["confidence"]
        assert "no timestamp" in unknown["basis"]

    def test_newest_picks_the_latest_of_several(self):
        assert newest([ago(10), ago(1), ago(5)]) == ago(1)
        assert newest([]) is None
        assert newest([None, "not a date"]) is None


class TestItNeverOverclaims:
    def test_confidence_is_capped(self):
        result = profile_confidence(10_000, ago(0), now=NOW)
        assert result["confidence"] <= CEILING

    def test_the_ceiling_is_below_certainty(self):
        """Volume and recency say how much was seen and how lately, not whether
        the reading was right. Correctness is the Accuracy Ledger's question."""
        assert CEILING < 1.0

    def test_every_figure_carries_its_basis(self):
        for n, when in ((0, None), (3, ago(2)), (50, ago(400))):
            result = profile_confidence(n, when, now=NOW)
            assert result["basis"]
            assert "observations" in result


class TestAllNineAreWired:
    PROFILES = [
        "behavior_profile", "interest_graph", "creator_graph", "learning_style",
        "attention_profile", "exploration_profile", "consistency_profile",
        "habit_profile", "motivation_signals",
    ]

    def test_every_sub_profile_model_can_hold_a_confidence(self):
        """Seven of the nine had nowhere to put one."""
        from identity import identity_engine as ie

        models = {
            "behavior_profile": ie.BehaviorProfile,
            "interest_graph": ie.InterestGraph,
            "creator_graph": ie.CreatorGraph,
            "learning_style": ie.LearningStyle,
            "attention_profile": ie.AttentionProfile,
            "exploration_profile": ie.ExplorationProfile,
            "consistency_profile": ie.ConsistencyProfile,
            "habit_profile": ie.HabitProfile,
            "motivation_signals": ie.MotivationSignals,
        }
        missing = [
            name for name, model in models.items()
            if "confidence" not in model.model_fields
            or "confidence_basis" not in model.model_fields
        ]
        assert not missing, f"no confidence field on: {missing}"

    def test_each_profile_draws_on_its_own_subset(self):
        """Nine copies of one number would satisfy "has a confidence" while
        saying nothing. The inputs have to differ."""
        import inspect
        from identity.identity_engine import IdentityEngine

        source = inspect.getsource(IdentityEngine._attach_profile_confidences)
        for subset in ("topics", "creators", "attended", "habitual",
                       "distinct_topics"):
            assert subset in source, subset
        assert "len(inferences" in source

    def test_profiles_resting_on_different_data_get_different_numbers(self):
        """The behavioural version of the check above: naming the subsets in
        the source is not the same as using them, and substituting the full
        behaviour list for one of them leaves every name in place."""
        from identity.identity_engine import IdentityEngine

        engine = IdentityEngine()

        class Temporal:
            last_seen = NOW
            occurrence_count = 5

        class Watch:
            avg_watch_time = 40.0

        def behaviour(topic, creators):
            b = type("B", (), {})()
            b.topic = topic
            b.creators = creators
            b.temporal_statistics = Temporal()
            b.watch_statistics = Watch()
            return b

        # Sixteen creator clusters and four topics: the creator graph rests on
        # four times the data the interest graph does.
        behaviours = (
            [behaviour(f"Content by c{i}", [f"c{i}"]) for i in range(16)]
            + [behaviour(f"topic{i}", []) for i in range(4)]
        )

        profiles = {}
        for name in self.PROFILES:
            profiles[name] = type("P", (), {"confidence": 0.0,
                                            "confidence_basis": {}})()

        engine._attach_profile_confidences(
            behaviors=behaviours, inferences=[], profiles=profiles)

        interest = profiles["interest_graph"].confidence
        creator = profiles["creator_graph"].confidence
        assert creator > interest, (creator, interest)
        assert profiles["motivation_signals"].confidence == 0.0

    def test_the_binary_constants_are_gone(self):
        import inspect
        from identity import identity_engine

        source = inspect.getsource(identity_engine)
        assert "0.7 if learning_inferences else 0.5" not in source
        assert "0.7 if inferences else 0.5" not in source


class TestOverallConfidenceDoesNotInventItsParts:
    def _engine(self):
        from identity.identity_engine import IdentityEngine
        return IdentityEngine()

    def _behaviour(self, confidence=0.5):
        class B:
            confidence_score = confidence
        return B()

    def test_absent_components_do_not_contribute_a_flat_half(self):
        """Two behaviour objects and nothing else reported 0.700 overall while
        every sub-profile reported about 0.10.

        Asserted exactly rather than against a loose bound: with evidence and
        inferences dropped, the result must be the weighted mean of the two
        components that exist, and a reinstated 0.5 filler changes it.
        """
        engine = self._engine()
        overall = engine._calculate_identity_confidence(
            behaviors=[self._behaviour(1.0) for _ in range(20)],
            inferences=[],
            evidence=[],
        )
        # Volume 20/20 = 1.0 and behaviour confidence 1.0, with nothing
        # else in existence, so the answer is 1.0. Values of 0.5 would
        # hide the defect, since the filler is itself 0.5; a reinstated
        # filler drags this to 0.8.
        assert overall == pytest.approx(1.0, abs=0.001), overall

    def test_it_cannot_exceed_what_the_data_supports(self):
        """The cap is the point. Two behaviour objects cannot yield a confident
        identity however sure the engine is about each one."""
        engine = self._engine()
        overall = engine._calculate_identity_confidence(
            behaviors=[self._behaviour(0.9) for _ in range(2)],
            inferences=[],
            evidence=[],
        )
        # 2 of 20 observations is a volume of 0.1, so nothing above that is
        # available no matter how confident the individual behaviours are.
        assert overall == pytest.approx(0.1, abs=0.001), overall

    def test_more_data_still_raises_it(self):
        engine = self._engine()
        thin = engine._calculate_identity_confidence(
            [self._behaviour(0.6) for _ in range(2)], [], [])
        thick = engine._calculate_identity_confidence(
            [self._behaviour(0.6) for _ in range(20)], [], [])
        assert thick > thin

    def test_no_behaviours_is_zero_not_a_guess(self):
        engine = self._engine()
        assert engine._calculate_identity_confidence([], [], []) == 0.0
