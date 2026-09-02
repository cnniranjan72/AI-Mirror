"""One reasoning run, opened up.

The architecture's central claim is that nothing is decided by a language
model: seven deterministic stages choose what to say, and the model is handed a
finished plan to put into words. Every run already records enough to check
that - per-stage timings, the intent and its confidence, how many retrieval
directives were fulfilled, how many facts entered the decision engine, how many
were dropped and for which of three reasons, and which provider was used. All
of it sat in a JSONB column that nothing read.

The most useful thing in there is the split. On a real run the six deciding
stages together took 3.23 ms while verbalization took 11,373 ms. A claim that
the model is not doing the thinking is easy to make and hard to believe; a
three-thousand-fold gap between deciding and talking is the kind of evidence
that settles it.

This module only reshapes what the pipeline already recorded. It computes
nothing about the run itself, so it cannot flatter it.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.db.postgres import fetchrow

logger = logging.getLogger(__name__)

# The stages, in execution order, with the trace key holding each duration.
# Verbalization is marked separately because it is the only one that may call
# a language model - the distinction this whole view exists to show.
STAGES = [
    ("Runtime", "runtime_load_ms", "deterministic",
     "Loads the frozen identity snapshot the rest of the run reads from."),
    ("Planning", "planning_ms", "deterministic",
     "Classifies intent and picks a reasoning mode, by rule."),
    ("Retrieval", "retrieval_ms", "deterministic",
     "Fetches only the sources the plan asked for."),
    ("Ranking", "ranking_ms", "deterministic",
     "Orders what came back by relevance to the plan."),
    ("Fusion", "fusion_ms", "deterministic",
     "Merges sources into candidate facts, dropping duplicates."),
    ("Decision", "decision_ms", "deterministic",
     "Scores each candidate and selects what may be said."),
    ("Context", "context_build_ms", "deterministic",
     "Assembles the selected facts into a structured plan."),
    ("Verbalization", "verbalization_ms", "language_model",
     "The only stage a language model can touch, and it receives a finished plan."),
]


def _decode(value: Any) -> Dict[str, Any]:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return {}
    return value or {}


def _num(data: Dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        value = data.get(key)
        return default if value is None else float(value)
    except (TypeError, ValueError):
        return default


def _detail(name: str, t: Dict[str, Any]) -> Optional[str]:
    """What that stage actually decided, in its own recorded terms."""
    if name == "Runtime":
        version = t.get("snapshot_version")
        return f"read identity snapshot v{version}" if version is not None else None
    if name == "Planning":
        intent, confidence = t.get("intent_type"), t.get("intent_confidence")
        if not intent:
            return None
        mode = t.get("reasoning_mode")
        text = f"intent: {intent}"
        if confidence is not None:
            text += f" ({float(confidence):.2f})"
        return text + (f", mode: {mode}" if mode else "")
    if name == "Retrieval":
        done, total = t.get("directives_fulfilled"), t.get("directives_total")
        got = t.get("retrieved_count")
        if done is None and got is None:
            return None
        return f"{done}/{total} directives fulfilled, {got} items"
    if name == "Fusion":
        generated = t.get("facts_generated")
        return None if generated is None else f"{generated} candidate facts"
    if name == "Decision":
        into, out = t.get("decision_input_facts"), t.get("decision_output_facts")
        if into is None:
            return None
        return f"{into} in, {out} kept"
    if name == "Context":
        cites = t.get("citations_created")
        return None if cites is None else f"{cites} citations attached"
    if name == "Verbalization":
        provider, model = t.get("provider"), t.get("model")
        if provider is None:
            return None
        # provider "fallback" with no model means the deterministic template
        # answered and no language model was reached at all.
        return f"provider: {provider}" + (f", model: {model}" if model else ", no model called")
    return None


async def build_xray(user_id: str, trace_id: str) -> Optional[Dict[str, Any]]:
    """Reshape one recorded run into stages, a funnel, and the timing split."""
    row = await fetchrow(
        "SELECT trace_id, user_id, query, trace_data, created_at "
        "FROM pipeline_traces WHERE trace_id = $1 AND user_id = $2",
        trace_id, user_id,
    )
    if not row:
        return None

    t = _decode(row["trace_data"])

    stages: List[Dict[str, Any]] = []
    for name, key, kind, purpose in STAGES:
        stages.append({
            "name": name,
            "ms": round(_num(t, key), 3),
            "kind": kind,
            "purpose": purpose,
            "detail": _detail(name, t),
        })

    deciding = round(sum(s["ms"] for s in stages if s["kind"] == "deterministic"), 3)
    talking = round(sum(s["ms"] for s in stages if s["kind"] == "language_model"), 3)

    into = int(_num(t, "decision_input_facts"))
    dropped = {
        "low confidence": int(_num(t, "decision_removed_low_confidence")),
        "duplicate": int(_num(t, "decision_removed_duplicates")),
        "topic already covered": int(_num(t, "decision_removed_diversity")),
    }

    return {
        "trace_id": row["trace_id"],
        "query": row["query"] or t.get("query"),
        "at": row["created_at"].isoformat() if row["created_at"] else None,
        "success": bool(t.get("success")),
        "stages": stages,
        "funnel": {
            "retrieved": int(_num(t, "retrieved_count")),
            "candidates": int(_num(t, "facts_generated")),
            "into_decision": into,
            "dropped": {k: v for k, v in dropped.items() if v},
            "dropped_total": sum(dropped.values()),
            "kept": int(_num(t, "decision_output_facts")),
            "citations": int(_num(t, "citations_created")),
            "conflicts": int(_num(t, "decision_conflicts")),
        },
        "timing": {
            "deciding_ms": deciding,
            "talking_ms": talking,
            # None rather than a number when there is nothing to compare
            # against; a fabricated ratio would be the easiest thing here to
            # get wrong in the system's favour.
            "ratio": round(talking / deciding, 1) if deciding > 0 and talking > 0 else None,
            "total_ms": round(_num(t, "total_ms"), 3),
        },
        # provider "fallback" without a model means no language model was
        # reached; the deterministic template produced the wording.
        "llm_called": bool(t.get("model")),
        "aggregate_confidence": t.get("aggregate_confidence"),
        "note": (
            "Every stage above except Verbalization is deterministic: the same "
            "input produces the same plan. The language model receives that "
            "plan already decided, and only puts it into words."
        ),
    }
