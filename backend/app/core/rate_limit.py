"""Rate limiting for the endpoints that cost real money to serve.

The deployed service accepts UNAUTHENTICATED writes for any `demo_*` user_id —
that is deliberate (the Chrome extension and the signed-out demo both need it)
but it means /import/archive, /ingest and /query are open to anyone with curl.
CORS does not help: it constrains browsers, not clients.

Each of those requests spends money and storage that is not the caller's:
an import parses up to 50k events, embeds them through a paid API, and writes
them to a shared database. Without a limit, one loop is an unbounded bill.

Design notes
------------
* In-process token buckets, no new dependency and no Redis. The service runs
  as a single Render instance, so a shared store would be ceremony without
  benefit. The honest limitations: buckets reset on restart or redeploy, and
  a multi-instance deployment would allow N times the configured rate. Both
  are acceptable for stopping casual abuse and neither is a secret — if this
  ever runs multi-instance, this module is the thing to replace.
* Keyed by authenticated username when present, falling back to client IP.
  A user_id cannot be the key: it is attacker-supplied, so anyone could get a
  fresh bucket per request just by changing it.
* Fails OPEN. A bug in accounting must never take down ingestion; the worst
  case for a wrong "allow" is one extra request, and for a wrong "deny" it is
  a user who cannot use the product.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

# Off during tests: the suite drives these endpoints far harder than a person
# would, and a shared limiter would make test outcomes depend on run order.
def _enabled() -> bool:
    return os.getenv("RATE_LIMIT_ENABLED", "true").lower() not in ("false", "0", "no")


@dataclass
class Bucket:
    tokens: float
    updated_at: float


@dataclass
class TokenBucketLimiter:
    """Classic token bucket: `capacity` requests, refilled over `per_seconds`.

    Bursts up to capacity are allowed on purpose — the Chrome extension posts
    several batches in quick succession when a user scrolls, and a strict
    per-second cap would break normal use while barely slowing an attacker.
    """

    capacity: int
    per_seconds: float
    name: str = "default"
    _buckets: Dict[str, Bucket] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def _rate(self) -> float:
        return self.capacity / self.per_seconds

    def check(self, key: str) -> Tuple[bool, float]:
        """(allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                self._buckets[key] = Bucket(tokens=self.capacity - 1, updated_at=now)
                return True, 0.0

            elapsed = now - bucket.updated_at
            bucket.tokens = min(self.capacity, bucket.tokens + elapsed * self._rate)
            bucket.updated_at = now

            if bucket.tokens >= 1:
                bucket.tokens -= 1
                return True, 0.0

            # Seconds until one whole token is available again.
            return False, max(1.0, (1 - bucket.tokens) / self._rate)

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


def client_key(request: Request) -> str:
    """Identify the caller.

    Prefers the authenticated username: it is verified, and it keeps users
    behind one NAT or corporate proxy from sharing a bucket.

    For anonymous callers, the client IP must come from X-Forwarded-For.
    Render terminates TLS at a proxy, so `request.client.host` is the proxy's
    address for EVERY request — keying on it would put the entire internet in
    a single bucket and rate-limit all users the moment one of them was busy.
    """
    auth = request.headers.get("authorization") or ""
    if auth.startswith("Bearer "):
        try:
            from app.services import auth as auth_service

            username = auth_service.verify_token(auth[7:])
            if username:
                return f"user:{username}"
        except Exception:
            pass

    forwarded = request.headers.get("x-forwarded-for") or ""
    if forwarded:
        # Left-most entry is the original client; the rest are proxies.
        return f"ip:{forwarded.split(',')[0].strip()}"

    client = request.client
    return f"ip:{client.host if client else 'unknown'}"


class RateLimit:
    """FastAPI dependency. Usage:

        @router.post("/import/archive", dependencies=[Depends(IMPORT_LIMIT)])
    """

    def __init__(self, limiter: TokenBucketLimiter):
        self.limiter = limiter

    async def __call__(self, request: Request) -> None:
        if not _enabled():
            return
        try:
            allowed, retry_after = self.limiter.check(client_key(request))
        except Exception as e:
            # Fail open — see the module docstring.
            logger.warning("Rate limiter error (allowing request): %s", e)
            return

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Too many requests. This endpoint allows "
                    f"{self.limiter.capacity} per "
                    f"{int(self.limiter.per_seconds / 60) or 1} minute(s)."
                ),
                headers={"Retry-After": str(int(retry_after))},
            )


# Limits are set by what the work COSTS, not by uniform policy.
#
# An import is the most expensive request in the system — it can parse 50k
# events, embed all of them through a paid API and write them to a shared
# database — and a human does it a handful of times ever.
IMPORT_LIMITER = TokenBucketLimiter(capacity=6, per_seconds=3600, name="import")

# The extension posts batches while a user scrolls, so this has to tolerate
# real bursts; it is here to stop a loop, not to pace normal use.
INGEST_LIMITER = TokenBucketLimiter(capacity=120, per_seconds=60, name="ingest")

# A query runs the full seven-stage pipeline and may call a language model.
QUERY_LIMITER = TokenBucketLimiter(capacity=30, per_seconds=60, name="query")

# Seeding fabricates a whole dataset and runs it through the pipeline.
SEED_LIMITER = TokenBucketLimiter(capacity=5, per_seconds=3600, name="seed")

# RL feedback is cheap to serve but writes to the ONE policy table shared by
# every user, so the cost of abuse is not compute — it is the model everyone
# gets. Authentication already keeps anonymous callers from applying anything;
# this bounds how fast a signed-in account can push the shared Q-values, and
# how fast anyone can spend database round-trips finding that out.
FEEDBACK_LIMITER = TokenBucketLimiter(capacity=60, per_seconds=3600, name="feedback")

import_rate_limit = RateLimit(IMPORT_LIMITER)
ingest_rate_limit = RateLimit(INGEST_LIMITER)
query_rate_limit = RateLimit(QUERY_LIMITER)
seed_rate_limit = RateLimit(SEED_LIMITER)
feedback_rate_limit = RateLimit(FEEDBACK_LIMITER)
