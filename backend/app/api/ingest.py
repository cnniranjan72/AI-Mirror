"""
POST /ingest — V3 Pipeline Integration

The SINGLE entry point for all event ingestion.
Every event now traverses:
  BehaviorGateway → KnowledgeConsolidation → BehaviorObjects
  → Evidence → Inference → Identity → Snapshot → SelfModel

Legacy V2 Persona is replaced by Identity + PersonaAdapter.
"""
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from backend.core.behavior_gateway import get_behavior_gateway
from backend.shared.contracts import BehaviorEvent, EventSource
from pipeline.orchestrator import V3Pipeline

from app.services import (
    enrichment,
    expansion,
    embedding as emb,
    vector_store,
    feature_engineering,
    rl_layer,
)
from app.services.persona_adapter import identity_to_persona
from app.db.postgres import fetchrow, execute
from backend.providers import get_provider_manager

logger = logging.getLogger(__name__)
router = APIRouter()

_v3_pipeline: Optional[V3Pipeline] = None


def get_v3_pipeline() -> V3Pipeline:
    global _v3_pipeline
    if _v3_pipeline is None:
        _v3_pipeline = V3Pipeline()
    return _v3_pipeline


class EventItem(BaseModel):
    reel_id: str
    username: str = "unknown"
    caption: str = ""
    hashtags: List[str] = Field(default_factory=list)
    audio: str = ""            # legacy field name
    audio_info: str = ""       # current extension field name
    audio_id: str = ""
    watch_time: float = 0
    # Engagement signal captured by the extension from the DOM.
    liked: bool = False
    saved: bool = False
    shared: bool = False
    commented: bool = False
    following: bool = True
    profile_url: str = ""
    # Content-popularity counts (nullable — Instagram frequently hides them).
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    repost_count: Optional[int] = None
    timestamp: str = ""
    session_id: str = ""
    source_url: str = ""
    # Multi-platform (V10). Defaults keep the Instagram extension unchanged.
    platform: str = "instagram"            # instagram | youtube
    surface: str = ""                      # youtube: "watch" | "shorts"
    video_length: Optional[float] = None   # seconds; YouTube exposes this, IG does not


class IngestRequest(BaseModel):
    user_id: str = "default"
    events: List[EventItem]


class ExtractRequest(BaseModel):
    url: str
    prompt: Optional[str] = None


class ExtractResponse(BaseModel):
    success: bool
    content_id: str
    title: Optional[str] = None
    caption: Optional[str] = None
    hashtags: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    intent: Optional[str] = None
    sentiment: Optional[str] = None
    confidence: float = 0
    provider: str = ""
    error: Optional[str] = None


class IngestResponse(BaseModel):
    success: bool
    events_stored: int
    embeddings_created: int
    persona_label: Optional[str] = None
    identity_version: Optional[int] = None
    confidence: Optional[float] = None
    alignment_score: Optional[float] = None
    message: str


async def record_cognitive_metrics(user_id: str, v3_result):
    try:
        from app.db.postgres import execute as db_execute
        metrics = [
            ("behavior_object_count", len(v3_result.behavior_objects) if v3_result.behavior_objects else 0, {"type": "pipeline"}),
            ("evidence_count", len(v3_result.evidence) if v3_result.evidence else 0, {"type": "pipeline"}),
            ("inference_count", len(v3_result.inferences) if v3_result.inferences else 0, {"type": "pipeline"}),
            ("identity_version", v3_result.identity.identity_version if v3_result.identity else 0, {"type": "identity"}),
            ("identity_confidence", v3_result.identity.overall_confidence if v3_result.identity else 0, {"type": "identity"}),
        ]
        for name, value, tags in metrics:
            await db_execute(
                """
                INSERT INTO cognitive_metrics (user_id, metric_name, metric_value, metric_tags)
                VALUES ($1, $2, $3, $4::jsonb)
                """,
                user_id, name, value, json.dumps(tags),
            )
    except Exception as e:
        logger.warning(f"Failed to record metrics: {e}")


