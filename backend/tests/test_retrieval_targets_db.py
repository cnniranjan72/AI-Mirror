"""The retrieval context, against a real database.

test_retrieval_targets.py scans source, which cannot settle this: replacing
`ctx["memory"] = [...]` with `pass  # ctx["memory"] not served` leaves the
string in place and the scan passes. Assigning an empty list would defeat it
equally. Only loading the context and looking at it can tell.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.db.postgres import execute
from app.services import memory_store

pytestmark = pytest.mark.db

NOW = datetime.now(timezone.utc)


async def _seed(user_id: str) -> None:
    for i in range(8):
        await execute(
            "INSERT INTO events (user_id, reel_id, username, caption, hashtags, "
            "watch_time, timestamp, session_id, raw_metadata) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)",
            user_id, f"reel_{i}", "creator_cooking", "A video about cooking",
            json.dumps(["cooking"]), 55.0,
            NOW - timedelta(days=1, minutes=i), "s1", json.dumps({}),
        )
    await memory_store.remember(
        user_id=user_id, memory_type="semantic", subject="cooking",
        content="cooking recurs in this history", importance=0.9,
    )


@pytest.mark.asyncio
async def test_the_required_targets_are_actually_populated(db, disposable_user_id):
    """memory_question required `memory` and behavioral_question required
    `behavior_history`; neither key existed, so both failed a mandatory
    directive on every request."""
    await _seed(disposable_user_id)

    from cognitive_pipeline.pipeline import get_cognitive_pipeline

    ctx = await get_cognitive_pipeline()._load_retrieval_context(disposable_user_id)

    assert ctx.get("memory"), "memory_question's required source is empty"
    assert ctx.get("behavior_history"), "behavioral_question's required source is empty"
    assert ctx.get("creator_history"), "creator_history is empty"


@pytest.mark.asyncio
async def test_the_history_is_events_not_consolidated_objects(db, disposable_user_id):
    """Serving the target by duplicating behavior_objects would satisfy
    "populated" while adding nothing."""
    await _seed(disposable_user_id)

    from cognitive_pipeline.pipeline import get_cognitive_pipeline

    ctx = await get_cognitive_pipeline()._load_retrieval_context(disposable_user_id)
    first = ctx["behavior_history"][0]

    assert "reel_id" in first and "watch_time" in first
    assert "lifecycle_state" not in first, "this is a behaviour object, not an event"


@pytest.mark.asyncio
async def test_the_rows_convert_into_retrieved_objects(db, disposable_user_id):
    """The real requirement, and stricter than it first looked.

    An earlier version of this asserted json.dumps succeeded on every row.
    That is not what the system needs: every other retrieval source returns
    raw datetimes and the pipeline handles them, and casting timestamps to
    text to satisfy the assertion broke RetrievedObject, which validates
    them as datetimes. What does matter is that the rows convert.

    Decimal is the genuine outlier - avg() produces one, no other source
    does, and it reaches the prompt as a repr rather than a number.
    """
    from decimal import Decimal

    await _seed(disposable_user_id)

    from cognitive_pipeline.pipeline import get_cognitive_pipeline
    from rag.retriever import get_retriever

    ctx = await get_cognitive_pipeline()._load_retrieval_context(disposable_user_id)

    for key in ("memory", "behavior_history", "creator_history"):
        objects = get_retriever()._convert_to_retrieved(ctx[key], key)
        assert objects, key
        for row in ctx[key]:
            for field, value in row.items():
                assert not isinstance(value, Decimal), (key, field)


@pytest.mark.asyncio
async def test_the_two_intents_no_longer_fail_a_required_directive(db, disposable_user_id):
    await _seed(disposable_user_id)

    from cognitive_planning.planner_models import IntentPlan, UserIntentType
    from cognitive_planning.retrieval_planner import get_retrieval_planner
    from cognitive_pipeline.pipeline import get_cognitive_pipeline
    from rag.retriever import get_retriever

    ctx = await get_cognitive_pipeline()._load_retrieval_context(disposable_user_id)
    retriever = get_retriever()

    for name in ("memory_question", "behavioral_question"):
        plan = get_retrieval_planner().plan(
            IntentPlan(intent_type=UserIntentType(name), intent_confidence=0.9))

        saved = dict(retriever._data_sources)
        retriever._data_sources.clear()
        try:
            result = retriever.retrieve(plan=plan, context=ctx)
        finally:
            retriever._data_sources.update(saved)

        # No errors is the property that matters: the retriever records an
        # error only when a REQUIRED directive returns nothing, which is
        # exactly what these two intents did on every request. Total
        # fulfilment is not the bar - this account has never been through
        # the pipeline, so the optional behaviour-object and evidence
        # directives legitimately come back empty, as does runtime_state,
        # which is deliberately not served.
        assert not result.errors, f"{name}: {result.errors}"
        assert result.directives_fulfilled > 0, name

        # And specifically that the source which used to come back empty is
        # among what was retrieved, rather than the count being made up by the
        # directives that always worked.
        required_key = "memory" if name == "memory_question" else "behavior_history"
        served = {o.source_type for o in result.objects}
        assert required_key in served, f"{name} did not retrieve {required_key}"
