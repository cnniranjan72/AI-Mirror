"""What the system does not know about someone, and which kind of not-knowing.

The self model has always carried an uncertainty map. It was stored for every
user, indexed, read back into the character runtime, consulted by the decision
engine and injected into the context the language model sees. It was never once
shown to the person it described.

Worse, it conflated two different claims. A topic the system had reasoned about
and found itself unsure of was given a measured uncertainty; a topic no belief
addressed at all was given a flat 0.8 and filed in the same dictionary, in the
same scale. Across the deployed instance 19 of 50 domain values were that
constant. Nothing downstream could tell them apart, so "I have never considered
this" reached the language model as "I am highly uncertain about this".

Three kinds of not-knowing are separated here, because the honest answer to each
is different:

  unexamined   No belief addresses this topic. The system has nothing to say,
               which is not the same as being unsure.
  uncertain    Beliefs exist and are weak. This is a measurement.
  contested    Beliefs exist and the evidence underneath them disagrees with
               itself - see services/contested.py.

Only the middle one is a number, and only it is reported as one.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.db.postgres import fetch, fetchrow

logger = logging.getLogger(__name__)

# A domain counts as poorly understood above this. It matches the threshold
# _update_categorization already uses for high_uncertainty_domains, so the two
# surfaces cannot disagree about the same account.
HIGH_UNCERTAINTY = 0.6

MAX_LISTED = 40


def _decode(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return None
    return value


async def build_blind_spots(user_id: str) -> Dict[str, Any]:
    """Where this model is thin, and why."""
    row = await fetchrow(
        """
        SELECT uncertainty_map, beliefs, uncertain_beliefs, strong_beliefs,
               overall_confidence, model_completeness, updated_at
        FROM self_models WHERE user_id = $1
        ORDER BY created_at DESC LIMIT 1
        """,
        user_id,
    )

    if not row:
        return {
            "user_id": user_id,
            "measurable": False,
            "note": (
                "No self model has been built for this account yet, so there is "
                "nothing to say about what it does or does not know."
            ),
        }

    umap = _decode(row["uncertainty_map"]) or {}
    beliefs = _decode(row["beliefs"]) or []
    uncertain_ids = set(_decode(row["uncertain_beliefs"]) or [])

    if not isinstance(umap, dict):
        umap = {}

    domains = umap.get("domain_uncertainties") or {}
    if not isinstance(domains, dict):
        domains = {}

    # Rows written before the distinction existed have no such key at all, and
    # their domain values silently mix measurement with a 0.8 placeholder.
    # There is no way to tell which is which after the fact, so the map says so
    # rather than presenting the mixture as measured.
    stale = "unexamined_domains" not in umap
    unexamined = list(umap.get("unexamined_domains") or [])

    # Which beliefs speak to each domain, so a number is never shown without
    # what produced it.
    by_domain: Dict[str, List[Dict[str, Any]]] = {}
    for domain in domains:
        needle = str(domain).strip().lower()
        speaking = []
        for belief in beliefs:
            text = (belief.get("description") or "").lower()
            if needle and needle in text:
                speaking.append({
                    "statement": belief.get("statement") or belief.get("description"),
                    "confidence": belief.get("confidence"),
                    "contested": belief.get("belief_id") in uncertain_ids,
                })
        by_domain[domain] = speaking

    assessed = sorted(
        (
            {
                "domain": d,
                "uncertainty": round(float(u), 3),
                "beliefs": by_domain.get(d, [])[:4],
                "belief_count": len(by_domain.get(d, [])),
                "poorly_understood": float(u) >= HIGH_UNCERTAINTY,
            }
            for d, u in domains.items()
            if isinstance(u, (int, float))
        ),
        key=lambda x: x["uncertainty"],
        reverse=True,
    )[:MAX_LISTED]

    contested_count = sum(
        1 for b in beliefs if b.get("belief_id") in uncertain_ids
    )

    total_topics = len(domains) + len(unexamined)
    share_assessed = (len(domains) / total_topics) if total_topics else 0.0

    if stale:
        note = (
            "This model was built before measured uncertainty and unexamined "
            "topics were recorded separately, so its figures may include a "
            "placeholder value for topics nothing was ever concluded about. "
            "The next time this account ingests activity the distinction will "
            "be drawn properly."
        )
    elif not unexamined and assessed:
        note = (
            f"Every topic in this identity has at least one belief attached to "
            f"it. {len([a for a in assessed if a['poorly_understood']])} of "
            f"{len(assessed)} are still poorly understood."
        )
    else:
        note = (
            f"{len(unexamined)} of {total_topics} topics in this identity have "
            f"no belief attached to them at all. That is not a low-confidence "
            f"reading, it is the absence of one: the system has nothing to say "
            f"about them, and says so rather than reporting a number it did "
            f"not measure."
        )

    return {
        "user_id": user_id,
        "measurable": True,
        "stale_model": stale,
        "coverage": {
            "topics": total_topics,
            "assessed": len(domains),
            "unexamined": len(unexamined),
            "share_assessed": round(share_assessed, 3),
            "model_completeness": row["model_completeness"],
            "overall_confidence": row["overall_confidence"],
        },
        "assessed": assessed,
        "unexamined": unexamined[:MAX_LISTED],
        "contested_beliefs": contested_count,
        "belief_count": len(beliefs),
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "note": note,
    }
