"""
Data privacy — export and delete every row this platform holds for a given
user_id. This is the compliance floor for handling behavioral data
commercially: anyone whose data this system models must be able to get a
full copy of it and have it permanently removed, not just deactivate a
login. Erasing the behavioural tables and erasing the ACCOUNT are separate
operations, because they answer different requests: "forget what you
learned about me" and "delete me". delete_all_user_data does the first;
delete_account does the second, and the caller chooses.

What matters is that the difference is never hidden. The `users` row is not
just a login — it also carries the email, the display name, the pbkdf2
password hash, and the user's own encrypted LLM API key (see
services/user_llm_config.py, which stores it in columns on `users`). A flow
that says it deleted "everything" while leaving a third-party API key behind
would be exactly the kind of claim this product exists to check, so
account_retention_note() below states plainly what survives, and the API
returns it on every deletion.
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from app.db.postgres import fetch, execute

logger = logging.getLogger(__name__)

# Every table keyed by user_id, in FK-safe delete order (children before
# parents where a relationship exists — most of these are independent, but
# self_models/identity_snapshots logically follow identities).
#
# ANY new table keyed by user_id must be added here. Export and erasure both
# iterate this list, so a table omitted from it is silently exempt from both —
# a right-to-erasure request would report success while leaving the rows in
# place. platform_profile_claims was added late and did exactly that.
USER_DATA_TABLES: List[str] = [
    "events", "embeddings", "actions_log", "personas",
    "behavior_objects", "evidence", "inferences", "reflections", "goals",
    "memories", "chat_messages", "pipeline_traces", "cognitive_metrics",
    "runtime_metrics", "guardian_alerts", "platform_profile_claims",
    "search_signals",
    # Operational telemetry, but it carries user_id plus the request path and
    # message that produced it, which makes it personal data. Losing some
    # diagnostics is the correct trade when someone asks to be erased.
    "error_events",
    "self_models", "identity_snapshots", "identities",
]


def _row_to_jsonable(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


async def export_all_user_data(user_id: str) -> Dict[str, Any]:
    """Every row across every user-owned table, as one downloadable bundle."""
    bundle: Dict[str, Any] = {
        "user_id": user_id,
        "exported_at": datetime.utcnow().isoformat(),
        "tables": {},
    }
    total_rows = 0
    for table in USER_DATA_TABLES:
        try:
            rows = await fetch(f"SELECT * FROM {table} WHERE user_id = $1", user_id)
            bundle["tables"][table] = [_row_to_jsonable(dict(r)) for r in rows]
            total_rows += len(rows)
        except Exception as e:
            logger.warning(f"Export: could not read {table} for {user_id}: {e}")
            bundle["tables"][table] = []
    bundle["total_rows"] = total_rows
    return bundle


async def delete_all_user_data(user_id: str) -> Dict[str, int]:
    """Permanently delete every row across every user-owned table. Returns
    the per-table row count actually deleted, so the caller (and the user)
    can verify exactly what was removed."""
    deleted: Dict[str, int] = {}
    for table in USER_DATA_TABLES:
        try:
            result = await execute(f"DELETE FROM {table} WHERE user_id = $1", user_id)
            # asyncpg execute() returns a string like "DELETE 12"
            count = int(result.split()[-1]) if result and result.split()[-1].isdigit() else 0
            deleted[table] = count
        except Exception as e:
            logger.error(f"Delete: failed on {table} for {user_id}: {e}")
            deleted[table] = -1
    return deleted


# Columns on the `users` row. Not behavioural data, but personal data and
# credentials all the same — including the user's own encrypted LLM API key.
ACCOUNT_FIELDS = [
    "email", "display_name", "password_hash", "salt",
    "llm_provider", "llm_api_key_encrypted", "llm_base_url", "llm_model",
]


async def account_retention_note(user_id: str) -> Dict[str, Any]:
    """What still exists after delete_all_user_data.

    Returned to the user on every deletion so the promise made by the UI and
    the rows actually removed cannot drift apart.
    """
    row = await fetch("SELECT * FROM users WHERE username = $1", user_id)
    if not row:
        return {"account_exists": False, "retained": []}

    record = dict(row[0])
    retained = [f for f in ACCOUNT_FIELDS if record.get(f) not in (None, "")]
    return {
        "account_exists": True,
        # Field names only — never the values.
        "retained": retained,
        "note": (
            "Your behavioural data is gone. Your account row still holds "
            + ", ".join(retained)
            + ". Delete the account itself to remove those."
        ) if retained else "Your behavioural data is gone. The account row remains.",
    }


async def delete_account(user_id: str) -> Dict[str, Any]:
    """Delete the account row itself: login, email, display name, password
    hash and stored LLM key.

    Refuses while the user still owns an organization. organizations.
    owner_username is a foreign key into users, so the delete would fail
    anyway — but more importantly, silently removing an org would take other
    members' workspace with it. That has to be a deliberate, separate act.
    """
    owned = await fetch(
        "SELECT name, slug FROM organizations WHERE owner_username = $1", user_id
    )
    if owned:
        return {
            "deleted": False,
            "reason": "owns_organization",
            "organizations": [dict(r) for r in owned],
            "note": (
                "This account owns an organization. Transfer or delete it "
                "first — removing the account would take the whole workspace "
                "with it."
            ),
        }

    result = await execute("DELETE FROM users WHERE username = $1", user_id)
    count = int(result.split()[-1]) if result and result.split()[-1].isdigit() else 0
    if count:
        logger.info("Account deleted: %s", user_id)
    return {"deleted": bool(count), "rows": count}
