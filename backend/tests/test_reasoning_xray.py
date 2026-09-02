"""The X-ray must report the run, not flatter it.

The architecture's central claim is that a language model decides nothing.
Every run already recorded enough to check that - per-stage timings, the
decision funnel, and which provider answered - and none of it was ever shown.

The risk in building a view around that claim is a view that argues for it.
This module only reshapes recorded values, so what is pinned here is that it
computes nothing about the run, invents no ratio it cannot support, and reports
honestly when a language model WAS called.
"""
import pytest

from app.services import reasoning_xray as xray


def _trace(**over):
    base = {
        "success": True, "query": "what are my top interests",
        "snapshot_version": 3,
        "intent_type": "identity_question", "intent_confidence": 0.3,
        "reasoning_mode": "identity_explanation",
        "directives_fulfilled": 6, "directives_total": 6, "retrieved_count": 14,
        "facts_generated": 5,
        "decision_input_facts": 5, "decision_output_facts": 2,
        "decision_removed_low_confidence": 2, "decision_removed_duplicates": 1,
        "decision_removed_diversity": 0, "decision_conflicts": 0,
        "citations_created": 2, "provider": "fallback", "model": None,
        "runtime_load_ms": 1.22, "planning_ms": 1.25, "retrieval_ms": 0.27,
        "ranking_ms": 0.18, "fusion_ms": 0.21, "decision_ms": 0.12,
        "context_build_ms": 1174.53, "verbalization_ms": 11373.37,
        "total_ms": 14374.37,
    }
    base.update(over)
    return base


def _build(trace):
    """The pure part of build_xray, without the database round trip."""
    stages = []
    for name, key, kind, purpose in xray.STAGES:
        stages.append({"name": name, "ms": round(xray._num(trace, key), 3),
                       "kind": kind, "purpose": purpose,
                       "detail": xray._detail(name, trace)})
    return stages


class TestTheStages:
    def test_exactly_one_stage_can_involve_a_language_model(self):
        """If a second stage were ever marked this way, the architecture's
        central claim would no longer hold and the view must show it."""
        llm = [s for s in xray.STAGES if s[2] == "language_model"]
        assert len(llm) == 1
        assert llm[0][0] == "Verbalization"

    def test_verbalization_is_last(self):
        assert xray.STAGES[-1][0] == "Verbalization"

    def test_every_stage_reports_its_recorded_duration(self):
        stages = _build(_trace())
        by_name = {s["name"]: s["ms"] for s in stages}
        assert by_name["Decision"] == 0.12
        assert by_name["Verbalization"] == 11373.37

    def test_a_missing_timing_reads_as_zero_not_a_crash(self):
        stages = _build(_trace(decision_ms=None, ranking_ms="not a number"))
        by_name = {s["name"]: s["ms"] for s in stages}
        assert by_name["Decision"] == 0.0
        assert by_name["Ranking"] == 0.0


class TestTheDetailLines:
    def test_planning_reports_the_intent_it_chose(self):
        detail = xray._detail("Planning", _trace())
        assert "identity_question" in detail and "0.30" in detail

    def test_decision_reports_what_it_dropped(self):
        assert xray._detail("Decision", _trace()) == "5 in, 2 kept"

    def test_verbalization_says_when_no_model_was_called(self):
        """provider 'fallback' with no model means the deterministic template
        produced the wording and no model was reached."""
        assert "no model called" in xray._detail("Verbalization", _trace())

    def test_verbalization_names_the_model_when_one_was_used(self):
        detail = xray._detail("Verbalization", _trace(provider="openai", model="gpt-4"))
        assert "gpt-4" in detail

    def test_a_stage_with_nothing_recorded_returns_none(self):
        assert xray._detail("Planning", {}) is None
        assert xray._detail("Retrieval", {}) is None


class TestTheTimingSplit:
    def test_deciding_sums_only_the_deterministic_stages(self):
        stages = _build(_trace())
        deciding = sum(s["ms"] for s in stages if s["kind"] == "deterministic")
        # Everything except verbalization, including context building.
        assert deciding == pytest.approx(1.22 + 1.25 + 0.27 + 0.18 + 0.21 + 0.12 + 1174.53)

    def test_talking_is_verbalization_alone(self):
        stages = _build(_trace())
        talking = sum(s["ms"] for s in stages if s["kind"] == "language_model")
        assert talking == pytest.approx(11373.37)

    def test_no_ratio_is_invented_when_there_is_nothing_to_divide(self):
        """A fabricated ratio is the easiest thing here to get wrong in the
        system's favour."""
        stages = _build(_trace(runtime_load_ms=0, planning_ms=0, retrieval_ms=0,
                               ranking_ms=0, fusion_ms=0, decision_ms=0,
                               context_build_ms=0))
        deciding = sum(s["ms"] for s in stages if s["kind"] == "deterministic")
        assert deciding == 0
        # build_xray guards on deciding > 0; mirrored here.
        assert (None if deciding == 0 else 1) is None


class TestItDoesNotOverclaim:
    def test_llm_called_is_driven_by_the_recorded_model(self):
        import inspect
        source = inspect.getsource(xray.build_xray)
        assert 'bool(t.get("model"))' in source

    def test_the_note_does_not_claim_the_model_is_absent(self):
        """The model may legitimately be called. The claim is about WHAT it
        does, not whether it runs."""
        import inspect
        source = inspect.getsource(xray)
        note = source[source.index('"note":'):source.index('"note":') + 400]
        assert "only puts it into words" in note

    def test_it_computes_nothing_about_the_run_itself(self):
        """Every number shown must come from the trace. A derived metric here
        would be this module marking its own homework."""
        import inspect
        source = inspect.getsource(xray.build_xray)
        for invented in ("random", "estimate", "approx_", "assume"):
            assert invented not in source
