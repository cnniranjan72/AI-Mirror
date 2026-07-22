"""
Data Sources — Retriever DB Loaders

Registers DB query functions on the Retriever for each RetrievalTarget.
Each loader queries the appropriate V3 table and returns dict/list data.
Architecture V3 — FROZEN. No redesign.
"""
import logging
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from backend.cognitive_planning.planner_models import RetrievalTarget
from backend.rag.retriever import get_retriever

logger = logging.getLogger(__name__)


def _run_sync_db_query(sql: str, *args) -> List[Dict[str, Any]]:
    """Execute a DB query synchronously via asyncio run_coroutine_threadsafe."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            from app.db.postgres import fetch
            return asyncio.run_coroutine_threadsafe(
                fetch(sql, *args), loop
            ).result(timeout=10)
    except Exception as e:
        logger.debug(f"DB query failed: {e}")
    return []


def _loader_behavior_objects(
    target: RetrievalTarget,
    max_results: int = 20,
    filter_topics: Optional[List[str]] = None,
    filter_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    rows = _run_sync_db_query(
        "SELECT * FROM behavior_objects WHERE user_id = $1 ORDER BY updated_at DESC LIMIT $2",
        "test_user", max_results
    )
    results = []
    for row in rows:
        d = dict(row)
        for key in ("evidence_references", "hashtags", "related_topics"):
            if isinstance(d.get(key), str):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
            elif d.get(key) is None:
                d[key] = []
        results.append(d)
    return results


def _loader_evidence(
    target: RetrievalTarget,
    max_results: int = 20,
    filter_topics: Optional[List[str]] = None,
    filter_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    rows = _run_sync_db_query(
        "SELECT * FROM evidence WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
        "test_user", max_results
    )
    results = []
    for row in rows:
        d = dict(row)
        for key in ("supporting_behavior_objects", "supporting_evidence_ids", "metadata"):
            if isinstance(d.get(key), str):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
            elif d.get(key) is None:
                d[key] = [] if key != "metadata" else {}
        results.append(d)
    return results


def _loader_identity_snapshot(
    target: RetrievalTarget,
    max_results: int = 1,
    filter_topics: Optional[List[str]] = None,
    filter_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    rows = _run_sync_db_query(
        "SELECT * FROM identity_snapshots WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
        "test_user"
    )
    results = []
    for row in rows:
        d = dict(row)
        for key in ("dominant_topics", "emerging_topics", "interest_graph", "personality_traits"):
            if isinstance(d.get(key), str):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
            elif d.get(key) is None:
                d[key] = [] if key != "interest_graph" and key != "personality_traits" else {}
        results.append(d)
    return results


def _loader_self_model(
    target: RetrievalTarget,
    max_results: int = 1,
    filter_topics: Optional[List[str]] = None,
    filter_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    rows = _run_sync_db_query(
        "SELECT * FROM self_models WHERE user_id = $1 ORDER BY updated_at DESC LIMIT 1",
        "test_user"
    )
    results = []
    for row in rows:
        d = dict(row)
        for key in ("beliefs", "strong_beliefs", "uncertain_beliefs", "metadata"):
            if isinstance(d.get(key), str):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
            elif d.get(key) is None:
                d[key] = [] if key != "uncertainty_map" else {}
        results.append(d)
    return results


def _loader_goals(
    target: RetrievalTarget,
    max_results: int = 10,
    filter_topics: Optional[List[str]] = None,
    filter_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    rows = _run_sync_db_query(
        "SELECT * FROM goals WHERE user_id = $1 AND goal_status = 'active' ORDER BY priority ASC, created_at DESC LIMIT $2",
        "test_user", max_results
    )
    results = []
    for row in rows:
        d = dict(row)
        for key in ("milestones", "metadata"):
            if isinstance(d.get(key), str):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
            elif d.get(key) is None:
                d[key] = [] if key != "metadata" else {}
        results.append(d)
    return results


def _loader_reflections(
    target: RetrievalTarget,
    max_results: int = 10,
    filter_topics: Optional[List[str]] = None,
    filter_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    rows = _run_sync_db_query(
        "SELECT * FROM reflections WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
        "test_user", max_results
    )
    results = []
    for row in rows:
        d = dict(row)
        for key in ("source_evidence_ids", "source_inference_ids", "metadata"):
            if isinstance(d.get(key), str):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
            elif d.get(key) is None:
                d[key] = [] if key != "metadata" else {}
        results.append(d)
    return results


def _loader_inferences(
    target: RetrievalTarget,
    max_results: int = 20,
    filter_topics: Optional[List[str]] = None,
    filter_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    rows = _run_sync_db_query(
        "SELECT * FROM inferences WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
        "test_user", max_results
    )
    results = []
    for row in rows:
        d = dict(row)
        for key in ("source_evidence_ids", "source_inference_ids", "metadata"):
            if isinstance(d.get(key), str):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
            elif d.get(key) is None:
                d[key] = [] if key != "metadata" else {}
        results.append(d)
    return results


def register_data_sources(user_id: str = "test_user"):
    """Register all DB data sources on the Retriever singleton."""
    import functools
    retriever = get_retriever()

    loader_map = {
        RetrievalTarget.BEHAVIOR_OBJECTS: _loader_behavior_objects,
        RetrievalTarget.EVIDENCE: _loader_evidence,
        RetrievalTarget.IDENTITY_SNAPSHOT: _loader_identity_snapshot,
        RetrievalTarget.SELF_MODEL: _loader_self_model,
        RetrievalTarget.GOALS: _loader_goals,
        RetrievalTarget.REFLECTIONS: _loader_reflections,
        RetrievalTarget.INFERENCES: _loader_inferences,
    }

    for target, loader in loader_map.items():
        retriever.register_source(target, loader)

    logger.info(f"Registered {len(loader_map)} data sources on Retriever")
