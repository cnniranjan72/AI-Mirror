"""Rate limiting on the endpoints that cost money to serve.

The deployed service accepts unauthenticated writes for any `demo_*` user_id —
deliberately, since the extension and the signed-out demo both need it. That
leaves /import/archive, /ingest and /query open to anyone with curl, and each
of those spends paid embedding calls and shared database storage. Before this,
a single loop was an unbounded bill.

The suite disables the limiter globally (see conftest); these tests enable it
explicitly so the real behaviour is still covered.
"""
import os

import pytest

from app.core.rate_limit import TokenBucketLimiter, RateLimit, client_key


@pytest.fixture(autouse=True)
def limiter_enabled(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")


class _Request:
    """Minimal stand-in for starlette's Request."""

    def __init__(self, headers=None, host="1.2.3.4"):
        self.headers = headers or {}
        self.client = type("C", (), {"host": host})() if host else None


class TestTokenBucket:
    def test_allows_up_to_capacity(self):
        limiter = TokenBucketLimiter(capacity=3, per_seconds=60)
        assert [limiter.check("k")[0] for _ in range(3)] == [True, True, True]

    def test_denies_past_capacity(self):
        limiter = TokenBucketLimiter(capacity=2, per_seconds=60)
        limiter.check("k"); limiter.check("k")
        allowed, retry_after = limiter.check("k")
        assert allowed is False
        assert retry_after >= 1

    def test_keys_are_independent(self):
        """One abusive caller must not lock everyone else out."""
        limiter = TokenBucketLimiter(capacity=1, per_seconds=60)
        assert limiter.check("a")[0] is True
        assert limiter.check("a")[0] is False
        assert limiter.check("b")[0] is True

    def test_refills_over_time(self, monkeypatch):
        limiter = TokenBucketLimiter(capacity=2, per_seconds=2)  # 1/sec
        clock = {"t": 1000.0}
        monkeypatch.setattr("app.core.rate_limit.time.monotonic", lambda: clock["t"])

        limiter.check("k"); limiter.check("k")
        assert limiter.check("k")[0] is False

        clock["t"] += 1.1
        assert limiter.check("k")[0] is True

    def test_refill_is_capped_at_capacity(self, monkeypatch):
        """A long idle period must not bank unlimited requests."""
        limiter = TokenBucketLimiter(capacity=2, per_seconds=2)
        clock = {"t": 1000.0}
        monkeypatch.setattr("app.core.rate_limit.time.monotonic", lambda: clock["t"])

        limiter.check("k")
        clock["t"] += 10_000  # idle for hours
        assert [limiter.check("k")[0] for _ in range(3)] == [True, True, False]

    def test_bursts_are_allowed_on_purpose(self):
        """The extension posts several batches while a user scrolls; a strict
        per-second cap would break normal use and barely slow an attacker."""
        limiter = TokenBucketLimiter(capacity=120, per_seconds=60)
        assert all(limiter.check("k")[0] for _ in range(120))


class TestCallerIdentity:
    def test_prefers_the_forwarded_client_ip(self):
        """Render terminates TLS at a proxy, so request.client.host is the
        proxy for every request. Keying on it would put the whole internet in
        one bucket and rate-limit all users at once."""
        key = client_key(_Request({"x-forwarded-for": "9.9.9.9, 10.0.0.1"}, host="10.0.0.1"))
        assert key == "ip:9.9.9.9"

    def test_falls_back_to_the_socket_address(self):
        assert client_key(_Request(host="5.6.7.8")) == "ip:5.6.7.8"

    def test_handles_a_missing_client(self):
        assert client_key(_Request(host=None)) == "ip:unknown"

    def test_an_invalid_bearer_token_does_not_become_the_key(self):
        """A forged token must fall back to IP, not mint a private bucket."""
        key = client_key(_Request({
            "authorization": "Bearer not-a-real-token",
            "x-forwarded-for": "9.9.9.9",
        }))
        assert key == "ip:9.9.9.9"

    def test_user_id_is_never_the_key(self):
        """user_id is attacker-supplied: keying on it would hand out a fresh
        bucket per request just by changing a string."""
        import inspect
        from app.core import rate_limit
        assert "user_id" not in inspect.getsource(rate_limit.client_key)


class TestDependencyBehaviour:
    @pytest.mark.asyncio
    async def test_raises_429_with_retry_after(self):
        from fastapi import HTTPException

        guard = RateLimit(TokenBucketLimiter(capacity=1, per_seconds=60))
        request = _Request({"x-forwarded-for": "1.1.1.1"})

        await guard(request)  # first one is fine
        with pytest.raises(HTTPException) as exc:
            await guard(request)

        assert exc.value.status_code == 429
        assert "Retry-After" in exc.value.headers

    @pytest.mark.asyncio
    async def test_disabled_by_env(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
        guard = RateLimit(TokenBucketLimiter(capacity=1, per_seconds=60))
        request = _Request({"x-forwarded-for": "1.1.1.1"})
        for _ in range(5):
            await guard(request)  # must not raise

    @pytest.mark.asyncio
    async def test_fails_open_when_accounting_breaks(self):
        """A bug in the limiter must never take down ingestion. The cost of a
        wrong allow is one extra request; of a wrong deny, a broken product."""
        class Broken(TokenBucketLimiter):
            def check(self, key):
                raise RuntimeError("bucket exploded")

        guard = RateLimit(Broken(capacity=1, per_seconds=60))
        await guard(_Request({"x-forwarded-for": "1.1.1.1"}))  # must not raise


class TestExpensiveEndpointsAreCovered:
    """The point of the feature: the paid paths are actually guarded."""

    @pytest.mark.parametrize("path,method", [
        ("/import/archive", "POST"),
        ("/ingest", "POST"),
        ("/query", "POST"),
        ("/seed", "POST"),
    ])
    def test_route_declares_a_limiter(self, path, method):
        from app.main import app
        from app.core.rate_limit import RateLimit as Guard

        route = next(
            r for r in app.routes
            if getattr(r, "path", None) == path and method in getattr(r, "methods", set())
        )
        # FastAPI's Dependant exposes the callable as `.call`.
        guards = [
            d.call for d in route.dependant.dependencies
            if isinstance(getattr(d, "call", None), Guard)
        ]
        assert guards, f"{method} {path} has no rate limit"

    def test_import_is_the_strictest(self):
        """It is the most expensive request in the system: up to 50k events
        parsed, embedded through a paid API, and stored."""
        from app.core.rate_limit import IMPORT_LIMITER, INGEST_LIMITER, QUERY_LIMITER

        def per_hour(l):
            return l.capacity * 3600 / l.per_seconds

        assert per_hour(IMPORT_LIMITER) < per_hour(QUERY_LIMITER)
        assert per_hour(IMPORT_LIMITER) < per_hour(INGEST_LIMITER)
