"""What someone is still doing, and what they have moved on from.

The lifecycle is one of the architecture's stated contributions and it had
never worked. Every one of 226 behaviour objects on the deployed instance was
growing or emerging; stable, declining, dormant and archived had not once
occurred. State was written only when a topic turned up in an ingest batch, and
a topic somebody has abandoned never turns up again, so the code that would
have retired it could not run. Ninety-six behaviours unseen for more than a
month were still growing, the oldest last seen 600 days earlier.

With state evaluated as of now (see reasoning/lifecycle.py), the interesting
half of a watch history becomes visible for the first time: not what someone is
into, which every recommender already claims to know, but what they have
drifted out of. That is the half a feed has no commercial reason to tell them.

Each entry carries the reason for its label, because "you have moved on from
this" is a claim about someone's life and should not be made without saying on
what basis.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.db.postgres import fetch
from reasoning.lifecycle import evaluate_lifecycle

logger = logging.getLogger(__name__)

CURRENT_STATES = ("emerging", "growing", "stable")
FADING_STATES = ("declining",)
PAST_STATES = ("dormant", "archived")

MAX_PER_GROUP = 30


def _decode(value: Any) -> Dict[str, Any]:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return {}
    return value or {}


def _is_creator(topic: str) -> bool:
    """Creator affinities are not subjects, and belong to the creator graph."""
    return str(topic or "").startswith("Content by ")


async def build_lifecycle_view(user_id: str) -> Dict[str, Any]:
    """Behaviours grouped by where they are in their life."""
    rows = await fetch(
        """
        SELECT topic, lifecycle_state, temporal_statistics, trend_information,
               importance_score, creators
        FROM behavior_objects WHERE user_id = $1
        """,
        user_id,
    )

    if not rows:
        return {
            "user_id": user_id,
            "measurable": False,
            "note": (
                "No behaviours have been consolidated for this account yet, so "
                "there is nothing to say about what is current and what is not."
            ),
        }

    now = datetime.now(timezone.utc)
    groups: Dict[str, List[Dict[str, Any]]] = {"current": [], "fading": [], "past": []}
    counts: Dict[str, int] = {}

    for row in rows:
        if _is_creator(row["topic"]):
            continue

        temporal = _decode(row["temporal_statistics"])
        trend = _decode(row["trend_information"])

        # Evaluated here as well as at ingest. A stored state is only as fresh
        # as the last ingest, and someone who stopped using the product
        # entirely is exactly the person whose behaviours have gone dormant.
        state, reason = evaluate_lifecycle(temporal, trend, now)
        counts[state] = counts.get(state, 0) + 1

        entry = {
            "topic": row["topic"],
            "state": state,
            "occurrences": reason.get("occurrences"),
            "days_since_last_seen": reason.get("days_since_last_seen"),
            "age_days": reason.get("age_days"),
            "recent_share": reason.get("recent_share"),
            "basis": reason.get("basis"),
            "importance": round(float(row["importance_score"] or 0.0), 3),
        }

        if state in FADING_STATES:
            groups["fading"].append(entry)
        elif state in PAST_STATES:
            groups["past"].append(entry)
        else:
            groups["current"].append(entry)

    # Most recently active first among current; longest gone first among past,
    # because the striking thing about an abandoned interest is how long ago it
    # was, not how big it once looked.
    groups["current"].sort(key=lambda e: (-(e["importance"] or 0)))
    groups["fading"].sort(key=lambda e: (e["recent_share"] if e["recent_share"] is not None else 1.0))
    groups["past"].sort(key=lambda e: -(e["days_since_last_seen"] or 0))

    for key in groups:
        groups[key] = groups[key][:MAX_PER_GROUP]

    total = sum(counts.values())
    past_n = sum(counts.get(s, 0) for s in PAST_STATES)

    if not total:
        note = (
            "Every behaviour recorded for this account is a creator affinity "
            "rather than a subject, so there is no topic lifecycle to show."
        )
    elif past_n:
        note = (
            f"{past_n} of {total} subjects have gone quiet. A behaviour is "
            f"counted as past when the silence since it was last seen is long "
            f"against the rhythm it used to keep, not against a fixed number of "
            f"days: a topic that recurred daily and one that recurred monthly "
            f"are not equally absent after a fortnight."
        )
    else:
        note = (
            f"All {total} subjects are still current. Nothing has been silent "
            f"long enough, relative to how often it used to appear, to count as "
            f"set aside."
        )

    return {
        "user_id": user_id,
        "measurable": True,
        "counts": counts,
        "total": total,
        "current": groups["current"],
        "fading": groups["fading"],
        "past": groups["past"],
        "note": note,
    }
