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

from fastapi import APIRouter, BackgroundTasks, File, Form, Header, HTTPException, UploadFile, Depends
from pydantic import BaseModel, Field

from app.api.deps import enforce_write_match
from app.core.error_tracking import record_error
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
from app.services import archive_import
from app.db.postgres import fetchrow, execute, execute as db_execute
from backend.providers import get_provider_manager
from app.core.rate_limit import ingest_rate_limit, import_rate_limit
from app.services import collection_control

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


class ExtractionWarning(BaseModel):
    type: str = "extraction_failed"
    platform: str = ""
    surface: str = ""
    content_id: str = ""
    tier: Optional[int] = None
    timestamp: str = ""


class IngestRequest(BaseModel):
    user_id: str = "default"
    events: List[EventItem]
    # Extraction failures the content script already decided to drop (e.g. a
    # stale DOM selector after YouTube changes its markup) — recorded so the
    # failure is visible (GET /admin/errors) instead of only a console.log
    # that disappears the moment the tab closes.
    warnings: List[ExtractionWarning] = Field(default_factory=list)


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
        # A pinned snapshot is exempt. Someone who has gone back to an earlier
        # version of their model is standing on exactly the row this would
        # otherwise delete once twenty newer ones exist, and the pin would then
        # dangle - reads falling back to the newest, which is the opposite of
        # what they asked for.
        await db_execute(
            """
            DELETE FROM identity_snapshots
            WHERE user_id = $1 AND snapshot_id NOT IN (
                SELECT snapshot_id FROM identity_snapshots
                WHERE user_id = $1
                ORDER BY snapshot_timestamp DESC
                LIMIT $2
            )
            AND snapshot_id NOT IN (
                SELECT snapshot_id FROM identity_pins WHERE user_id = $1
            )
            """,
            user_id, keep_count,
        )
    except Exception as e:
        logger.warning(f"Snapshot cleanup failed: {e}")


@router.post("/ingest", response_model=IngestResponse, dependencies=[Depends(ingest_rate_limit)])
async def ingest_events(
    req: IngestRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(default=None),
):
    """
    V3 Pipeline: Extension → BehaviorGateway → KnowledgeConsolidation
    → BehaviorObjects → Evidence → Inference → Identity → Snapshot → SelfModel

    Backward-compatible: Persona derived from Identity via PersonaAdapter.
    Legacy: V2 services (embedding, vector_store, RL) still run alongside.
    """
    enforce_write_match(authorization, req.user_id)

    # The switch is enforced here rather than in the extension or the
    # dashboard. Anywhere else it would be a request, not a guarantee: anything
    # holding the user_id could keep posting. Checked before any write, and
    # reported rather than silently dropped, so the caller can tell the
    # difference between "stored" and "refused".
    if await collection_control.is_paused(req.user_id):
        return IngestResponse(
            success=True,
            events_stored=0,
            embeddings_created=0,
            message="Collection is paused for this account. No events were stored.",
        )

    if req.warnings:
        for w in req.warnings:
            background_tasks.add_task(
                record_error,
                Exception(f"Extension extraction failed: {w.platform}/{w.surface} {w.content_id} (tier {w.tier})"),
                user_id=req.user_id,
                error_type="extension_extraction_failed",
                message=f"{w.platform} {w.content_id}: extraction failed, event dropped (tier {w.tier})",
            )

    if not req.events:
        if req.warnings:
            return IngestResponse(success=True, events_stored=0, embeddings_created=0, message="No events (warnings recorded)")
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
            # Pipeline stages (behavior_objects.supporting_event_ids, evidence.supporting_events,
            # memories.source_event_ids) key off bev.event_id — it arrives as a random evt_xxxx
            # from the normalizer with no link back to this row. Overwrite it with the real
            # Postgres id so downstream clustering can be traced back to a specific event (the
            # Timeline endpoint's reverse-index depends on this).
            bev.event_id = str(event_id)

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
            embeddings = await emb.encode_batch(texts_to_embed)
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
            summary_vec = await emb.encode(features["summary_text"])
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


class ArchiveImportResponse(BaseModel):
    success: bool
    events_found: int
    events_stored: int
    sources: Dict[str, int] = Field(default_factory=dict)
    duplicates_removed: int = 0
    skipped_files: int = 0
    truncated: bool = False
    profile_claims_imported: int = 0
    search_signals_imported: int = 0
    identity_version: Optional[int] = None
    confidence: Optional[float] = None
    message: str


