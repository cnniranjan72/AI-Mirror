"""What the system's own evidence argues against.

Every claim this product makes rests on evidence, and every piece of evidence
now records the observations that contradict it as well as the ones that
support it. Those contradictions were computed, stored, indexed and read back
by four separate layers and never once shown to the person they were about.

This assembles them into the view that was missing: which claims the evidence
does not fully support, how far short it falls, and - the part that makes it
checkable rather than merely honest - the specific pieces of content behind the
disagreement. A claim that says "18 of 63 observations argue against this" and
can name all eighteen is one someone can actually dispute.

Ordering is by how contested a claim is, not by confidence. A confident claim
with a third of its evidence pointing the other way is more worth a reader's
attention than a tentative one nobody disputes, and every other surface in the
product already sorts by confidence.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.db.postgres import fetch

logger = logging.getLogger(__name__)

# Enough claims to see the shape of the disagreement without paging.
MAX_CLAIMS = 40

# Per claim. The count is always reported in full; this caps only how many are
# resolved to actual content, so the number a reader sees is never the
# truncated one.
MAX_EXAMPLES = 6


def _decode(value: Any) -> Any:
    """asyncpg hands back JSONB as text, no codec registered."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return None
    return value


def _subject(metadata: Any, explanation: str) -> str:
    meta = _decode(metadata) or {}
    if isinstance(meta, dict):
        for key in ("topic", "creator"):
            value = meta.get(key)
            if value and value != "unknown":
                return str(value)
    return (explanation or "").strip()[:60] or "this claim"


async def build_contested(user_id: str, limit: int = MAX_CLAIMS) -> Dict[str, Any]:
    """Claims whose own evidence records observations against them."""
    rows = await fetch(
        """
        SELECT evidence_id, evidence_type, explanation, confidence,
               net_confidence, conflict_resolution, metadata,
               supporting_events, conflicting_observations
        FROM evidence
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 400
        """,
        user_id,
    )

    claims: List[Dict[str, Any]] = []
    wanted_event_ids: set = set()

    total_support = 0
    total_counter = 0

    for row in rows:
        supporting = _decode(row["supporting_events"]) or []
        conflicting = _decode(row["conflicting_observations"]) or []
        if not isinstance(supporting, list) or not isinstance(conflicting, list):
            continue

        total_support += len(supporting)
        total_counter += len(conflicting)

        if not conflicting:
            continue

        observed = len(supporting) + len(conflicting)
        examples = []
        for raw in conflicting[:MAX_EXAMPLES]:
            try:
                examples.append(int(raw))
            except (TypeError, ValueError):
                continue
        wanted_event_ids.update(examples)

        claims.append({
            "evidence_id": row["evidence_id"],
            "kind": row["evidence_type"],
            "subject": _subject(row["metadata"], row["explanation"]),
            "explanation": row["explanation"],
            "confidence": round(float(row["confidence"] or 0.0), 3),
            "net_confidence": (
                round(float(row["net_confidence"]), 3)
                if row["net_confidence"] is not None else None
            ),
            "supported": len(supporting),
            "contradicted": len(conflicting),
            "observed": observed,
            "contradicted_share": round(len(conflicting) / observed, 3) if observed else 0.0,
            "note": row["conflict_resolution"],
            "_example_ids": examples,
        })

    # One query for every example across every claim rather than one per claim.
    events_by_id: Dict[int, Dict[str, Any]] = {}
    if wanted_event_ids:
        ids = sorted(wanted_event_ids)
        placeholders = ", ".join(f"${i + 2}" for i in range(len(ids)))
        event_rows = await fetch(
            f"""
            SELECT id, caption, username, watch_time, timestamp
            FROM events WHERE user_id = $1 AND id IN ({placeholders})
            """,
            user_id, *ids,
        )
        for event in event_rows:
            events_by_id[event["id"]] = {
                "caption": (event["caption"] or "").strip()[:120],
                "creator": event["username"],
                "watch_time": round(float(event["watch_time"] or 0.0), 1),
                "at": event["timestamp"].isoformat() if event["timestamp"] else None,
            }

    for claim in claims:
        claim["examples"] = [
            events_by_id[eid] for eid in claim.pop("_example_ids")
            if eid in events_by_id
        ]

    # Most contested first. Share rather than count, so a claim with four
    # observations against six does not sit below one with ten against three
    # hundred.
    claims.sort(key=lambda c: (c["contradicted_share"], c["contradicted"]), reverse=True)
    claims = claims[:limit]

    observations = total_support + total_counter
    if not rows:
        return {
            "user_id": user_id,
            "measurable": False,
            "claims": [],
            "note": (
                "No evidence has been collected for this account yet, so there "
                "is nothing for the system to disagree with itself about."
            ),
        }

    return {
        "user_id": user_id,
        "measurable": True,
        "claims": claims,
        "summary": {
            "claims_examined": len(rows),
            "claims_contested": len([c for c in claims if c["contradicted"]]),
            "observations": observations,
            "contradicting": total_counter,
            "contradicting_share": (
                round(total_counter / observations, 3) if observations else 0.0
            ),
        },
        "note": (
            f"{total_counter} of {observations} observations behind these claims "
            f"argue against the claim they belong to. An observation counts "
            f"against when the content was scrolled past well below your own "
            f"typical watch time, which is measured from your history rather "
            f"than fixed in seconds."
            if total_counter else
            "Nothing in the evidence collected so far contradicts itself. Every "
            "observation behind every claim was actually watched."
        ),
    }
