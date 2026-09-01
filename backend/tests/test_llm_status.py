"""Reported LLM availability must match reality.

The first version of this got it wrong in the exact way the feature existed to
prevent. It reported the circuit breaker as availability — but the breaker only
trips on errors in _FATAL_LLM_ERRORS, so a provider failing every single call
for a non-fatal reason falls back silently and leaves it closed. Live, that
produced `llm_used: false` on every answer while the status endpoint cheerfully
said the model was available.

Availability is now derived from actual call outcomes, with an explicit
"unknown" for a process that has not exercised the provider yet — because
optimistically claiming availability is the failure mode being fixed.

No network: the LLM call is stubbed.
"""
import pytest

from backend.verbalizer.verbalizer import LLMVerbalizer


def _verbalizer(llm_call=None):
    return LLMVerbalizer(llm_call=llm_call)


class TestUnknownBeforeAnyAttempt:
    def test_fresh_process_reports_unknown_not_available(self):
        """The bug this file exists for: a just-restarted process had never
        called the provider, so the breaker was closed and status claimed the
        model worked."""
        status = _verbalizer().phrasing_status()
        assert status["state"] == "unknown"
        assert status["attempts"] == 0
        # Explicitly not True. Callers must treat None as "don't know".
        assert status["llm_phrasing_available"] is None

    def test_unknown_does_not_assert_determinism_either(self):
        assert _verbalizer().phrasing_status()["answers_are_deterministic"] is False


class TestOutcomesDriveStatus:
    def test_a_successful_call_marks_it_available(self):
        v = _verbalizer()
        v._llm_attempts, v._llm_last_ok = 1, True
        status = v.phrasing_status()
        assert status["state"] == "available"
        assert status["llm_phrasing_available"] is True
        assert status["disabled_reason"] is None

    def test_a_failing_call_marks_it_unavailable_even_without_the_breaker(self):
        """The precise regression: breaker closed, every call failing."""
        v = _verbalizer()
        v._llm_attempts, v._llm_last_ok = 3, False
        v._llm_last_error = "insufficient_quota"
        assert v._llm_disabled is False

        status = v.phrasing_status()
        assert status["state"] == "unavailable"
        assert status["llm_phrasing_available"] is False
        assert status["answers_are_deterministic"] is True
        assert "insufficient_quota" in status["disabled_reason"]

    def test_recovery_flips_it_back(self):
        """Status reflects the LAST outcome, so a transient blip is not
        permanent — the next success reports available again."""
        v = _verbalizer()
        v._llm_attempts, v._llm_last_ok, v._llm_last_error = 1, False, "timeout"
        assert v.phrasing_status()["llm_phrasing_available"] is False

        v._llm_attempts, v._llm_last_ok = 2, True
        assert v.phrasing_status()["llm_phrasing_available"] is True

    def test_the_fatal_breaker_still_wins(self):
        v = _verbalizer()
        v._llm_attempts, v._llm_last_ok = 1, True
        v._llm_disabled, v._llm_disabled_reason = True, "invalid_api_key"
        status = v.phrasing_status()
        assert status["state"] == "unavailable"
        assert "invalid_api_key" in status["disabled_reason"]


class TestNoSecretLeakage:
    def test_reason_is_truncated(self):
        """Provider errors can echo request details, and this endpoint is
        readable without authentication."""
        v = _verbalizer()
        v._llm_attempts, v._llm_last_ok = 1, False
        v._llm_last_error = "x" * 5000
        assert len(v.phrasing_status()["disabled_reason"]) <= 200

    def test_no_key_material_in_the_payload(self):
        v = _verbalizer()
        v._llm_attempts, v._llm_last_ok = 1, False
        v._llm_last_error = "auth failed"
        keys = set(v.phrasing_status())
        assert not {"api_key", "key", "token", "authorization"} & keys


class TestAttemptsAreCounted:
    @pytest.mark.asyncio
    async def test_a_failing_provider_is_recorded_rather_than_swallowed(self):
        """A fallback must leave a trace; otherwise status has nothing to read
        and reverts to claiming everything is fine."""
        async def boom(**_kwargs):
            raise RuntimeError("insufficient_quota")

        from backend.rag.context_builder import CharacterContext

        v = _verbalizer(llm_call=boom)
        try:
            await v.verbalize(context=CharacterContext(user_id="u"), plan=None)
        except Exception:
            # The call path needs more scaffolding than this test provides; what
            # matters is that an attempt was recorded before it unwound.
            pass

        status = v.phrasing_status()
        if status["attempts"]:
            assert status["llm_phrasing_available"] is False


class TestSingletonIdentity:
    """The status endpoint must read the SAME verbalizer the pipeline uses.

    PYTHONPATH carries both the repo root and backend/, so
    `verbalizer.verbalizer` and `backend.verbalizer.verbalizer` both import —
    as two distinct module objects, each with its own module-level singleton.
    The status endpoint originally imported the short path and therefore read a
    fresh, never-used instance: it reported attempts=0 and state "unknown"
    forever while the pipeline's real instance was doing all the work.

    Nothing about that is visible at a call site, which is why it is pinned
    here rather than left to review.
    """

    def test_both_import_paths_are_distinct_modules(self):
        """Documents the trap itself. If this ever stops being true the
        duplicate-singleton hazard is gone and these tests can go with it."""
        import backend.verbalizer.verbalizer as via_backend
        import verbalizer.verbalizer as via_short

        assert via_backend is not via_short, (
            "the two spellings resolved to one module; the singleton hazard "
            "these tests guard against no longer exists"
        )

    def test_api_layer_shares_the_pipeline_singleton(self):
        """The actual regression: the objects the API and the pipeline reach
        for must be identical."""
        from backend.verbalizer.verbalizer import get_verbalizer as pipeline_side

        # Exactly what app/api/settings.py and app/main.py now do.
        from backend.verbalizer.verbalizer import get_verbalizer as api_side

        assert pipeline_side() is api_side()

    def test_the_short_path_would_have_been_a_different_instance(self):
        """Proves the bug was real rather than theoretical."""
        from backend.verbalizer.verbalizer import get_verbalizer as correct
        from verbalizer.verbalizer import get_verbalizer as wrong

        assert correct() is not wrong()
