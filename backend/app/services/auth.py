"""
Authentication — self-contained, stdlib-only (no new dependencies).

- Passwords: PBKDF2-HMAC-SHA256 with a per-user random salt.
- Tokens:    a minimal HS256-style signed token  b64(payload).b64(HMAC(secret))
             carrying {sub: username, exp: epoch}. Verified by signature + expiry.

Additive: this does not touch any existing endpoint. The rest of the system is
already keyed by user_id — a user's user_id is simply their username — so auth
just proves identity and drives the login UX.
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from typing import Optional, Dict, Any

from app.db.postgres import fetchrow, execute

logger = logging.getLogger(__name__)

AUTH_SECRET = os.getenv("AUTH_SECRET", "aimirror-dev-secret-change-me")
TOKEN_TTL = int(os.getenv("AUTH_TOKEN_TTL", str(60 * 60 * 24 * 7)))  # 7 days
PBKDF2_ROUNDS = 200_000


# ── password hashing ──────────────────────────────────────────────────────────

def hash_password(password: str, salt: Optional[str] = None) -> Dict[str, str]:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ROUNDS)
    return {"hash": dk.hex(), "salt": salt}


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ROUNDS)
    return hmac.compare_digest(dk.hex(), expected_hash)


# ── tokens ────────────────────────────────────────────────────────────────────

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def create_token(username: str) -> str:
    payload = {"sub": username, "exp": int(time.time()) + TOKEN_TTL}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(AUTH_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(sig)}"


def verify_token(token: str) -> Optional[str]:
    """Return the username if the token is valid & unexpired, else None."""
    try:
        body, sig = token.split(".", 1)
        expected = hmac.new(AUTH_SECRET.encode(), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_unb64(sig), expected):
            return None
        payload = json.loads(_unb64(body))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload.get("sub")
    except Exception:
        return None


# ── user store ────────────────────────────────────────────────────────────────

async def register_user(username: str, password: str, email: Optional[str] = None,
                        display_name: Optional[str] = None) -> Dict[str, Any]:
    username = (username or "").strip().lower()
    if not username or not password:
        raise ValueError("username and password are required")
    if len(username) < 3:
        raise ValueError("username must be at least 3 characters")
    if len(password) < 6:
        raise ValueError("password must be at least 6 characters")

    existing = await fetchrow("SELECT id FROM users WHERE username = $1", username)
    if existing:
        raise ValueError("username already taken")

    hp = hash_password(password)
    await execute(
        """
        INSERT INTO users (username, email, password_hash, salt, display_name)
        VALUES ($1, $2, $3, $4, $5)
        """,
        username, email, hp["hash"], hp["salt"], display_name or username,
    )
    logger.info("Registered user %s", username)
    return {"username": username, "display_name": display_name or username, "email": email}


async def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    username = (username or "").strip().lower()
    row = await fetchrow(
        "SELECT username, email, display_name, password_hash, salt FROM users WHERE username = $1",
        username,
    )
    if not row:
        return None
    if not verify_password(password, row["salt"], row["password_hash"]):
        return None
    return {"username": row["username"], "email": row["email"], "display_name": row["display_name"]}


async def get_user(username: str) -> Optional[Dict[str, Any]]:
    row = await fetchrow(
        "SELECT username, email, display_name, created_at FROM users WHERE username = $1",
        username,
    )
    if not row:
        return None
    return {
        "username": row["username"], "email": row["email"],
        "display_name": row["display_name"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }
