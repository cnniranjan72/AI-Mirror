"""
Research export — the opt-in, de-identified bulk dataset for behavioral-
science research. Built the same way app/services/insights_export.py builds
a single user's CSV: allowlisted columns only, read-only, no fields that
weren't already surfaced elsewhere in the product.

De-identification: a participant's row is keyed by an HMAC-SHA256 of their
username under a dedicated secret (RESEARCH_EXPORT_SALT, distinct from
AUTH_SECRET so the two can be rotated independently) — one-way, stable
across exports for the same user (so a longitudinal study can still join
records for one participant across export runs), and never reversible back
to a username from the export alone.

Participation is opt-in only (users.research_opt_in, default FALSE) — a
user's data is invisible here until they explicitly turn it on in Settings,
and turning it off removes them from every future export (past exports
already downloaded by a researcher can't be recalled — documented in the
Settings UI copy, not just here).
"""
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

from app.db.postgres import fetch, execute

logger = logging.getLogger(__name__)

RESEARCH_EXPORT_SALT = os.getenv("RESEARCH_EXPORT_SALT", "aimirror-dev-research-salt-change-me")
SCHEMA_VERSION = "1.0"

# Mirrors insights_export.export_table_csv's allowlist — no free-text
# captions or raw content, no creator-identifying fields beyond what's
# already a public creator handle, nothing that wasn't already exportable
# per-user.
_TABLE_QUERIES = {
    "behavior_objects": (
        "SELECT topic, lifecycle_state, confidence_score, importance_score, "
        "stability_score, keywords, updated_at FROM behavior_objects WHERE user_id = $1"
    ),
    "evidence": (
        "SELECT evidence_type, confidence, weight, created_at FROM evidence WHERE user_id = $1"
    ),
    "inferences": (
        "SELECT inference_type, label, confidence, created_at FROM inferences WHERE user_id = $1"
    ),
    "identity_snapshots": (
        "SELECT identity_version, overall_confidence, identity_completeness, created_at "
        "FROM identity_snapshots WHERE user_id = $1 ORDER BY created_at"
    ),
}


def participant_id(username: str) -> str:
    digest = hmac.new(RESEARCH_EXPORT_SALT.encode(), username.encode(), hashlib.sha256).hexdigest()
    return f"p_{digest[:16]}"


def _jsonable(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


async def set_opt_in(username: str, opt_in: bool) -> None:
    await execute("UPDATE users SET research_opt_in = $1 WHERE username = $2", opt_in, username)


async def get_opt_in(username: str) -> bool:
    rows = await fetch("SELECT research_opt_in FROM users WHERE username = $1", username)
    return bool(rows[0]["research_opt_in"]) if rows else False


async def build_export() -> Dict[str, Any]:
    opted_in = await fetch("SELECT username FROM users WHERE research_opt_in = TRUE")
    participants: List[Dict[str, Any]] = []

    for row in opted_in:
        username = row["username"]
        pid = participant_id(username)
        record: Dict[str, Any] = {"participant_id": pid}
        for table, query in _TABLE_QUERIES.items():
            table_rows = await fetch(query, username)
            cleaned = []
            for r in table_rows:
                d = _jsonable(dict(r))
                for k, v in d.items():
                    if isinstance(v, (list, dict)):
                        d[k] = v
                    elif isinstance(v, str) and v.startswith(("[", "{")):
                        try:
                            d[k] = json.loads(v)
                        except Exception:
                            pass
                cleaned.append(d)
            record[table] = cleaned
        participants.append(record)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.utcnow().isoformat(),
        "participant_count": len(participants),
        "deidentification": (
            "participant_id = HMAC-SHA256(RESEARCH_EXPORT_SALT, username)[:16], "
            "one-way and non-reversible from this export alone"
        ),
        "participants": participants,
    }
