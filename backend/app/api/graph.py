"""
GET /graph/knowledge — a force-directed graph of the topics and creators
that actually make up a user's behavior_objects. Not a decorative layout:
node size/confidence and platform mix come straight from real scores, and
edges are real relationships (topic -> creator co-occurrence, topic <->
topic keyword/subtopic overlap) rather than a synthetic/random layout.
"""
import json
import logging
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import resolve_user_id
from app.db.postgres import fetch

logger = logging.getLogger(__name__)
router = APIRouter()


def _parse_json(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


@router.get("/graph/knowledge")
async def get_knowledge_graph(user_id: str = Depends(resolve_user_id)):
    rows = await fetch(
        "SELECT unique_id, topic, subtopics, keywords, creators, importance_score, "
        "confidence_score, lifecycle_state, supporting_event_ids "
        "FROM behavior_objects WHERE user_id = $1",
        user_id,
    )
    if not rows:
        return {"nodes": [], "links": []}

    parsed = []
    all_event_ids = set()
    for r in rows:
        d = dict(r)
        d["subtopics"] = _parse_json(d["subtopics"]) or []
        d["keywords"] = _parse_json(d["keywords"]) or []
        d["creators"] = _parse_json(d["creators"]) or []
        d["supporting_event_ids"] = _parse_json(d["supporting_event_ids"]) or []
        parsed.append(d)
        for eid in d["supporting_event_ids"]:
            try:
                all_event_ids.add(int(eid))
            except (TypeError, ValueError):
                continue

    # Platform lookup, event-id based: only newly-linked (numeric) event ids
    # resolve this way — older evt_xxxx-linked behavior objects (from before
    # ingest.py/seed.py started setting BehaviorEvent.event_id to the real
    # Postgres id) don't have a usable id here at all.
    platform_by_event = {}
    if all_event_ids:
        ids = list(all_event_ids)
        placeholders = ", ".join(f"${i + 1}" for i in range(len(ids)))
        ev_rows = await fetch(f"SELECT id, platform FROM events WHERE id IN ({placeholders})", *ids)
        platform_by_event = {r["id"]: r["platform"] for r in ev_rows}

    # Fallback platform lookup, creator-based: for the legacy evt_xxxx objects
    # above, fall back to the platform(s) their real creators actually posted
    # on. Only safe because it's deterministic in practice: every username in
    # this user's events maps to exactly one platform (verified live), so this
    # is a real fact about the account's data, not a guess.
    creator_rows = await fetch(
        "SELECT DISTINCT username, platform FROM events WHERE user_id = $1 AND username IS NOT NULL",
        user_id,
    )
    platform_by_username = defaultdict(set)
    for r in creator_rows:
        platform_by_username[r["username"]].add(r["platform"])

    nodes = []
    links = []
    creator_topic_count = defaultdict(int)
    creator_platforms = defaultdict(set)

    for d in parsed:
        platforms = set()
        for eid in d["supporting_event_ids"]:
            try:
                p = platform_by_event.get(int(eid))
            except (TypeError, ValueError):
                p = None
            if p:
                platforms.add(p)
        if not platforms:
            for creator in d["creators"]:
                platforms |= platform_by_username.get(creator, set())

        topic_id = f"topic:{d['unique_id']}"
        nodes.append({
            "id": topic_id,
            "label": d["topic"],
            "group": "topic",
            "importance": round(d["importance_score"] or 0, 3),
            "confidence": round(d["confidence_score"] or 0, 3),
            "lifecycle": d["lifecycle_state"],
            "platforms": sorted(platforms),
            "keywords": d["keywords"][:6],
            "event_count": len(d["supporting_event_ids"]),
        })

        for creator in d["creators"][:8]:
            if not creator:
                continue
            cid = f"creator:{creator}"
            creator_topic_count[cid] += 1
            # A creator's own platform is unambiguous from their username,
            # independent of which platforms the topic as a whole spans.
            creator_platforms[cid] |= (platform_by_username.get(creator) or platforms)
            links.append({"source": topic_id, "target": cid, "kind": "creates"})

    for cid, count in creator_topic_count.items():
        nodes.append({
            "id": cid,
            "label": cid.split(":", 1)[1],
            "group": "creator",
            "topic_count": count,
            "platforms": sorted(creator_platforms[cid]),
        })

    # Topic <-> topic edges: real overlap in keywords/subtopics, not a random layout.
    for i, a in enumerate(parsed):
        a_terms = set(w.lower() for w in (a["keywords"] + a["subtopics"]) if w)
        if not a_terms:
            continue
        for b in parsed[i + 1:]:
            b_terms = set(w.lower() for w in (b["keywords"] + b["subtopics"]) if w)
            shared = a_terms & b_terms
            if len(shared) >= 2:
                links.append({
                    "source": f"topic:{a['unique_id']}",
                    "target": f"topic:{b['unique_id']}",
                    "kind": "related",
                    "weight": len(shared),
                })

    return {"nodes": nodes, "links": links}
