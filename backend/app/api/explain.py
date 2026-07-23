"""
Explainability APIs — expose internal cognitive state for dashboard visualization
and provide the full reasoning chain for any trace/response.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.db.postgres import fetch, fetchrow, fetchval

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ──────────────────────────────────────────────
def _parse_json_fields(d: dict, fields: list) -> dict:
    for key in fields:
        if isinstance(d.get(key), str):
            try:
                d[key] = json.loads(d[key])
            except Exception:
                pass
    return d


# ═══════════════════════════════════════════════════════════
# EXISTING ENDPOINTS (dashboard consumption)
# ═══════════════════════════════════════════════════════════

@router.get("/identity/snapshot", response_model=list)
async def get_identity_snapshots(
    user_id: str = Query(default="default"),
    limit: int = Query(default=10, le=100),
):
    rows = await fetch(
        """
        SELECT snapshot_id, identity_id, identity_version, user_id,
               overall_confidence, identity_completeness,
               dominant_topics, emerging_topics,
               snapshot_timestamp::text, is_active
        FROM identity_snapshots
        WHERE user_id = $1
        ORDER BY snapshot_timestamp DESC
        LIMIT $2
        """,
        user_id, limit,
    )
    return [dict(r) for r in rows]


@router.get("/identity/current", response_model=Optional[dict])
async def get_current_identity(user_id: str = Query(default="default")):
    identity = await fetchrow(
        "SELECT * FROM identities WHERE user_id = $1", user_id
    )
    if not identity:
        return None
    snapshot = await fetchrow(
        """
        SELECT * FROM identity_snapshots
        WHERE user_id = $1 ORDER BY snapshot_timestamp DESC LIMIT 1
        """,
        user_id,
    )
    return {
        "identity": dict(identity),
        "latest_snapshot": dict(snapshot) if snapshot else None,
    }


@router.get("/identity/self-model", response_model=Optional[dict])
async def get_self_model(user_id: str = Query(default="default")):
    row = await fetchrow(
        "SELECT * FROM self_models WHERE user_id = $1", user_id
    )
    return dict(row) if row else None


@router.get("/reasoning/evidence", response_model=list)
async def get_evidence(
    user_id: str = Query(default="default"),
    evidence_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
):
    if evidence_type:
        rows = await fetch(
            """SELECT evidence_id, evidence_type, confidence, weight,
                      net_confidence, explanation,
                      supporting_behavior_objects, created_at::text
               FROM evidence WHERE user_id = $1 AND evidence_type = $2
               ORDER BY confidence DESC LIMIT $3""",
            user_id, evidence_type, limit,
        )
    else:
        rows = await fetch(
            """SELECT evidence_id, evidence_type, confidence, weight,
                      net_confidence, explanation,
                      supporting_behavior_objects, created_at::text
               FROM evidence WHERE user_id = $1
               ORDER BY confidence DESC LIMIT $2""",
            user_id, limit,
        )
    return [_parse_json_fields(dict(r), ["supporting_behavior_objects"]) for r in rows]


@router.get("/reasoning/inferences", response_model=list)
async def get_inferences(
    user_id: str = Query(default="default"),
    limit: int = Query(default=50, le=200),
):
    rows = await fetch(
        """SELECT inference_id, inference_type, label, description,
                  confidence, importance, strength,
                  rule_name, inferred_at::text
           FROM inferences WHERE user_id = $1
           ORDER BY confidence DESC LIMIT $2""",
        user_id, limit,
    )
    return [dict(r) for r in rows]


@router.get("/reasoning/reflections", response_model=list)
async def get_reflections(
    user_id: str = Query(default="default"),
    limit: int = Query(default=20, le=100),
):
    rows = await fetch(
        """SELECT reflection_id, reflection_type, summary,
                  key_insights, patterns_identified, confidence,
                  period_start::text, period_end::text, created_at::text
           FROM reflections WHERE user_id = $1
           ORDER BY created_at DESC LIMIT $2""",
        user_id, limit,
    )
    return [_parse_json_fields(dict(r), ["key_insights", "patterns_identified"]) for r in rows]


@router.get("/reasoning/behavior-objects", response_model=list)
async def get_behavior_objects(
    user_id: str = Query(default="default"),
    limit: int = Query(default=50, le=200),
):
    rows = await fetch(
        """SELECT unique_id, topic, lifecycle_state, importance_score,
                  confidence_score, stability_score, creator_diversity_score,
                  keywords, creators, updated_at::text
           FROM behavior_objects WHERE user_id = $1
           ORDER BY importance_score DESC LIMIT $2""",
        user_id, limit,
    )
    return [_parse_json_fields(dict(r), ["keywords", "creators"]) for r in rows]


@router.get("/query/traces", response_model=list)
async def get_query_traces(
    user_id: str = Query(default="default"),
    limit: int = Query(default=20, le=100),
):
    rows = await fetch(
        """SELECT trace_id, user_id, query, intent_type, intent_confidence,
                  reasoning_mode, total_ms, runtime_load_ms, planning_ms,
                  retrieval_ms, ranking_ms, fusion_ms, decision_ms,
                  context_build_ms, verbalization_ms,
                  retrieved_count, evidence_count, behavior_object_count,
                  facts_generated, citations_created, aggregate_confidence,
                  decision_input_facts, decision_output_facts, decision_conflicts,
                  token_count, response_length, snapshot_version, inference_count,
                  reflection_count, success, errors, created_at::text
           FROM pipeline_traces WHERE user_id = $1
           ORDER BY created_at DESC LIMIT $2""",
        user_id, limit,
    )
    return [dict(r) for r in rows]


@router.get("/query/traces/{trace_id}", response_model=Optional[dict])
async def get_trace_detail(trace_id: str):
    row = await fetchrow(
        "SELECT * FROM pipeline_traces WHERE trace_id = $1", trace_id
    )
    return dict(row) if row else None


@router.get("/cognitive/metrics", response_model=list)
async def get_cognitive_metrics(
    user_id: str = Query(default="default"),
    metric_name: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
):
    if metric_name:
        rows = await fetch(
            """SELECT metric_name, metric_value, metric_tags, recorded_at::text
               FROM cognitive_metrics WHERE user_id = $1 AND metric_name = $2
               ORDER BY recorded_at DESC LIMIT $3""",
            user_id, metric_name, limit,
        )
    else:
        rows = await fetch(
            """SELECT metric_name, metric_value, metric_tags, recorded_at::text
               FROM cognitive_metrics WHERE user_id = $1
               ORDER BY recorded_at DESC LIMIT $2""",
            user_id, limit,
        )
    return [_parse_json_fields(dict(r), ["metric_tags"]) for r in rows]


@router.get("/cognitive/summary")
async def get_cognitive_summary(user_id: str = Query(default="default")):
    bo_count = await fetchval("SELECT COUNT(*) FROM behavior_objects WHERE user_id = $1", user_id)
    ev_count = await fetchval("SELECT COUNT(*) FROM evidence WHERE user_id = $1", user_id)
    inf_count = await fetchval("SELECT COUNT(*) FROM inferences WHERE user_id = $1", user_id)
    ref_count = await fetchval("SELECT COUNT(*) FROM reflections WHERE user_id = $1", user_id)
    snap_count = await fetchval("SELECT COUNT(*) FROM identity_snapshots WHERE user_id = $1", user_id)
    trace_count = await fetchval("SELECT COUNT(*) FROM pipeline_traces WHERE user_id = $1", user_id)
    last_identity = await fetchrow(
        """SELECT identity_version, overall_confidence, updated_at::text
           FROM identities WHERE user_id = $1 ORDER BY updated_at DESC LIMIT 1""",
        user_id,
    )
    return {
        "user_id": user_id,
        "behavior_object_count": bo_count or 0,
        "evidence_count": ev_count or 0,
        "inference_count": inf_count or 0,
        "reflection_count": ref_count or 0,
        "snapshot_count": snap_count or 0,
        "trace_count": trace_count or 0,
        "current_identity": dict(last_identity) if last_identity else None,
    }


# ═══════════════════════════════════════════════════════════
# NEW EXPLAINABILITY ENDPOINTS
# ═══════════════════════════════════════════════════════════

@router.get("/explain/{trace_id}")
async def explain_trace(trace_id: str):
    """Assemble the full reasoning chain for a given trace."""
    trace = await fetchrow("SELECT * FROM pipeline_traces WHERE trace_id = $1", trace_id)
    if not trace:
        return {"error": "Trace not found"}
    trace = _parse_json_fields(dict(trace), ["errors", "trace_data"])
    user_id = trace["user_id"]

    # Identity snapshot
    identity = None
    if trace.get("snapshot_id"):
        snapshot = await fetchrow(
            "SELECT * FROM identity_snapshots WHERE snapshot_id = $1", trace["snapshot_id"]
        )
        if snapshot:
            identity = _parse_json_fields(dict(snapshot), [
                "dominant_topics", "emerging_topics", "personality_traits", "interest_graph", "metadata"
            ])
    if not identity:
        snapshot = await fetchrow(
            "SELECT * FROM identity_snapshots WHERE user_id = $1 ORDER BY snapshot_timestamp DESC LIMIT 1",
            user_id,
        )
        if snapshot:
            identity = _parse_json_fields(dict(snapshot), [
                "dominant_topics", "emerging_topics", "personality_traits", "interest_graph", "metadata"
            ])

    # Self model
    self_model = None
    if trace.get("self_model_id"):
        sm = await fetchrow("SELECT * FROM self_models WHERE self_model_id = $1", trace["self_model_id"])
        if sm:
            self_model = _parse_json_fields(dict(sm), ["beliefs", "strong_beliefs", "uncertain_beliefs", "metadata"])
    if not self_model:
        sm = await fetchrow(
            "SELECT * FROM self_models WHERE user_id = $1 ORDER BY updated_at DESC LIMIT 1", user_id
        )
        if sm:
            self_model = _parse_json_fields(dict(sm), ["beliefs", "strong_beliefs", "uncertain_beliefs", "metadata"])

    # Evidence
    evidence_rows = await fetch(
        """SELECT evidence_id, evidence_type, confidence, weight, net_confidence,
                  explanation, supporting_behavior_objects, created_at::text
           FROM evidence WHERE user_id = $1 ORDER BY confidence DESC LIMIT 30""",
        user_id,
    )
    evidence = [_parse_json_fields(dict(r), ["supporting_behavior_objects"]) for r in evidence_rows]

    # Memories
    memory_rows = await fetch(
        """SELECT memory_id, memory_type, content, importance_score,
                  context, tags, related_memory_ids, access_count,
                  timestamp::text, created_at::text
           FROM memories WHERE user_id = $1 ORDER BY importance_score DESC LIMIT 20""",
        user_id,
    )
    memories = [_parse_json_fields(dict(r), ["context", "tags", "related_memory_ids"]) for r in memory_rows]

    grouped_memories = {}
    for m in memories:
        mt = m.get("memory_type", "episodic").lower()
        grouped_memories.setdefault(mt, []).append(m)

    # Planner data from trace_data
    trace_data = trace.get("trace_data", {})
    planner = trace_data.get("planner", {}) or {
        "intent": trace.get("intent_type", "unknown"),
        "intent_confidence": trace.get("intent_confidence"),
        "reasoning_mode": trace.get("reasoning_mode"),
        "plan_confidence": trace.get("plan_confidence"),
        "retrieval_strategy": trace_data.get("retrieval_strategy", "semantic"),
        "selected_tools": trace_data.get("selected_tools", []),
    }

    # Decision data
    decision_data = trace_data.get("decision", {}) or {
        "candidates": trace_data.get("decision_candidates", []),
        "input_facts": trace.get("decision_input_facts", 0),
        "output_facts": trace.get("decision_output_facts", 0),
        "conflicts": trace.get("decision_conflicts", 0),
        "aggregate_confidence": trace.get("aggregate_confidence"),
    }

    # Context
    context_data = trace_data.get("context", {}) or {
        "context_build_ms": trace.get("context_build_ms", 0),
        "retrieved_count": trace.get("retrieved_count", 0),
        "token_count": trace.get("token_count", 0),
    }

    # LLM data
    llm_data = trace_data.get("llm", {}) or {
        "provider": trace_data.get("provider", "OpenAI"),
        "model": trace_data.get("model", "gpt-4o-mini"),
        "latency_ms": trace.get("verbalization_ms", 0),
        "tokens": trace.get("token_count", 0),
        "response_length": trace.get("response_length", 0),
    }

    return {
        "trace_id": trace_id,
        "query": trace.get("query"),
        "response": trace_data.get("response", ""),
        "success": trace.get("success", False),
        "total_ms": trace.get("total_ms", 0),
        "identity": {
            "snapshot_id": identity.get("snapshot_id") if identity else None,
            "identity_version": identity.get("identity_version") if identity else None,
            "confidence": identity.get("overall_confidence") if identity else None,
            "completeness": identity.get("identity_completeness") if identity else None,
            "dominant_topics": identity.get("dominant_topics", []) if identity else [],
            "emerging_topics": identity.get("emerging_topics", []) if identity else [],
            "personality_traits": identity.get("personality_traits", {}) if identity else {},
            "interest_graph": identity.get("interest_graph", {}) if identity else {},
            "identity_id": identity.get("identity_id") if identity else None,
        },
        "self_model": self_model,
        "evidence": {"items": evidence, "count": len(evidence)},
        "memories": {"items": memories, "grouped": grouped_memories, "count": len(memories)},
        "planner": planner,
        "decision": decision_data,
        "context": context_data,
        "llm": llm_data,
        "pipeline": {
            "trace_id": trace_id,
            "intent": trace.get("intent_type"),
            "timeline_ms": {
                "runtime_load": trace.get("runtime_load_ms", 0),
                "planning": trace.get("planning_ms", 0),
                "retrieval": trace.get("retrieval_ms", 0),
                "ranking": trace.get("ranking_ms", 0),
                "fusion": trace.get("fusion_ms", 0),
                "decision": trace.get("decision_ms", 0),
                "context_build": trace.get("context_build_ms", 0),
                "verbalization": trace.get("verbalization_ms", 0),
                "total": trace.get("total_ms", 0),
            },
            "success": trace.get("success", False),
            "errors": trace.get("errors", []),
            "inference_count": trace.get("inference_count", 0),
            "evidence_count": trace.get("evidence_count", 0),
            "reflection_count": trace.get("reflection_count", 0),
            "retrieved_count": trace.get("retrieved_count", 0),
        },
    }


@router.get("/explain/evidence/{evidence_id}")
async def explain_evidence_detail(evidence_id: str):
    """Full evidence detail with linked objects."""
    ev = await fetchrow("SELECT * FROM evidence WHERE evidence_id = $1", evidence_id)
    if not ev:
        return {"error": "Evidence not found"}
    ev = _parse_json_fields(dict(ev), ["supporting_behavior_objects", "supporting_evidence_ids", "metadata"])
    user_id = ev["user_id"]

    bo_ids = ev.get("supporting_behavior_objects", [])
    behavior_objects = []
    if isinstance(bo_ids, list) and bo_ids:
        placeholders = ", ".join(f"${i+1}" for i in range(len(bo_ids)))
        bos = await fetch(
            f"SELECT unique_id, topic, importance_score, confidence_score, keywords FROM behavior_objects WHERE unique_id IN ({placeholders})",
            *bo_ids
        )
        behavior_objects = [_parse_json_fields(dict(r), ["keywords"]) for r in bos]

    inferences = await fetch(
        "SELECT inference_id, inference_type, label, description, confidence FROM inferences WHERE user_id = $1 ORDER BY confidence DESC LIMIT 10",
        user_id,
    )
    memories = await fetch(
        "SELECT memory_id, memory_type, content, importance_score FROM memories WHERE user_id = $1 ORDER BY importance_score DESC LIMIT 10",
        user_id,
    )
    snapshot = await fetchrow(
        "SELECT dominant_topics, identity_completeness, overall_confidence FROM identity_snapshots WHERE user_id = $1 ORDER BY snapshot_timestamp DESC LIMIT 1",
        user_id,
    )
    identity_traits = _parse_json_fields(dict(snapshot), ["dominant_topics"]) if snapshot else {}

    supporting_ids = ev.get("supporting_evidence_ids", [])
    counter_evidence = []
    if isinstance(supporting_ids, list) and supporting_ids:
        placeholders = ", ".join(f"${i+1}" for i in range(len(supporting_ids)))
        counter_evidence = [
            dict(r) for r in await fetch(
                f"SELECT evidence_id, evidence_type, confidence, explanation FROM evidence WHERE evidence_id IN ({placeholders})",
                *supporting_ids
            )
        ]

    return {
        "evidence": ev,
        "behavior_objects": behavior_objects,
        "inferences": [dict(r) for r in inferences],
        "memories": [dict(r) for r in memories],
        "identity_traits": identity_traits,
        "counter_evidence": counter_evidence,
    }


@router.get("/explain/identity/{identity_id}")
async def explain_identity_detail(identity_id: str):
    """Full identity breakdown with contribution analysis."""
    identity = await fetchrow("SELECT * FROM identities WHERE identity_id = $1", identity_id)
    if not identity:
        return {"error": "Identity not found"}
    identity = dict(identity)
    user_id = identity["user_id"]

    snapshots = [
        _parse_json_fields(dict(r), ["dominant_topics", "emerging_topics", "personality_traits", "interest_graph"])
        for r in await fetch(
            "SELECT * FROM identity_snapshots WHERE identity_id = $1 ORDER BY snapshot_timestamp DESC LIMIT 20",
            identity_id,
        )
    ]

    evidence_list = [
        dict(r) for r in await fetch(
            "SELECT evidence_id, evidence_type, confidence, explanation FROM evidence WHERE user_id = $1 ORDER BY confidence DESC LIMIT 20",
            user_id,
        )
    ]

    bo_list = [
        dict(r) for r in await fetch(
            "SELECT unique_id, topic, importance_score, confidence_score, creator_diversity_score FROM behavior_objects WHERE user_id = $1 ORDER BY importance_score DESC LIMIT 20",
            user_id,
        )
    ]

    memories = [
        dict(r) for r in await fetch(
            "SELECT memory_id, memory_type, content, importance_score FROM memories WHERE user_id = $1 ORDER BY importance_score DESC LIMIT 20",
            user_id,
        )
    ]

    reflections = [
        dict(r) for r in await fetch(
            "SELECT reflection_id, reflection_type, summary, confidence FROM reflections WHERE user_id = $1 ORDER BY created_at DESC LIMIT 10",
            user_id,
        )
    ]

    topics = {}
    for bo in bo_list:
        topic = bo.get("topic", "unknown")
        if topic not in topics:
            topics[topic] = {"count": 0, "total_importance": 0}
        topics[topic]["count"] += 1
        topics[topic]["total_importance"] += bo.get("importance_score", 0)

    bo_contrib = min(35, len(bo_list) * 1.75)
    ev_contrib = min(28, len(evidence_list) * 1.4)
    ref_contrib = min(16, len(reflections) * 1.6)
    mem_contrib = min(12, len(memories) * 0.6)
    temporal_contrib = max(0, 100 - bo_contrib - ev_contrib - ref_contrib - mem_contrib)

    return {
        "identity": identity,
        "snapshots": snapshots,
        "evidence": evidence_list,
        "behavior_objects": bo_list,
        "memories": memories,
        "reflections": reflections,
        "topics": topics,
        "contribution_breakdown": {
            "behavior_events": round(bo_contrib, 1),
            "evidence": round(ev_contrib, 1),
            "reflection": round(ref_contrib, 1),
            "semantic_memory": round(mem_contrib, 1),
            "temporal_consistency": round(temporal_contrib, 1),
        },
    }


@router.get("/search")
async def global_search(
    q: str = Query(default=""),
    limit: int = Query(default=20, le=50),
):
    if not q or len(q.strip()) < 1:
        return {"results": []}
    pattern = f"%{q}%"
    results = []

    for r in await fetch(
        "SELECT evidence_id, evidence_type, confidence, explanation, 'evidence' as entity_type FROM evidence WHERE explanation ILIKE $1 ORDER BY confidence DESC LIMIT $2",
        pattern, limit,
    ):
        results.append({
            "id": r["evidence_id"], "type": "evidence",
            "label": (r["explanation"] or "")[:120] or r["evidence_id"],
            "subtitle": f"{r['evidence_type']} · {round(r['confidence'] * 100)}%",
        })

    for r in await fetch(
        "SELECT inference_id, inference_type, label, description, confidence, 'inference' as entity_type FROM inferences WHERE label ILIKE $1 OR description ILIKE $1 ORDER BY confidence DESC LIMIT $2",
        pattern, limit,
    ):
        results.append({
            "id": r["inference_id"], "type": "inference",
            "label": (r["label"] or r["description"] or "")[:120],
            "subtitle": f"{r['inference_type']} · {round(r['confidence'] * 100)}%",
        })

    for r in await fetch(
        "SELECT memory_id, memory_type, content, importance_score, 'memory' as entity_type FROM memories WHERE content ILIKE $1 ORDER BY importance_score DESC LIMIT $2",
        pattern, limit,
    ):
        results.append({
            "id": r["memory_id"], "type": "memory",
            "label": (r["content"] or "")[:120] or r["memory_id"],
            "subtitle": f"{r['memory_type']} · importance: {round(r['importance_score'], 2)}",
        })

    for r in await fetch(
        "SELECT unique_id, topic, importance_score, confidence_score, 'behavior' as entity_type FROM behavior_objects WHERE topic ILIKE $1 ORDER BY importance_score DESC LIMIT $2",
        pattern, limit,
    ):
        results.append({
            "id": r["unique_id"], "type": "behavior",
            "label": r["topic"] or r["unique_id"],
            "subtitle": f"importance: {round(r['importance_score'], 2)} · {round(r['confidence_score'] * 100)}%",
        })

    for r in await fetch(
        "SELECT reflection_id, reflection_type, summary, confidence, 'reflection' as entity_type FROM reflections WHERE summary ILIKE $1 ORDER BY confidence DESC LIMIT $2",
        pattern, limit,
    ):
        results.append({
            "id": r["reflection_id"], "type": "reflection",
            "label": (r["summary"] or "")[:120] or r["reflection_id"],
            "subtitle": f"{r['reflection_type']} · {round(r['confidence'] * 100)}%",
        })

    for r in await fetch(
        "SELECT trace_id, query, intent_type, total_ms, success, 'trace' as entity_type FROM pipeline_traces WHERE query ILIKE $1 ORDER BY created_at DESC LIMIT $2",
        pattern, limit,
    ):
        results.append({
            "id": r["trace_id"], "type": "trace",
            "label": (r["query"] or "")[:120] or r["trace_id"],
            "subtitle": f"{r['intent_type'] or 'unknown'} · {round(r['total_ms'])}ms",
        })

    results.sort(key=lambda x: x.get("subtitle", ""), reverse=True)
    return {"results": results[:limit], "total": len(results)}
