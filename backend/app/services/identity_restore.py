"""Going back to a version of the model you recognise.

The architecture has claimed rollback since the first paper draft: snapshots are
immutable and versioned, and one "can be rolled back if later evidence
invalidates the drift". The method exists,
`IdentityEvolutionEngine.rollback_to_snapshot`. It logs "Rolled back to snapshot
X", returns None, and carries the comment "Placeholder - would return
reconstructed identity". Nothing has ever called it. Across 35 stored snapshots
`is_active` was TRUE on every one, so the column and its partial index had never
superseded anything.

Restoring by writing the snapshot back over the identities row would not work,
and shipping it would have been worse than shipping nothing. Identity
construction runs from scratch on every ingest - `existing_identity` supplies
only the identifier and the version counter, and all nine sub-profiles are
recomputed from the behaviour objects. A restored row survives exactly until the
next event arrives, so the control would appear to work and then quietly undo
itself, which is the failure mode a person is least able to detect.

What does hold is choosing which snapshot is the active one. Invariant 2 of the
architecture is that user-facing reads come from frozen snapshots rather than
from the live identity, so the pin is not a workaround: it is the same mechanism
the architecture already depends on, pointed somewhere the person chose.

Three properties this has to keep.

Nothing is destroyed. The live identity keeps evolving underneath and every
snapshot stays where it was; unpinning returns to the newest.

The pin cannot be pruned away. cleanup_old_snapshots keeps the twenty most
recent and would happily delete the one someone is standing on.

A dangling pin fails loudly rather than silently. If the snapshot is gone the
reader falls back to the latest and says that it did, because a rollback that
silently stops applying is the same lie as one that never applied.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.db.postgres import execute, fetch, fetchrow

logger = logging.getLogger(__name__)

MAX_RESTORE_POINTS = 25

# Reasons are the person's own words, shown back to them later.
MAX_REASON_LENGTH = 280


def _decode(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return None
    return value


async def get_pin(user_id: str) -> Optional[Dict[str, Any]]:
    row = await fetchrow(
        "SELECT snapshot_id, pinned_at, reason FROM identity_pins WHERE user_id = $1",
        user_id,
    )
    if not row:
        return None
    return {
        "snapshot_id": row["snapshot_id"],
        "pinned_at": row["pinned_at"].isoformat() if row["pinned_at"] else None,
        "reason": row["reason"],
    }


async def active_snapshot(user_id: str) -> Optional[Dict[str, Any]]:
    """The snapshot user-facing reads should use.

    The pinned one when there is a pin and it still exists, otherwise the most
    recent. The result says which of those happened, so a caller never has to
    guess whether a pin was honoured.
    """
    pin = await get_pin(user_id)

    if pin:
        row = await fetchrow(
            "SELECT * FROM identity_snapshots WHERE snapshot_id = $1 AND user_id = $2",
            pin["snapshot_id"], user_id,
        )
        if row:
            result = dict(row)
            result["_pinned"] = True
            result["_pin_reason"] = pin["reason"]
            return result

        # The pin outlived its snapshot. Report it rather than quietly serving
        # something else: a restore that stops applying without saying so is
        # indistinguishable, from the outside, from one that never worked.
        logger.warning("Pinned snapshot %s missing for %s; falling back to latest",
                       pin["snapshot_id"], user_id)
        row = await fetchrow(
            "SELECT * FROM identity_snapshots WHERE user_id = $1 "
            "ORDER BY snapshot_timestamp DESC LIMIT 1", user_id)
        if not row:
            return None
        result = dict(row)
        result["_pinned"] = False
        result["_pin_broken"] = pin["snapshot_id"]
        return result

    row = await fetchrow(
        "SELECT * FROM identity_snapshots WHERE user_id = $1 "
        "ORDER BY snapshot_timestamp DESC LIMIT 1", user_id)
    if not row:
        return None
    result = dict(row)
    result["_pinned"] = False
    return result


async def list_restore_points(user_id: str, limit: int = MAX_RESTORE_POINTS) -> Dict[str, Any]:
    """Every snapshot this account could go back to, and what differs."""
    rows = await fetch(
        """
        SELECT snapshot_id, identity_version, snapshot_timestamp,
               overall_confidence, identity_completeness, dominant_topics
        FROM identity_snapshots WHERE user_id = $1
        ORDER BY snapshot_timestamp DESC LIMIT $2
        """,
        user_id, min(limit, MAX_RESTORE_POINTS),
    )

    if not rows:
        return {
            "user_id": user_id,
            "measurable": False,
            "points": [],
            "pinned": None,
            "note": (
                "No identity snapshots have been written for this account yet. "
                "One is taken whenever the model of you shifts far enough to be "
                "worth recording, so there is nothing to go back to."
            ),
        }

    pin = await get_pin(user_id)
    pinned_id = pin["snapshot_id"] if pin else None
    current_id = rows[0]["snapshot_id"]

    points: List[Dict[str, Any]] = []
    for row in rows:
        topics = _decode(row["dominant_topics"]) or []
        points.append({
            "snapshot_id": row["snapshot_id"],
            "version": row["identity_version"],
            "at": row["snapshot_timestamp"].isoformat() if row["snapshot_timestamp"] else None,
            "confidence": round(float(row["overall_confidence"] or 0.0), 3),
            "completeness": round(float(row["identity_completeness"] or 0.0), 3),
            "topics": topics if isinstance(topics, list) else [],
            "is_latest": row["snapshot_id"] == current_id,
            "is_pinned": row["snapshot_id"] == pinned_id,
        })

    # What each older point would change, against whatever is active now.
    active = next((p for p in points if p["is_pinned"]), None) or points[0]
    active_topics = set(active["topics"])
    for point in points:
        if point["snapshot_id"] == active["snapshot_id"]:
            point["changes"] = None
            continue
        theirs = set(point["topics"])
        point["changes"] = {
            "topics_gained": sorted(theirs - active_topics),
            "topics_lost": sorted(active_topics - theirs),
            "confidence_delta": round(point["confidence"] - active["confidence"], 3),
        }

    broken = bool(pin and pinned_id not in {p["snapshot_id"] for p in points})

    if broken:
        note = (
            f"This account is pinned to snapshot {pinned_id}, which is no longer "
            f"stored - only the twenty most recent are kept. Reads have fallen "
            f"back to the newest snapshot. Pin a different one, or unpin, to "
            f"clear this."
        )
    elif pinned_id:
        note = (
            "Reads are pinned to an earlier snapshot. Your history is untouched "
            "and the live model keeps updating underneath; unpinning returns to "
            "the newest."
        )
    else:
        note = (
            f"{len(points)} restore points. Pinning one changes what the system "
            f"shows and answers with, and nothing else: no events, behaviours or "
            f"snapshots are altered or removed."
        )

    return {
        "user_id": user_id,
        "measurable": True,
        "points": points,
        "pinned": pinned_id,
        "pin_reason": pin["reason"] if pin else None,
        "pin_broken": broken,
        "note": note,
    }


async def set_pin(user_id: str, snapshot_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """Pin reads to an earlier snapshot. Reversible, and destroys nothing."""
    row = await fetchrow(
        "SELECT snapshot_id, identity_version, snapshot_timestamp "
        "FROM identity_snapshots WHERE snapshot_id = $1 AND user_id = $2",
        snapshot_id, user_id,
    )
    if not row:
        # Checked against this user, so the endpoint cannot be used to discover
        # whether somebody else's snapshot id exists.
        return {"ok": False, "error": "No such snapshot for this account."}

    cleaned = (reason or "").strip()[:MAX_REASON_LENGTH] or None

    await execute(
        """
        INSERT INTO identity_pins (user_id, snapshot_id, reason)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id) DO UPDATE
        SET snapshot_id = EXCLUDED.snapshot_id,
            reason = EXCLUDED.reason,
            pinned_at = NOW(),
            updated_at = NOW()
        """,
        user_id, snapshot_id, cleaned,
    )

    logger.info("Identity pinned for %s to %s (v%s)",
                user_id, snapshot_id, row["identity_version"])

    return {
        "ok": True,
        "pinned": snapshot_id,
        "version": row["identity_version"],
        "at": row["snapshot_timestamp"].isoformat() if row["snapshot_timestamp"] else None,
        "reason": cleaned,
        "note": (
            "Reads now come from this snapshot. Nothing was deleted: your events, "
            "behaviours and every other snapshot are unchanged, and the live model "
            "carries on updating underneath. Unpin to return to the newest."
        ),
    }


async def clear_pin(user_id: str) -> Dict[str, Any]:
    result = await execute("DELETE FROM identity_pins WHERE user_id = $1", user_id)
    removed = "DELETE 1" in str(result)
    return {
        "ok": True,
        "was_pinned": removed,
        "note": (
            "Reads are back to the most recent snapshot."
            if removed else
            "This account was not pinned; nothing changed."
        ),
    }