async def cleanup_old_snapshots(user_id: str, keep_count: int = 20):
    try:
        from app.db.postgres import execute as db_execute
        await db_execute(
            """
            DELETE FROM identity_snapshots
            WHERE user_id = $1 AND snapshot_id NOT IN (
                SELECT snapshot_id FROM identity_snapshots
                WHERE user_id = $1
                ORDER BY snapshot_timestamp DESC
                LIMIT $2
            )
            """,
            user_id, keep_count,
        )
    except Exception as e:
        logger.warning(f"Snapshot cleanup failed: {e}")


@router.post("/ingest", response_model=IngestResponse)
async def ingest_events(req: IngestRequest, background_tasks: BackgroundTasks):
    """
    V3 Pipeline: Extension → BehaviorGateway → KnowledgeConsolidation
    → BehaviorObjects → Evidence → Inference → Identity → Snapshot → SelfModel

    Backward-compatible: Persona derived from Identity via PersonaAdapter.
    Legacy: V2 services (embedding, vector_store, RL) still run alongside.
    """
    if not req.events:
        raise HTTPException(status_code=400, detail="No events provided")

    user_id = req.user_id
    stored_count = 0
    embed_count = 0
    normalized_events = []

    try:
        # ── STEP 1: Behavior Gateway (normalize all events) ──
        gateway = get_behavior_gateway()
        for ev in req.events:
            raw_payload = {
                "events": [{
                    "reel_id": ev.reel_id,
                    "username": ev.username,
                    "caption": ev.caption,
                    "hashtags": ev.hashtags,
                    # Prefer the current field name, fall back to the legacy one.
                    "audio_info": ev.audio_info or ev.audio,
                    "audio_id": ev.audio_id,
                    "watch_time": ev.watch_time,
                    "liked": ev.liked,
                    "saved": ev.saved,
                    "shared": ev.shared,
                    "commented": ev.commented,
                    "following": ev.following,
                    "profile_url": ev.profile_url,
                    "timestamp": ev.timestamp or datetime.now(timezone.utc).isoformat(),
                    "session_id": ev.session_id,
                    "source_url": ev.source_url or "",
                    "platform": ev.platform,
                    "surface": ev.surface,
                }]
            }
            batch_events = gateway.process_batch(raw_payload, EventSource.CHROME_EXTENSION)
            normalized_events.extend(batch_events)

        if not normalized_events:
            raise HTTPException(status_code=400, detail="No valid events after normalization")

        logger.info(f"Normalized {len(normalized_events)} events via BehaviorGateway")

        # ── STEP 2: Store raw events to database ──
        texts_to_embed = []
        metadatas = []
        event_dicts = []

        # Idempotency: a batch can be re-sent (the extension re-buffers events on
        # a failed/uncertain send). Skip events already stored, and intra-batch
        # duplicates, keyed by (reel_id, session_id, timestamp) — a genuine
        # re-watch has a different timestamp and is still stored.
        seen_keys = set()
        skipped_dupes = 0

        for i, bev in enumerate(normalized_events):
            raw_ev = req.events[min(i, len(req.events) - 1)]

            dedup_key = (bev.content_id, bev.session_id, str(bev.timestamp))
            if dedup_key in seen_keys:
                skipped_dupes += 1
                continue
            seen_keys.add(dedup_key)
            already = await fetchrow(
                "SELECT 1 FROM events WHERE user_id=$1 AND reel_id=$2 "
                "AND session_id=$3 AND timestamp=$4 LIMIT 1",
                user_id, bev.content_id, bev.session_id, bev.timestamp,
            )
            if already:
                skipped_dupes += 1
                continue

            row = await fetchrow(
                """
                INSERT INTO events (user_id, reel_id, username, caption, hashtags,
                                    audio, watch_time, timestamp, session_id,
                                    liked, saved, shared, commented, following,
                                    audio_id, profile_url,
                                    like_count, comment_count, repost_count,
                                    platform, surface)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9,
                        $10, $11, $12, $13, $14, $15, $16, $17, $18, $19,
                        $20, $21)
                RETURNING id
                """,
                user_id,
                bev.content_id,
                bev.creator,
                bev.caption or "",
                json.dumps(bev.hashtags),
                bev.audio_info,
                bev.watch_time,
                bev.timestamp,
                bev.session_id,
                bool(raw_ev.liked),
                bool(raw_ev.saved),
                bool(raw_ev.shared),
                bool(raw_ev.commented),
                bool(raw_ev.following),
                raw_ev.audio_id or "",
                raw_ev.profile_url or "",
                raw_ev.like_count,
                raw_ev.comment_count,
                raw_ev.repost_count,
                raw_ev.platform,
                raw_ev.surface,
            )
            event_id = row["id"]
            stored_count += 1

            # Content Intelligence (still needed for expansion/embeddings)
            enriched = enrichment.enrich(bev.caption or "", bev.hashtags)
            expanded_text = expansion.expand(bev.caption or "", bev.hashtags, enriched)

            texts_to_embed.append(expanded_text)
            metadatas.append({
                "event_id": event_id,
                "reel_id": bev.content_id,
                "username": bev.creator,
                "watch_time": bev.watch_time,
                "session_id": bev.session_id,
                "topics": enriched.get("topics", []),
                "sentiment": enriched.get("sentiment", "neutral"),
                "intent": enriched.get("intent", "entertainment"),
            })

            event_dicts.append({
                "reel_id": bev.content_id,
                "username": bev.creator,
                "caption": bev.caption,
                "hashtags": bev.hashtags,
                "watch_time": bev.watch_time,
                "session_id": bev.session_id,
            })

        if skipped_dupes:
            logger.info(f"Skipped {skipped_dupes} duplicate event(s) (idempotency)")

        # ── STEP 2.5: URL-based content enrichment (if source_url provided) ──
        for ev in req.events:
            url = (ev.source_url or "").strip()
            if not url:
                continue
            try:
                pm = get_provider_manager()
                extracted = await pm.extract_content(url)
                if extracted and extracted.confidence > 0.3:
                    # Find the corresponding normalized event
                    for bev in normalized_events:
                        if bev.content_id == ev.reel_id:
                            if extracted.caption and not bev.caption:
                                bev.caption = extracted.caption
                            if extracted.hashtags:
                                existing_tags = set(t.lower() for t in bev.hashtags)
                                for tag in extracted.hashtags:
                                    if tag.lower() not in existing_tags:
                                        bev.hashtags.append(tag)
                                        existing_tags.add(tag.lower())
                            if extracted.topics:
                                bev.raw_metadata["extracted_topics"] = extracted.topics
                            if extracted.creator and not bev.creator:
                                bev.creator = extracted.creator
                            bev.raw_metadata["content_extracted"] = True
                            bev.raw_metadata["extraction_provider"] = extracted.provider
                            bev.raw_metadata["extraction_confidence"] = extracted.confidence
                            logger.info(f"URL enrichment for {ev.reel_id} from {url}: topics={extracted.topics}")
                            break
            except Exception as e:
                logger.warning(f"URL enrichment failed for {url}: {e}")

        # ── STEP 3: Generate embeddings (for vector search) ──
        if texts_to_embed:
            embeddings = emb.encode_batch(texts_to_embed)
            embed_count = await vector_store.insert_embeddings_batch(
                user_id=user_id,
                texts=texts_to_embed,
                embeddings=embeddings,
                doc_type="event",
                metadatas=metadatas,
            )

        # ── STEP 4: Run V3 Pipeline (Identity replaces Persona) ──
        pipeline = get_v3_pipeline()
        existing_identity = await pipeline.load_identity(user_id)

        v3_result = await pipeline.run(
            user_id=user_id,
            events=normalized_events,
            existing_identity=existing_identity,
        )

        # ── STEP 5: Create Persona from Identity (backward compatibility) ──
        persona_data = None
        if v3_result.identity:
            persona_data = identity_to_persona(v3_result.identity)
            await save_persona_from_adapter(user_id, persona_data)

        # ── STEP 6: V2 services still run alongside (for dashboard compat) ──
        features = feature_engineering.compute_features(event_dicts)

        # Store behavioral summary embedding
        if features["summary_text"]:
            summary_vec = emb.encode(features["summary_text"])
            await vector_store.insert_embedding(
                user_id=user_id,
                text=features["summary_text"],
                embedding=summary_vec,
                doc_type="behavioral_summary",
                metadata={"source": "feature_engineering", "event_count": len(event_dicts)},
            )

        # ── STEP 7: RL contextual bandit (learns from alignment improvement) ──
        persona_for_rl = persona_data or _empty_persona()
        alignment = rl_layer.compute_alignment(persona_for_rl, features)

        # Close the loop: reward the PREVIOUS suggestion by how much alignment
        # has changed since it was made, updating the policy's Q-values.
        learn_result = await rl_layer.learn_from_transition(user_id, alignment["overall_score"])
        if learn_result:
            logger.info("RL learned: %s", learn_result)

        suggestion = await rl_layer.suggest_action(alignment, features)

        # Log the new action with the context + baseline alignment so the NEXT
        # ingest can compute this action's reward.
        log_state = dict(alignment["state"])
        log_state["alignment_before"] = alignment["overall_score"]
        log_state["context_key"] = suggestion["context_key"]
        await rl_layer.log_action(
            user_id=user_id,
            action_type=suggestion["action"]["action_id"],
            action_data=suggestion["action"],
            state=log_state,
            reward=suggestion["expected_reward"],
        )

        # Background: record metrics and cleanup old snapshots
        background_tasks.add_task(record_cognitive_metrics, user_id, v3_result)
        background_tasks.add_task(cleanup_old_snapshots, user_id)

        # Build response
        identity_version = v3_result.identity.identity_version if v3_result.identity else None
        confidence = v3_result.identity.overall_confidence if v3_result.identity else None

        return IngestResponse(
            success=True,
            events_stored=stored_count,
            embeddings_created=embed_count,
            persona_label=persona_data["persona_label"] if persona_data else None,
            identity_version=identity_version,
            confidence=confidence,
            alignment_score=alignment["overall_score"],
            message=(
                f"V3 pipeline: {stored_count} events → "
                f"{len(v3_result.behavior_objects)} behavior objects → "
                f"{len(v3_result.evidence)} evidence → "
                f"{len(v3_result.inferences)} inferences → "
                f"identity v{identity_version}"
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Ingest pipeline failed")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@router.post("/extract", response_model=ExtractResponse)
async def extract_content(req: ExtractRequest):
    """
    Extract structured content from a URL using ScrapeGraphAI.
    Uses LLM-powered SmartScraperGraph to extract:
    title, caption, hashtags, topics, intent, sentiment, creator.
    """
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    try:
        pm = get_provider_manager()
        result = await pm.extract_content(url=req.url, prompt=req.prompt)

        return ExtractResponse(
            success=result.confidence > 0.3,
            content_id=result.content_id,
            title=result.title,
            caption=result.caption,
            hashtags=result.hashtags,
            topics=result.topics,
            intent=result.intent,
            sentiment=result.sentiment,
            confidence=result.confidence,
            provider=result.provider,
        )

    except Exception as e:
        logger.exception("Content extraction failed")
        return ExtractResponse(
            success=False,
            content_id="",
            error=str(e),
        )


async def save_persona_from_adapter(user_id: str, persona: Dict[str, Any]):
    """Save identity-derived persona to personas table for backward compat"""
    try:
        await execute(
            """
            INSERT INTO personas (user_id, interest_vector, behavior_vector,
                                  persona_label, traits, strengths, weaknesses,
                                  recommendations, confidence)
            VALUES ($1, $2::jsonb, $3::jsonb, $4, $5::jsonb, $6::jsonb, $7::jsonb, $8::jsonb, $9)
            """,
            user_id,
            json.dumps(persona["interest_vector"]),
            json.dumps(persona["behavior_vector"]),
            persona["persona_label"],
            json.dumps(persona["traits"]),
            json.dumps(persona["strengths"]),
            json.dumps(persona["weaknesses"]),
            json.dumps(persona["recommendations"]),
            persona["confidence"],
        )
    except Exception as e:
        logger.warning(f"Could not save persona adapter data: {e}")


def _empty_persona() -> Dict[str, Any]:
    return {
        "persona_label": "Emerging User",
        "traits": {"attention_score": 0, "engagement_score": 0, "content_diversity": 0, "curiosity_score": 0},
        "interest_vector": {"top_topics": [], "topic_count": 0},
        "behavior_vector": {"avg_watch_time": 0, "total_watch_time": 0, "total_events": 0, "top_creators": []},
        "strengths": [],
        "weaknesses": [],
        "recommendations": [],
        "confidence": 0,
    }
