"""
Character API — the live state of the virtual character the chat actually
talks through, and how the RL loop is tuning its behavior. This is not a
separate model: it's the same character_core/character_state built by
RuntimeBuilder on every /query call (see cognitive_pipeline/pipeline.py).
This endpoint builds it on demand for inspection, so a viewer can see
exactly what the character "knows" right now.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import resolve_user_id
from app.services import rl_layer
from app.db.postgres import fetch, fetchrow

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/character/state")
async def get_character_state(user_id: str = Depends(resolve_user_id)):
    """Build the runtime (character_core + character_state) fresh and
    summarize it — identity snapshot version, self-model beliefs, active
    goals, inference/reflection counts. Offloaded to a thread since
    RuntimeBuilder does sync DB bridging internally (same pattern the
    cognitive pipeline uses)."""
    try:
        import asyncio
        from backend.character.runtime_builder import get_runtime_builder
        from backend.cognitive_pipeline.pipeline import get_cognitive_pipeline

        builder = get_runtime_builder()
        # RuntimeBuilder's snapshot manager only has an in-memory cache, so a
        # cold build (nothing queried yet this process) sees "no snapshot" even
        # though one exists in Postgres. The cognitive pipeline works around
        # this by loading the latest snapshot from DB first and passing it in
        # — reuse that exact loader here so this endpoint doesn't duplicate its
        # ~50 lines of row-to-model reconstruction.
        pipeline = get_cognitive_pipeline()
        identity_snapshot = await pipeline._load_latest_snapshot_from_db(user_id)
        recent_inferences = await pipeline._load_recent_inferences_from_db(user_id)
        recent_reflections = await pipeline._load_recent_reflections_from_db(user_id)
        identity_source_ids = await pipeline._load_identity_source_ids_from_db(user_id)

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: builder.build_runtime(
                user_id=user_id,
                identity_snapshot=identity_snapshot,
                recent_inferences=recent_inferences,
                recent_reflections=recent_reflections,
                identity_source_ids=identity_source_ids,
            ),
        )

        if not result.success or not result.character_core:
            return {
                "built": False,
                "errors": result.errors,
                "warnings": result.warnings,
            }

        core = result.character_core
        state = result.character_state

        return {
            "built": True,
            "core_id": core.core_id,
            "build_time_ms": round(result.build_time_ms, 2),
            "identity_snapshot": {
                "snapshot_id": core.identity_snapshot.snapshot_id,
                "version": core.get_snapshot_version(),
                "overall_confidence": core.identity_snapshot.overall_confidence,
                "identity_completeness": core.identity_snapshot.identity_completeness,
                "dominant_topics": core.get_dominant_topics(8),
            },
            "self_model": {
                "self_model_id": core.self_model.self_model_id,
                "overall_confidence": core.self_model.overall_confidence,
                "strong_beliefs": core.get_strong_beliefs(),
                "uncertain_beliefs": core.get_uncertain_beliefs(),
            },
            "memory": {
                "behavior_memory_count": len(core.behavior_memory_ids),
                "reflection_memory_count": len(core.reflection_memory_ids),
                "goal_memory_count": len(core.goal_memory_ids),
                "episodic_memory_count": len(core.episodic_memory_ids),
                "semantic_memory_count": len(core.semantic_memory_ids),
            },
            "inference_count": core.get_inference_count(),
            "state_summary": state.get_state_summary() if state else None,
            "state_valid": state.is_valid if state else None,
        }
    except Exception as e:
        logger.error(f"Error building character state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/character/activity")
async def get_character_activity(user_id: str = Depends(resolve_user_id), limit: int = Query(default=10)):
    """Recent turns the character has actually spoken through (query traces),
    proof this is the live thing being talked to, not a static profile."""
    rows = await fetch(
        "SELECT trace_id, query, intent_type, reasoning_mode, total_ms, "
        "snapshot_version, success, created_at::text "
        "FROM pipeline_traces WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
        user_id, limit,
    )
    return [dict(r) for r in rows]


@router.get("/character/learning-summary")
async def get_character_learning_summary(user_id: str = Depends(resolve_user_id)):
    """How the RL loop is currently steering the character's behavior —
    the learned policy plus the most recent action taken for this user."""
    policy = await rl_layer.get_policy()
    history = await rl_layer.get_action_history(user_id, limit=1)
    return {
        "policy_size": len(policy),
        "policy": policy,
        "last_action": history[0] if history else None,
    }
