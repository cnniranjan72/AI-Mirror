"""
Explainability APIs — expose internal cognitive state for dashboard visualization
and provide the full reasoning chain for any trace/response.

Four endpoints here are addressed by an opaque resource id rather than by
user_id: /query/traces/{trace_id}, /explain/{trace_id},
/explain/evidence/{evidence_id} and /explain/identity/{identity_id}. They read
the owning user_id off the row they just fetched and then assemble that user's
identity snapshot, personality traits, interest graph, beliefs, evidence,
inferences and reflections — the most sensitive data in the product.

They originally did that with no ownership check at all, so anyone holding an
id could read another account's complete profile. The ids are not hard to come
by either: evidence ids are built as evidence_{type}_{topic}_{timestamp} and
identity ids embed the username with 8 hex characters of randomness.

Because the owner is only known after the row is read, the check cannot be a
dependency; each handler calls enforce_user_match once it has the row. That
keeps the usual contract — demo/public ids stay browsable signed out, a real
user needs a matching token.

One accepted limitation: enforcing after the lookup means a caller can tell an
id that exists but is not theirs (401/403) from one that does not exist (the
not-found body). That leaks existence, not content, and is the trade for
giving a signed-out user a clear "sign in" error instead of a false 404.
"""
import json
import logging
from typing import Optional, Any, Dict, List

from fastapi import APIRouter, Depends, Header, Query, HTTPException

from app.api.deps import enforce_user_match, resolve_user_id
from pydantic import BaseModel

from app.db.postgres import fetch, fetchrow, fetchval

logger = logging.getLogger(__name__)
# A popular topic can accumulate hundreds of skips. The count is reported in
# full; only the resolved rows are capped, so the number a reader sees is never
# the truncated one.
MAX_CONFLICTS_RETURNED = 50

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
    user_id: str = Depends(resolve_user_id),
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
async def get_current_identity(user_id: str = Depends(resolve_user_id)):
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


@router.get("/query/traces/{trace_id}/xray")
async def get_reasoning_xray(
    trace_id: str,
    authorization: Optional[str] = Header(default=None),
    user_id: str = Query(default="default"),
):
    """One reasoning run, opened up: per-stage timings, the decision funnel,
    and the split between deciding and talking.

    Scoped by user_id and checked, like the other trace endpoints: a run
    records what the system concluded about a specific person.
    """
    enforce_user_match(authorization, user_id)
    from app.services.reasoning_xray import build_xray

    xray = await build_xray(user_id, trace_id)
    if xray is None:
        raise HTTPException(status_code=404, detail="Trace not found for this user")
    return xray


class CounterfactualRequest(BaseModel):
    user_id: str
    events: List[Dict[str, Any]]


@router.post("/identity/counterfactual")
async def post_counterfactual(
    body: CounterfactualRequest,
    authorization: Optional[str] = Header(default=None),
):
    """What the system would conclude if these events had also happened.

    Reads the caller's real history, so it is gated like a read of that
    history. It writes nothing: the reasoning stages run and the result is
    discarded, which is the property that makes the question safe to ask.
    """
    enforce_user_match(authorization, body.user_id)
    from app.services.counterfactual import run_counterfactual

    return await run_counterfactual(body.user_id, body.events)


@router.get("/identity/space")
async def get_behaviour_space(
    user_id: str = Depends(resolve_user_id),
    limit: int = Query(default=600, le=600),
):
    """The stored embeddings of what this person watched, projected to 3D.

    PCA rather than t-SNE or UMAP: a map of someone that rearranges itself on
    every view would sit badly in a product arguing its reasoning reproduces.
    """
    from app.services.behaviour_space import build_space
    return await build_space(user_id, limit)


@router.get("/reasoning/lifecycle")
async def get_lifecycle(user_id: str = Depends(resolve_user_id)):
    """What is still current, what is fading, and what has been set aside.

    The six-state lifecycle had only ever produced two. State was written when
    a topic appeared in an ingest batch, and an abandoned topic never appears
    in one again, so nothing could retire it: 96 behaviours unseen for over a
    month were still labelled growing. It is evaluated as of now instead.
    """
    from app.services.lifecycle_view import build_lifecycle_view

    return await build_lifecycle_view(user_id)


@router.get("/identity/blind-spots")
async def get_blind_spots(user_id: str = Depends(resolve_user_id)):
    """Where this model is thin, separated by what kind of thin.

    The uncertainty map has been stored, indexed, read into the character
    runtime and injected into the language model's context since the schema was
    written, and never shown to the person it describes. It also conflated a
    measured uncertainty with a placeholder given to topics nothing had been
    concluded about, so "I have never considered this" reached the model as
    "I am highly uncertain about this".
    """
    from app.services.blind_spots import build_blind_spots

    return await build_blind_spots(user_id)