@router.post("/import/archive", response_model=ArchiveImportResponse, dependencies=[Depends(import_rate_limit)])
async def import_archive(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form("default"),
    authorization: Optional[str] = Header(default=None),
):
    """Import an official platform data export (Instagram DYI / Google Takeout).

    Deliberately delegates to ingest_events rather than driving the pipeline
    itself: a second ingestion path would be a second place for enrichment,
    embedding, identity evolution and RL to drift out of step. Everything this
    endpoint does is parse bytes into the same EventItem list the extension
    posts.
    """
    enforce_write_match(authorization, user_id)

    raw = await file.read()
    try:
        parsed = archive_import.parse_archive(raw, file.filename or "export.zip")
    except archive_import.ArchiveImportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Archive import failed: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=f"Could not read this export: {e}")

    # Persist what the PLATFORM claims about this user, kept in its own table
    # and never fed to the pipeline — the twin has to stay an independent
    # model, or it would end up confirming whatever it was told.
    claims = parsed.get("profile_claims") or []
    claims_stored = 0
    if claims:
        try:
            platforms = {c["platform"] for c in claims}
            for platform in platforms:
                # Re-importing an export refreshes that platform's claim set
                # rather than accumulating stale ones alongside it.
                await db_execute(
                    "DELETE FROM platform_profile_claims WHERE user_id = $1 AND platform = $2",
                    user_id, platform,
                )
            for claim in claims:
                await db_execute(
                    """
                    INSERT INTO platform_profile_claims
                        (user_id, platform, claim_type, label, raw_label, source_file)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (user_id, platform, claim_type, label) DO NOTHING
                    """,
                    user_id, claim["platform"], claim["claim_type"],
                    claim["label"], claim["raw_label"], claim.get("source_file"),
                )
                claims_stored += 1
        except Exception as e:
            # An import that carried claims but no events is still a failure
            # worth reporting, but a claims-table problem must not discard the
            # user's behavioural history.
            logger.error("Could not store profile claims: %s", e, exc_info=True)

    # Search history: evidence the user went looking for something, which is
    # the only strong intent signal available (see interest_provenance).
    # Stored outside events on purpose — a query is not a content view.
    searches = parsed.get("search_signals") or []
    searches_stored = 0
    for signal in searches:
        try:
            # The parser emits ISO strings so its output stays JSON-serialisable,
            # but asyncpg type-checks the Python value against the column and
            # rejects a str for timestamptz regardless of the ::timestamptz
            # cast. Convert at the binding site.
            raw_when = signal.get("searched_at")
            when = datetime.fromisoformat(raw_when) if isinstance(raw_when, str) else raw_when

            await db_execute(
                """
                INSERT INTO search_signals
                    (user_id, platform, query, raw_query, searched_at, source_file)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (user_id, platform, query, searched_at) DO NOTHING
                """,
                user_id, signal["platform"], signal["query"], signal["raw_query"],
                when, signal.get("source_file"),
            )
            searches_stored += 1
        except Exception as e:
            logger.warning("Could not store search signal: %s", e)

    events = parsed["events"]
    if not events:
        if claims_stored or searches_stored:
            # An ad-interests-only export is a legitimate upload: it is exactly
            # what someone auditing their profile would send.
            return ArchiveImportResponse(
                success=True, events_found=0, events_stored=0,
                sources=parsed["sources"], duplicates_removed=0,
                skipped_files=parsed["skipped_files"], truncated=False,
                profile_claims_imported=claims_stored,
                search_signals_imported=searches_stored,
                message=f"Imported {claims_stored} platform ad-interest claims "
                        f"and {searches_stored} search signals. "
                        f"Open the Algorithmic Mirror to compare them against your behaviour.",
            )
        # A specific, actionable message. "No events found" alone leaves the
        # user with no idea whether they uploaded the wrong file or the right
        # file from an unsupported vintage.
        raise HTTPException(
            status_code=400,
            detail=(
                f"No supported activity found in this file "
                f"({parsed['skipped_files']} JSON files inspected). Expected an "
                f"Instagram 'Download your information' export in JSON format, "
                f"or a Google Takeout YouTube watch-history.json."
            ),
        )

    result = await ingest_events(
        IngestRequest(user_id=user_id, events=[EventItem(**e) for e in events]),
        background_tasks,
        authorization=authorization,
    )

    return ArchiveImportResponse(
        success=result.success,
        events_found=len(events),
        events_stored=result.events_stored,
        sources=parsed["sources"],
        duplicates_removed=parsed["duplicates_removed"],
        skipped_files=parsed["skipped_files"],
        truncated=parsed["truncated"],
        profile_claims_imported=claims_stored,
        search_signals_imported=searches_stored,
        identity_version=result.identity_version,
        confidence=result.confidence,
        message=(
            f"Imported {result.events_stored} events from "
            f"{', '.join(parsed['sources']) or 'export'}"
            + (" (truncated at the per-import limit)" if parsed["truncated"] else "")
        ),
    )
