"""
Data privacy — export and delete every row this platform holds for a given
user_id. This is the compliance floor for handling behavioral data
commercially: anyone whose data this system models must be able to get a
full copy of it and have it permanently removed, not just deactivate a
login. Deliberately scoped to the cognitive/behavioral data tables (not the
`users` auth table) — account deletion/logout is a separate concern.
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
