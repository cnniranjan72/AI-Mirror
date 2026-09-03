"""What the 596-query benchmark actually measures.

The reported figure - 81.21% accuracy, macro F1 0.8214 - reproduces exactly.
It is also two very different halves reported as one number:

    curated    110 queries    accuracy 1.0000
    synthetic  486 queries    accuracy 0.7695

A rule set scores 100% against the examples it was written from, and every one
of the 110 curated queries is such an example. Including them in the headline
credits the classifier with a generalisation it has not shown.

Reading the synthetic failures spent that half too: any pattern added
afterwards is informed by them. So playground/intent_holdout.py was written
fresh, by hand, and never consulted while the patterns were being changed. On
it the classifier scored 0.3056 - against a published 0.8121.

These tests hold the separation rather than a number. Accuracy on any of these
sets will move as the classifier changes; what must not move is that curated
performance is never reported as evidence of generalisation, and that the
holdout stays uncontaminated.
"""
import pytest

pytestmark = pytest.mark.playground


def _planner():
    from cognitive_planning.intent_planner import get_intent_planner
    return get_intent_planner()


def _score(pairs):
    planner = _planner()
    correct = sum(
        1 for query, expected in pairs
        if planner.classify(query).intent_type.value == expected
    )
    return correct / len(pairs) if pairs else 0.0


def _sets():
    from playground.intent_dataset import INTENT_DATASET as CURATED
    from playground.intent_dataset_expanded import EXPANDED_DATASET
    from playground.intent_holdout import HOLDOUT_DATASET

    curated_queries = {q for q, _ in CURATED}
    curated = [(q, l) for q, l in EXPANDED_DATASET if q in curated_queries]
    synthetic = [(q, l) for q, l in EXPANDED_DATASET if q not in curated_queries]
    return curated, synthetic, HOLDOUT_DATASET


class TestTheSetsStaySeparate:
    def test_the_holdout_shares_no_query_with_the_benchmark(self):
        """The moment it overlaps it stops being an estimate of anything."""
        curated, synthetic, holdout = _sets()
        benchmark = {q for q, _ in curated} | {q for q, _ in synthetic}
        overlap = sorted(q for q, _ in holdout if q in benchmark)
        assert not overlap, f"holdout leaked into the benchmark: {overlap}"

    def test_the_holdout_covers_more_than_one_intent(self):
        """A single-class holdout would flatter any change to that class."""
        _curated, _synthetic, holdout = _sets()
        assert len({label for _q, label in holdout}) >= 8

    def test_the_benchmark_halves_are_both_present(self):
        curated, synthetic, _holdout = _sets()
        assert len(curated) == 110
        assert len(synthetic) > 400


class TestCuratedIsATrainingScore:
    def test_curated_is_effectively_saturated(self):
        """Recorded as the reason it cannot be read as generalisation: the
        rules were written from these queries, so a perfect score is what the
        method produces by construction, not evidence about unseen input."""
        curated, _synthetic, _holdout = _sets()
        assert _score(curated) >= 0.99

    def test_unseen_phrasing_scores_far_below_it(self):
        """The gap is the finding. If this ever stops being true the reported
        figure has become meaningful and this test should be revisited - but it
        should be revisited deliberately, not by quietly deleting it."""
        curated, _synthetic, holdout = _sets()
        assert _score(holdout) < _score(curated) - 0.2


class TestTheIdentityFix:
    def test_identity_questions_are_read_by_subject_not_frame(self):
        """The patterns matched frames - "what kind of X am I" - so "describe
        my values" and "tell me about my strengths" were read as generic
        information requests. These are the subjects, in frames the classifier
        was never shown."""
        planner = _planner()
        for query in (
            "How would you describe my values?",
            "Tell me about my weaknesses",
            "What defines my character?",
            "Give me an honest read on my character",
            "What would you say my blind spots are?",
        ):
            got = planner.classify(query).intent_type.value
            assert got == "identity_question", f"{query!r} -> {got}"

    def test_it_did_not_swallow_genuine_information_requests(self):
        """The risk of widening identity is that it eats questions about the
        system rather than about the person."""
        planner = _planner()
        for query in (
            "What does the confidence score actually mean?",
            "How is a behaviour object put together?",
        ):
            got = planner.classify(query).intent_type.value
            assert got != "identity_question", f"{query!r} -> {got}"
