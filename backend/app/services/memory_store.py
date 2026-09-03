"""The recall index: what is worth remembering, and how often it is recalled.

The `memories` table has existed since the original schema, with five indexes
including one on importance and one on (user_id, memory_type). It held zero
rows. There was no writer anywhere in the system - a fact already documented in
cognitive_pipeline/pipeline.py, which populates the character's memory
references from identities.source_behavior_objects instead, and in
app/api/timeline.py, which queries the table on every request and has always
received nothing.

The `memory/` package alongside it declares five memory types across six
modules. Each stores to `self._memory_store: Dict[str, MemoryRecord]` under the
comment "In-memory storage (in production, use database)", and none of the five
classes is referenced anywhere outside its own singleton getter. The paper
states that "AIMirror uses five memory types and, unlike these systems, selects
among them with a planner that never calls a language model"; the planner half
is true and the five-memory-types half was not.

The functional consequence is on the live answer path. For the memory_question
intent the retrieval planner requests RetrievalTarget.MEMORY at priority 0.8
with required=True - the highest-priority mandatory source for that intent -
and it resolved to an empty table.

What this is not
----------------

Not another copy of the typed stores. Events, behaviour objects, evidence,
inferences, reflections and goals all have homes with better structure than a
generic row, and duplicating them here would create a second source of truth
that drifts from the first.

A recall index is the thing none of those tables is: a curated subset carrying
what the schema was already shaped for - importance, access_count,
last_accessed - so the system can answer "what stands out" rather than "what
happened", and can tell how often something has actually been recalled.

Writes are idempotent. A memory's id is derived from what it is about, so
re-ingesting the same history updates one row rather than appending a duplicate
on every batch, which is how the reflections table came to hold 29 rows nobody
could use.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from app.db.postgres import execute, fetch

logger = logging.getLogger(__name__)

# Only material above this is worth keeping. A recall index that stores
# everything is the table it is built from.
MIN_IMPORTANCE = 0.35

# Per ingest, per type. Bounds the write and keeps the index a selection.
MAX_PER_TYPE = 25

VALID_TYPES = ("episodic", "semantic", "behavioral", "goal", "reflection")


def memory_id(user_id: str, memory_type: str, subject: str) -> str:
    """Deterministic, so re-ingesting updates rather than appends.

    Keyed on what the memory is about rather than on when it was written: the
    same conclusion drawn twice is one memory that has been reinforced, not two
    memories.
    """
    digest = hashlib.md5(
        f"{user_id}|{memory_type}|{subject}".encode("utf-8")
    ).hexdigest()[:16]
    return f"mem_{memory_type}_{digest}"


def _clip(text: Any, limit: int = 500) -> str:
    return (str(text or "").strip())[:limit]


async def remember(
    user_id: str,
    memory_type: str,
    subject: str,
    content: str,
    importance: float,
    source_event_ids: Optional[List[Any]] = None,
    tags: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> bool:
    """Record one memory, or reinforce it if already held."""
    if memory_type not in VALID_TYPES:
        logger.warning("Unknown memory type %r; not stored", memory_type)
        return False
    if not content or importance < MIN_IMPORTANCE:
        return False

    ids = []
    for raw in (source_event_ids or []):
        try:
            ids.append(int(raw))
        except (TypeError, ValueError):
            continue

    try:
        await execute(
            """
            INSERT INTO memories (
                memory_id, user_id, memory_type, content, context, tags,
                importance_score, source_event_ids, metadata, timestamp
            ) VALUES ($1,$2,$3,$4,$5::jsonb,$6::jsonb,$7,$8::jsonb,$9::jsonb, NOW())
            ON CONFLICT (memory_id) DO UPDATE SET
                content = EXCLUDED.content,
                importance_score = EXCLUDED.importance_score,
                source_event_ids = EXCLUDED.source_event_ids,
                context = EXCLUDED.context,
                tags = EXCLUDED.tags,
                timestamp = NOW()
            """,
            memory_id(user_id, memory_type, subject),
            user_id,
            memory_type,
            _clip(content),
            json.dumps(context or {}),
            json.dumps(tags or []),
            round(float(max(0.0, min(1.0, importance))), 3),
            json.dumps(ids),
            json.dumps({"subject": _clip(subject, 120)}),
        )
        return True
    except Exception as e:
        logger.error("Could not store memory for %s: %s", user_id, e)
        return False


async def recall(
    user_id: str,
    limit: int = 15,
    memory_types: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """The most important memories, and note that they were recalled.

    access_count and last_accessed exist in the schema and had never been
    written, so nothing could tell a memory consulted daily from one never
    looked at. Recall records itself.
    """
    wanted = [t for t in (memory_types or []) if t in VALID_TYPES]

    if wanted:
        rows = await fetch(
            """SELECT memory_id, memory_type, content, importance_score,
                      access_count, source_event_ids, timestamp
               FROM memories
               WHERE user_id = $1 AND memory_type = ANY($2)
               ORDER BY importance_score DESC, timestamp DESC LIMIT $3""",
            user_id, wanted, limit,
        )
    else:
        rows = await fetch(
            """SELECT memory_id, memory_type, content, importance_score,
                      access_count, source_event_ids, timestamp
               FROM memories WHERE user_id = $1
               ORDER BY importance_score DESC, timestamp DESC LIMIT $2""",
            user_id, limit,
        )

    if rows:
        try:
            await execute(
                """UPDATE memories SET access_count = access_count + 1,
                                       last_accessed = NOW()
                   WHERE memory_id = ANY($1)""",
                [r["memory_id"] for r in rows],
            )
        except Exception as e:
            # Recording the read must never fail the read.
            logger.warning("Could not record memory access: %s", e)

    return [
        {
            "memory_id": r["memory_id"],
            "memory_type": r["memory_type"],
            "content": r["content"],
            "importance": float(r["importance_score"] or 0.0),
            "recalled_before": int(r["access_count"] or 0),
            "at": r["timestamp"].isoformat() if r["timestamp"] else None,
        }
        for r in rows
    ]


async def write_from_pipeline(
    user_id: str,
    behavior_objects: Optional[List[Any]] = None,
    inferences: Optional[List[Any]] = None,
    reflection: Any = None,
) -> int:
    """Select what is worth remembering from one consolidation.

    Each type is drawn from the material that genuinely has that character,
    rather than writing the same row five times under five labels.
    """
    written = 0

    # Semantic: consolidated facts about the person. Importance is the
    # behaviour's own, so the selection is the pipeline's judgement, not a
    # second opinion invented here.
    ranked = sorted(
        [b for b in (behavior_objects or [])
         if getattr(b, "topic", None)],
        key=lambda b: float(getattr(b, "importance_score", 0.0) or 0.0),
        reverse=True,
    )[:MAX_PER_TYPE]

    for bo in ranked:
        stats = getattr(bo, "temporal_statistics", None)
        count = getattr(stats, "occurrence_count", 0) or 0
        ok = await remember(
            user_id=user_id,
            memory_type="semantic",
            subject=str(bo.topic),
            content=f"{bo.topic} appears {count} times in this history.",
            importance=float(getattr(bo, "importance_score", 0.0) or 0.0),
            source_event_ids=getattr(bo, "supporting_event_ids", None),
            tags=[str(bo.topic)],
            context={"lifecycle": str(getattr(bo, "lifecycle_state", "") or "")},
        )
        written += 1 if ok else 0

    # Behavioural: the conclusions drawn, which are what a person would
    # recognise as something the system remembers about them.
    for inf in (inferences or [])[:MAX_PER_TYPE]:
        ok = await remember(
            user_id=user_id,
            memory_type="behavioral",
            subject=str(getattr(inf, "rule_name", "") or getattr(inf, "label", "")),
            content=str(getattr(inf, "description", "") or ""),
            importance=float(getattr(inf, "importance", 0.0) or 0.0),
            tags=list(getattr(inf, "affected_topics", None) or [])[:5],
            context={"confidence": float(getattr(inf, "confidence", 0.0) or 0.0)},
        )
        written += 1 if ok else 0

    # Reflection: the narrative summary of the period.
    if reflection is not None and getattr(reflection, "summary", None):
        ok = await remember(
            user_id=user_id,
            memory_type="reflection",
            subject=str(getattr(reflection, "reflection_type", "reflection")),
            content=str(reflection.summary),
            importance=float(getattr(reflection, "confidence", 0.5) or 0.5),
            context={"period_start": str(getattr(reflection, "period_start", "") or "")},
        )
        written += 1 if ok else 0

    if written:
        logger.info("Recall index: %d memories written for %s", written, user_id)
    return written
