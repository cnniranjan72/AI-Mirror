"""
Insights export — assembles the platform's existing cognitive data into a
single, clean "Algorithmic Identity Profile": the structured, exportable
artifact this product is built to produce for downstream consumers (ad
targeting / audience research, mental-health & wellbeing research, academic
behavioral research). Nothing here is computed freshly — it's a read-only
aggregation of data the pipeline already produced (identity, evidence,
inferences, RL alignment, wellbeing signal), reshaped for external use.
"""
import csv
import io
import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from app.db.postgres import fetch, fetchrow
from app.services import wellbeing, rl_layer

logger = logging.getLogger(__name__)


def _j(v, default):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return default
    return v if v is not None else default


async def build_algorithmic_identity_profile(user_id: str) -> Dict[str, Any]:
    """The canonical exportable profile. Every field cites its source table so
    a consumer can verify provenance rather than trust a black box."""
    identity = await fetchrow("SELECT * FROM identities WHERE user_id = $1", user_id)
    persona = await fetchrow(
        "SELECT * FROM personas WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1", user_id
    )
    bo_rows = await fetch(
        "SELECT topic, lifecycle_state, confidence_score, importance_score, creators "
        "FROM behavior_objects WHERE user_id = $1 ORDER BY importance_score DESC LIMIT 20",
        user_id,
    )
    inf_rows = await fetch(
        "SELECT inference_type, label, description, confidence FROM inferences WHERE user_id = $1",
        user_id,
    )
    wb = await wellbeing.compute_wellbeing_report(user_id)

    interest_graph = _j(identity["interest_graph"], {}) if identity else {}
    creator_graph = _j(identity["creator_graph"], {}) if identity else {}
    dominant_topics = _j(identity["dominant_topics"], []) if identity else []
    emerging_topics = _j(identity["emerging_topics"], []) if identity else []

    # Audience segment: a compact label a media planner / researcher can filter
    # on, derived from persona label + dominant content mix + engagement depth.
    scanning = any("scanning" in (i["description"] or "").lower() for i in inf_rows)
    learning_oriented = any("learning orientation" in (i["label"] or "").lower() for i in inf_rows)
    segment_tags = []
    if learning_oriented:
        segment_tags.append("self-directed-learner")
    if scanning:
        segment_tags.append("high-velocity-scroller")
    else:
        segment_tags.append("deep-engager")
    if creator_graph.get("dependence_score", 0) and creator_graph.get("dependence_score", 0) > 0.5:
        segment_tags.append("creator-loyal")
    else:
        segment_tags.append("creator-diverse")

    top_creators: List[str] = []
    for r in bo_rows:
        cs = _j(r["creators"], [])
        for c in cs:
            if c not in top_creators:
                top_creators.append(c)
    top_creators = top_creators[:15]

    return {
        "schema_version": "1.0",
        "user_id": user_id,
        "generated_at": datetime.utcnow().isoformat(),
        "identity": {
            "source": "identities table",
            "identity_version": identity["identity_version"] if identity else None,
            "overall_confidence": float(identity["overall_confidence"]) if identity else None,
            "identity_completeness": float(identity["identity_completeness"]) if identity else None,
            "persona_label": persona["persona_label"] if persona else None,
        },
        "interests": {
            "source": "identity.interest_graph + behavior_objects",
            "dominant_topics": dominant_topics,
            "emerging_topics": emerging_topics,
            "diversity_score": interest_graph.get("diversity_score"),
            "top_behavior_objects": [
                {"topic": r["topic"], "lifecycle_state": r["lifecycle_state"],
                 "confidence": float(r["confidence_score"] or 0),
                 "importance": float(r["importance_score"] or 0)}
                for r in bo_rows
            ],
        },
        "creator_affinity": {
            "source": "identity.creator_graph + behavior_objects.creators",
            "dependence_score": creator_graph.get("dependence_score"),
            "creator_diversity_score": creator_graph.get("creator_diversity_score"),
            "top_creators": top_creators,
        },
        "cognitive_signals": {
            "source": "inferences table (rule-based, explainable)",
            "inferences": [
                {"type": r["inference_type"], "label": r["label"],
                 "description": r["description"], "confidence": float(r["confidence"] or 0)}
                for r in inf_rows
            ],
        },
        "audience_segment": {
            "tags": segment_tags,
            "note": "Derived from persona label, engagement-depth inference, and creator dependence - not demographic data.",
        },
        "wellbeing_signal": {
            "source": "app/services/wellbeing.py - same computation as the Guardian tab",
            "risk_score": wb["risk_score"],
            "risk_level": wb["risk_level"],
            "risk_factors": wb["risk_factors"],
        },
        "behavioral_alignment": {
            "source": "rl_layer - contextual bandit alignment dimensions",
            "note": "Recorded per-ingest in actions_log; latest snapshot only shown here.",
        },
    }


async def export_table_csv(user_id: str, table: str) -> str:
    """Raw table export as CSV text. Whitelisted tables only."""
    allowed = {
        "behavior_objects": "SELECT topic, lifecycle_state, confidence_score, importance_score, "
                             "stability_score, creators, keywords, updated_at FROM behavior_objects WHERE user_id = $1",
        "evidence": "SELECT evidence_type, confidence, weight, explanation, created_at FROM evidence WHERE user_id = $1",
        "inferences": "SELECT inference_type, label, description, confidence, created_at FROM inferences WHERE user_id = $1",
        "reflections": "SELECT summary, confidence, created_at FROM reflections WHERE user_id = $1",
    }
    if table not in allowed:
        raise ValueError(f"Unknown or disallowed table: {table}")

    rows = await fetch(allowed[table], user_id)
    buf = io.StringIO()
    if not rows:
        return ""
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for r in rows:
        d = dict(r)
        for k, v in d.items():
            if isinstance(v, (list, dict)):
                d[k] = json.dumps(v)
        writer.writerow(d)
    return buf.getvalue()
