"""What would it take to change the system's mind about you?

This is the one thing the architecture can do that a language-model-driven
system cannot do honestly. Because every stage before verbalization is
deterministic, the pipeline can be re-run over a hypothetical history and the
answer is trustworthy: the same inputs give the same conclusions, so a
difference in the output is caused by the difference in the input and nothing
else. Ask a stochastic model the same question twice and the two answers differ
for reasons that have nothing to do with the hypothetical.

The run touches nothing. V3Pipeline keeps all fifteen of its write calls behind
_persist_all, and the five reasoning steps are read-only - checked by AST, not
assumed. This module therefore calls those steps directly and never calls
_persist_all, so a counterfactual cannot alter the identity it is asking about.
That property is load-bearing: a feature that silently rewrote someone's twin
while showing them a hypothetical would be indefensible in a product built on
this argument.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# A hypothetical is capped well below a normal ingest. The purpose is to see
# which way the model moves and how far, not to simulate a new lifetime, and an
# unbounded body would let one request run the whole pipeline repeatedly.
MAX_HYPOTHETICAL_EVENTS = 200


async def run_counterfactual(
    user_id: str,
    hypothetical_events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Re-run the reasoning stages over real history plus hypothetical events.

    Returns the identity the system WOULD hold, the distance from the one it
    actually holds, and which of the seventeen measures moved.
    """
    from app.db.postgres import fetch
    from backend.core.behavior_gateway import get_behavior_gateway
    from backend.identity.identity_evolution import IdentityEvolutionEngine
    from backend.shared.contracts import EventSource
    from pipeline.orchestrator import V3Pipeline

    from app.services.identity_drift import DIMENSIONS, _Shim, _decode, _distance, _vector

    if not hypothetical_events:
        return {"error": "no hypothetical events supplied"}
    if len(hypothetical_events) > MAX_HYPOTHETICAL_EVENTS:
        hypothetical_events = hypothetical_events[:MAX_HYPOTHETICAL_EVENTS]

    # The identity as it stands, read from the same vector definition the
    # snapshot threshold uses, so "how far would this move me" is measured on
    # the scale the system itself acts on.
    live_row = await fetch("SELECT * FROM identities WHERE user_id = $1", user_id)
    if not live_row:
        return {"measurable": False,
                "note": "No identity yet, so there is nothing to move. "
                        "Counterfactuals need a baseline to compare against."}
    live = {k: (_decode(v) if isinstance(v, (str, dict)) else v)
            for k, v in dict(live_row[0]).items()}
    before = _vector(_Shim(live))

    # Replay the user's real events alongside the hypothetical ones, so the
    # comparison is "history plus this" rather than "this alone".
    real_rows = await fetch(
        """SELECT reel_id, username, caption, hashtags, watch_time, timestamp, session_id
           FROM events WHERE user_id = $1 ORDER BY timestamp DESC LIMIT 800""",
        user_id,
    )
    real = [{
        "reel_id": r["reel_id"], "username": r["username"] or "unknown",
        "caption": r["caption"] or "", "hashtags": _decode(r["hashtags"]) or [],
        "watch_time": float(r["watch_time"] or 0),
        "timestamp": r["timestamp"].isoformat() if r["timestamp"] else "",
        "session_id": r["session_id"] or "",
    } for r in real_rows]

    combined = real + list(hypothetical_events)
    normalized = get_behavior_gateway().process_batch(
        {"events": combined}, EventSource.CHROME_EXTENSION)

    pipeline = V3Pipeline()
    try:
        # Steps 1-5 only. _persist_all is deliberately never called; see the
        # module docstring for why that is the point rather than an oversight.
        behaviors = await pipeline._consolidate_events(user_id, normalized)
        evidence = pipeline._collect_evidence(user_id, normalized, behaviors)
        inferences = pipeline._generate_inferences(user_id, behaviors, evidence)
        built = await pipeline._construct_identity(
            user_id, behaviors, inferences, evidence, None, None)
    except Exception as e:
        logger.error("Counterfactual run failed for %s: %s", user_id, e, exc_info=True)
        return {"measurable": False, "note": f"The hypothetical run failed: {e}"}

    hypothetical_identity = built.get("identity")
    if hypothetical_identity is None:
        return {"measurable": False,
                "note": "The hypothetical produced no identity to compare."}

    after = _vector(hypothetical_identity)
    shift = _distance(before, after)

    moves = []
    for i in range(min(len(before), len(after), len(DIMENSIONS))):
        delta = round(after[i] - before[i], 4)
        if abs(delta) >= 0.01:
            moves.append({
                "dimension": DIMENSIONS[i][0],
                "meaning": DIMENSIONS[i][1],
                "from": round(before[i], 4),
                "to": round(after[i], 4),
                "delta": delta,
            })
    moves.sort(key=lambda m: -abs(m["delta"]))

    threshold = IdentityEvolutionEngine().config.get("snapshot_threshold", 0.30)
    return {
        "measurable": True,
        "added_events": len(hypothetical_events),
        "real_events_replayed": len(real),
        "shift": shift,
        "snapshot_threshold": threshold,
        # Whether this hypothetical is enough for the system to record a new
        # version of you, which is the concrete stake behind the question.
        "would_warrant_snapshot": bool(shift is not None and shift > threshold),
        "moves": moves[:8],
        "unchanged": len(DIMENSIONS) - len(moves),
        "persisted": False,
        "note": (
            "Nothing was saved. The reasoning stages ran over your real history "
            "plus these hypothetical events, and the result was discarded. Your "
            "identity is unchanged."
        ),
    }