@router.get("/reasoning/contested")
async def get_contested_claims(
    user_id: str = Depends(resolve_user_id),
    limit: int = Query(default=40, le=100),
):
    """The claims this system's own evidence argues against.

    Every piece of evidence records the observations that contradict it as well
    as the ones that support it. Four layers computed, stored, indexed and read
    those contradictions back, and no surface ever showed them to the person
    they were about.

    Sorted by how contested a claim is rather than how confident, because a
    confident claim with a third of its evidence pointing the other way is the
    one worth a reader's attention, and every other view here already sorts by
    confidence.
    """
    from app.services.contested import build_contested

    return await build_contested(user_id, limit=limit)


@router.get("/identity/drift")
async def get_identity_drift(
    user_id: str = Depends(resolve_user_id),
    limit: int = Query(default=12, le=50),
):
    """How the model of this person moved, dimension by dimension.

    The architecture has always stored versioned snapshots and measured the
    distance between them; the figure lived in a log line and was never shown
    to the person it describes.
    """
    from app.services.identity_drift import build_drift
    return await build_drift(user_id, limit)


@router.get("/identity/self-model", response_model=Optional[dict])
async def get_self_model(user_id: str = Depends(resolve_user_id)):
    row = await fetchrow(
        "SELECT * FROM self_models WHERE user_id = $1", user_id
    )
    return dict(row) if row else None


@router.get("/reasoning/evidence", response_model=list)
async def get_evidence(
    user_id: str = Depends(resolve_user_id),
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
    user_id: str = Depends(resolve_user_id),
    limit: int = Query(default=50, le=200),
):
    rows = await fetch(
        """SELECT inference_id, inference_type, label, description,
                  confidence, importance, strength,
                  rule_name, claim_key, inferred_at::text
           FROM inferences WHERE user_id = $1
           ORDER BY confidence DESC LIMIT $2""",
        user_id, limit,
    )
    # Annotated, not filtered. This endpoint SHOWS the reasoning rather than
    # asserting it, so a claim the user denied stays visible and marked —
    # hiding it would make their own correction invisible and irreversible.
    # The surfaces that assert (chat, the character) exclude it instead.
    from app.services.calibration import annotate_contested
    return await annotate_contested(user_id, [dict(r) for r in rows])


