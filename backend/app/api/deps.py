"""
Auth enforcement — optional-but-verified, demo-preserving.

The rest of the app takes user_id as a plain query/body parameter with no
relation to auth (see app/services/auth.py's own comment: "a user's user_id
is simply their username"). That's fine for a small set of public/demo
ids — it's how the app has always worked signed-out — but it means anyone
who knows a real user_id can read/write that user's data. This makes the
demo ids explicit and requires a *matching* bearer token for everything else:

- No token, public user_id (default/test_user_001/demo_*) -> allowed (today's
  signed-out demo behavior, unchanged).
- No token, real user_id -> 401.
- Valid token, user_id matches the token's username -> allowed.
- Valid token, user_id is a public id -> allowed (a signed-in user can still
  browse the demo data; client.js always attaches the token once signed in).
- Valid token, user_id is someone else's -> 403.
- Invalid/expired token -> 401, even against a public user_id (a broken
  token should never be silently treated the same as "no token").

`enforce_user_match`/`resolve_user_id` are for READS: the public-id bypass is
correct there (public data is meant to be browsable by anyone, signed in or
not). For anything that WRITES or DESTROYS data, that same bypass is wrong —
it would let any signed-in user mutate or delete a public id's data just
because it's public to read. `enforce_write_match` below is the same
contract minus that bypass: a valid token must match user_id EXACTLY, full
stop, even when user_id is public. (Discovered live: an early version of
this file used enforce_user_match for /admin/reprocess too, and a valid
token for an unrelated account was able to reprocess test_user_001 — wiping
its accumulated identity/reflection history. That's exactly the class of bug
this split exists to prevent.)
"""
from typing import Optional

from fastapi import Header, HTTPException, Query

from app.api.auth_api import _bearer
from app.services import auth

PUBLIC_USER_IDS = {"default", "test_user_001"}
PUBLIC_USER_PREFIXES = ("demo_",)


def _is_public_user(user_id: str) -> bool:
    return user_id in PUBLIC_USER_IDS or any(user_id.startswith(p) for p in PUBLIC_USER_PREFIXES)


def enforce_user_match(authorization: Optional[str], user_id: str) -> None:
    token = _bearer(authorization)
    if token:
        username = auth.verify_token(token)
        if not username:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if username != user_id and not _is_public_user(user_id):
            raise HTTPException(status_code=403, detail="Token does not authorize this user_id")
    elif not _is_public_user(user_id):
        raise HTTPException(status_code=401, detail="Authentication required for this user_id")


def enforce_write_match(authorization: Optional[str], user_id: str) -> None:
    """Stricter than enforce_user_match: no public-id bypass. A valid token
    must belong to exactly this user_id. No token at all is still allowed
    for a public user_id (the anonymous Chrome extension / seed flows write
    to test_user_001 with no login), but a token for someone ELSE never is,
    even when user_id is public."""
    token = _bearer(authorization)
    if token:
        username = auth.verify_token(token)
        if not username:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if username != user_id:
            raise HTTPException(status_code=403, detail="Token does not authorize writing to this user_id")
    elif not _is_public_user(user_id):
        raise HTTPException(status_code=401, detail="Authentication required for this user_id")


async def resolve_user_id(
    user_id: str = Query(default="default"),
    authorization: Optional[str] = Header(default=None),
) -> str:
    """FastAPI dependency: drop-in replacement for `user_id: str = Query(default="default")`."""
    enforce_user_match(authorization, user_id)
    return user_id
