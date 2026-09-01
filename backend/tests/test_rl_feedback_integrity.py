"""The shared bandit policy must not be steerable by anonymous callers.

rl_policy is keyed on (context_key, action_id) with NO user_id — one table
shared by every user, deciding which nudge each of them is shown. /rl/feedback
writes to it, and originally did so with no authentication, no rate limit and
an unvalidated context_key taken straight from the request body.

That combination was worse than it looks, because of the update rule:

    Q += max(ALPHA_MIN, 1/n) * (reward - Q)

The ALPHA_MIN floor exists so late feedback still matters. It also means
repeated posts converge on whatever value the caller picks, rather than being
averaged away — the arithmetic is pinned in test_the_floor_is_what_made_it_cheap
below, because that is the part that turns "an unauthenticated write" into
"total control of a shared model for the price of 60 requests".

These tests are pure arithmetic and route inspection; no database.
"""
import pytest

from app.services import rl_layer


class TestContextKeysAreAClosedSet:
    """Unvalidated context_key meant every distinct string inserted a row into
    a shared table, with no upper bound."""

    def test_the_valid_set_matches_what_the_code_can_produce(self):
        """Derived from ALIGNMENT_DIMENSIONS, so the two cannot drift apart."""
        produced = {
            rl_layer.context_key({"dimensions": {d: 0.1}})
            for d in rl_layer.ALIGNMENT_DIMENSIONS
        }
        produced.add(rl_layer.context_key({"dimensions": {}}))
        assert produced == set(rl_layer.VALID_CONTEXT_KEYS)

    def test_it_is_small_and_finite(self):
        assert 0 < len(rl_layer.VALID_CONTEXT_KEYS) < 20

    @pytest.mark.parametrize("junk", [
        "", "weak_", "weak_nonexistent", "../../etc/passwd",
        "a" * 500, "weak_depth ", "WEAK_DEPTH", "'; DROP TABLE rl_policy;--",
    ])
    def test_junk_contexts_are_not_accepted(self, junk):
        assert junk not in rl_layer.VALID_CONTEXT_KEYS


class TestTheEndpointContract:
    def _route(self):
        from app.main import app
        return next(
            r for r in app.routes
            if getattr(r, "path", None) == "/rl/feedback" and "POST" in getattr(r, "methods", set())
        )

    def test_feedback_is_rate_limited(self):
        from app.core.rate_limit import RateLimit

        guards = [
            d.call for d in self._route().dependant.dependencies
            if isinstance(getattr(d, "call", None), RateLimit)
        ]
        assert guards, "/rl/feedback writes shared state with no rate limit"

    def test_it_reads_the_authorization_header(self):
        """Whether feedback is applied depends on the caller being signed in,
        so the handler has to actually look."""
        import inspect
        source = inspect.getsource(self._route().endpoint)
        assert "authorization" in source
        assert "verify_token" in source

    def test_reward_is_bounded_by_the_schema(self):
        """Out-of-range rewards are rejected rather than silently clamped, so
        a caller cannot push Q outside [0,1] or discover the clamp by probing."""
        from pydantic import ValidationError
        from app.api.rl import FeedbackRequest

        for bad in (-1.0, 1.5, 1e9, float("inf")):
            with pytest.raises(ValidationError):
                FeedbackRequest(context_key="weak_depth", action_id="reduce_session", reward=bad)

        ok = FeedbackRequest(context_key="weak_depth", action_id="reduce_session", reward=0.5)
        assert ok.reward == 0.5

    def test_anonymous_feedback_is_answered_honestly(self):
        """It returns 200 so the signed-out demo does not look broken — but it
        must say that nothing was learned, not imply success."""
        import inspect
        source = inspect.getsource(self._route().endpoint)
        assert '"applied": False' in source, (
            "the anonymous path must report applied=False rather than a bare success"
        )


class TestTheAttackArithmetic:
    """Why authentication was the necessary fix and not a nicety."""

    @staticmethod
    def _converge(q, target, n, alpha_min):
        for _ in range(n):
            q += max(alpha_min, 0.0) * (target - q)
        return q

    def test_the_floor_is_what_made_it_cheap(self):
        """With a learning-rate floor, repeated feedback converges on the
        caller's chosen value instead of being averaged into insignificance.
        ~60 posts get within 5% of any target; 200 pin it."""
        alpha = rl_layer.ALPHA_MIN
        assert alpha > 0, "no floor means this test is describing the wrong rule"

        start, target = 0.5, 0.0
        assert self._converge(start, target, 60, alpha) < 0.05
        assert self._converge(start, target, 200, alpha) < 0.001

    def test_a_true_running_mean_would_have_resisted_it(self):
        """Contrast: with alpha = 1/n and no floor, the same 60 posts barely
        move an established value. The floor is a deliberate trade — it buys
        adaptivity and costs tamper-resistance, which is why the endpoint
        needs an authentication gate rather than a different constant."""
        q, n = 0.5, 10_000
        for _ in range(60):
            n += 1
            q += (1.0 / n) * (0.0 - q)
        assert q > 0.49

    def test_fabricated_feedback_also_dilutes_real_feedback(self):
        """Every post increments n, and alpha shrinks as n grows, so spam
        permanently reduces how much a genuine rating can move the value."""
        def alpha_at(n):
            return max(rl_layer.ALPHA_MIN, 1.0 / (n + 1))

        assert alpha_at(0) > alpha_at(100), "n must actually damp the step size"