@router.get("/reasoning/reflections", response_model=list)
async def get_reflections(
    user_id: str = Depends(resolve_user_id),
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
    user_id: str = Depends(resolve_user_id),
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
    user_id: str = Depends(resolve_user_id),
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
    return [_parse_json_fields(dict(r), ["errors"]) for r in rows]


@router.get("/query/traces/{trace_id}", response_model=Optional[dict])
async def get_trace_detail(trace_id: str, authorization: Optional[str] = Header(default=None)):
    row = await fetchrow(
        "SELECT * FROM pipeline_traces WHERE trace_id = $1", trace_id
    )
    if not row:
        return None
    enforce_user_match(authorization, row["user_id"])
    return _parse_json_fields(dict(row), ["errors", "trace_data"])


@router.get("/cognitive/metrics", response_model=list)
async def get_cognitive_metrics(
    user_id: str = Depends(resolve_user_id),
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
async def get_cognitive_summary(user_id: str = Depends(resolve_user_id)):
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
    platform_rows = await fetch(
        "SELECT platform, COUNT(*) as c FROM events WHERE user_id = $1 GROUP BY platform",
        user_id,
    )
    platform_breakdown = {r["platform"]: r["c"] for r in platform_rows}
    return {
        "user_id": user_id,
        "behavior_object_count": bo_count or 0,
        "evidence_count": ev_count or 0,
        "inference_count": inf_count or 0,
        "reflection_count": ref_count or 0,
        "snapshot_count": snap_count or 0,
        "trace_count": trace_count or 0,
        "current_identity": dict(last_identity) if last_identity else None,
        "platform_breakdown": platform_breakdown,
    }


# ═══════════════════════════════════════════════════════════
# NEW EXPLAINABILITY ENDPOINTS
# ═══════════════════════════════════════════════════════════

@router.get("/explain/{trace_id}")
async def explain_trace(trace_id: str, authorization: Optional[str] = Header(default=None)):
    """Assemble the full reasoning chain for a given trace."""
    trace = await fetchrow("SELECT * FROM pipeline_traces WHERE trace_id = $1", trace_id)
    if not trace:
        return {"error": "Trace not found"}
    trace = _parse_json_fields(dict(trace), ["errors", "trace_data"])
    user_id = trace["user_id"]
    enforce_user_match(authorization, user_id)

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

    # LLM data — provider/model come from the trace itself (set in
    # cognitive_pipeline/pipeline.py from the verbalizer's actual response),
    # never a hardcoded vendor name. "unknown" only for traces recorded
    # before these fields existed, not as a stand-in for a real answer.
    llm_data = trace_data.get("llm", {}) or {
        "provider": trace_data.get("provider") or "unknown",
        "model": trace_data.get("model") or "unknown",
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
async def explain_evidence_detail(evidence_id: str, authorization: Optional[str] = Header(default=None)):
    """Full evidence detail with linked objects."""
    ev = await fetchrow("SELECT * FROM evidence WHERE evidence_id = $1", evidence_id)
    if not ev:
        return {"error": "Evidence not found"}
    ev = _parse_json_fields(dict(ev), [
        "supporting_events", "supporting_behavior_objects", "metadata",
        "counter_evidence_ids", "conflicting_observations",
    ])
    user_id = ev["user_id"]
    enforce_user_match(authorization, user_id)

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
    snapshot = await fetchrow(
        "SELECT dominant_topics, identity_completeness, overall_confidence FROM identity_snapshots WHERE user_id = $1 ORDER BY snapshot_timestamp DESC LIMIT 1",
        user_id,
    )
    identity_traits = _parse_json_fields(dict(snapshot), ["dominant_topics"]) if snapshot else {}

    # This block used to read ev["supporting_evidence_ids"] - a column the
    # evidence table does not have - so "counter_evidence" was permanently [],
    # and it would have been the wrong content anyway: it looked up supporting
    # evidence and returned it under the name of its opposite.
    counter_ids = ev.get("counter_evidence_ids") or []
    counter_evidence = []
    if isinstance(counter_ids, list) and counter_ids:
        placeholders = ", ".join(f"${i+1}" for i in range(len(counter_ids)))
        counter_evidence = [
            dict(r) for r in await fetch(
                f"SELECT evidence_id, evidence_type, confidence, explanation FROM evidence WHERE evidence_id IN ({placeholders})",
                *counter_ids
            )
        ]

    # The observations that argue against this evidence are events, not other
    # evidence, so they are resolved here rather than left as bare ids. Showing
    # someone the reels they scrolled past is the whole point of recording them.
    conflicting_ids = []
    for raw in (ev.get("conflicting_observations") or []):
        try:
            conflicting_ids.append(int(raw))
        except (TypeError, ValueError):
            continue

    conflicting_observations = []
    if conflicting_ids:
        capped = conflicting_ids[:MAX_CONFLICTS_RETURNED]
        placeholders = ", ".join(f"${i+2}" for i in range(len(capped)))
        conflicting_observations = [
            dict(r) for r in await fetch(
                f"SELECT id, caption, username, watch_time, timestamp FROM events "
                f"WHERE user_id = $1 AND id IN ({placeholders}) ORDER BY watch_time ASC",
                user_id, *capped
            )
        ]

    return {
        "evidence": ev,
        "behavior_objects": behavior_objects,
        "inferences": [dict(r) for r in inferences],
        "identity_traits": identity_traits,
        "counter_evidence": counter_evidence,
        "conflicting_observations": conflicting_observations,
        "conflicting_total": len(conflicting_ids),
        "conflict_resolution": ev.get("conflict_resolution"),
        "net_confidence": ev.get("net_confidence"),
    }


@router.get("/explain/identity/{identity_id}")
async def explain_identity_detail(identity_id: str, authorization: Optional[str] = Header(default=None)):
    """Full identity breakdown with contribution analysis."""
    identity = await fetchrow("SELECT * FROM identities WHERE identity_id = $1", identity_id)
    if not identity:
        return {"error": "Identity not found"}
    identity = dict(identity)
    user_id = identity["user_id"]
    enforce_user_match(authorization, user_id)

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

    # What this identity is actually built from, by real row count — NOT a
    # weighting on how much each category influenced overall_confidence
    # (the pipeline doesn't compute per-category weights anywhere, so
    # presenting one here would just be inventing a number). Proportional
    # shares of real counts, normalized to sum to exactly 100.
    counts = {
        "behavior_objects": len(bo_list),
        "evidence": len(evidence_list),
        "reflections": len(reflections),
    }
    total_rows = sum(counts.values())
    if total_rows == 0:
        composition = {k: 0.0 for k in counts}
    else:
        composition = {k: round(v / total_rows * 100, 1) for k, v in counts.items()}
        diff = round(100 - sum(composition.values()), 1)
        if diff:
            largest = max(composition, key=composition.get)
            composition[largest] = round(composition[largest] + diff, 1)

    return {
        "identity": identity,
        "snapshots": snapshots,
        "evidence": evidence_list,
        "behavior_objects": bo_list,
        "reflections": reflections,
        "topics": topics,
        "grounding_composition": composition,
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
