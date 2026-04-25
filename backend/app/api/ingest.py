"""
POST /ingest — Full behavioral intelligence pipeline
Extension → Enrich → Expand → Embed → Store → Persona → RL
"""

import json
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import (
    enrichment,
    expansion,
    embedding as emb,
    vector_store,
    feature_engineering,
    persona as persona_svc,
    rl_layer,
)
from app.db.postgres import fetchrow, execute

logger = logging.getLogger(__name__)
router = APIRouter()


class EventItem(BaseModel):
    reel_id: str
    username: str = "unknown"
    caption: str = ""
    hashtags: List[str] = Field(default_factory=list)
    audio: str = ""
    watch_time: float = 0
    timestamp: str = ""
    session_id: str = ""


class IngestRequest(BaseModel):
    user_id: str = "default"
    events: List[EventItem]


class IngestResponse(BaseModel):
    success: bool
    events_stored: int
    embeddings_created: int
    persona_label: Optional[str] = None
    alignment_score: Optional[float] = None
    message: str


@router.post("/ingest", response_model=IngestResponse)
async def ingest_events(req: IngestRequest):
    """
    Full pipeline:
    1. Store raw events
    2. NLP enrichment (topics, sentiment, intent)
    3. Content expansion (short → rich text)
    4. Embedding generation (384-dim)
    5. Vector store insertion (pgvector)
    6. Feature engineering
    7. Persona computation
    8. RL alignment check
    """
    if not req.events:
        raise HTTPException(status_code=400, detail="No events provided")

    user_id = req.user_id
    stored_count = 0
    embed_count = 0
    event_dicts = []

    try:
        # ── STEP 1 & 2 & 3: Process each event ──
        texts_to_embed = []
        metadatas = []

        for ev in req.events:
            # 1. Store raw event
            ts = ev.timestamp or datetime.utcnow().isoformat()
            try:
                ts_parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                ts_parsed = datetime.utcnow()

            row = await fetchrow(
                """
                INSERT INTO events (user_id, reel_id, username, caption, hashtags,
                                    audio, watch_time, timestamp, session_id)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9)
                RETURNING id
                """,
                user_id,
                ev.reel_id,
                ev.username,
                ev.caption,
                json.dumps(ev.hashtags),
                ev.audio,
                ev.watch_time,
                ts_parsed,
                ev.session_id,
            )
            event_id = row["id"]
            stored_count += 1

            logger.info(
                "Event stored id=%d reel=%s user=%s caption=%s",
                event_id, ev.reel_id, ev.username,
                ev.caption[:50] if ev.caption else "(empty)",
            )

            # 2. NLP enrichment
            enriched = enrichment.enrich(ev.caption, ev.hashtags)
            logger.info("[ENRICH] topics=%s sentiment=%s intent=%s",
                         enriched["topics"], enriched["sentiment"], enriched["intent"])

            # 3. Content expansion
            expanded_text = expansion.expand(ev.caption, ev.hashtags, enriched)
            logger.info("[EXPAND] expanded text length: %d", len(expanded_text))

            texts_to_embed.append(expanded_text)
            metadatas.append({
                "event_id": event_id,
                "reel_id": ev.reel_id,
                "username": ev.username,
                "watch_time": ev.watch_time,
                "session_id": ev.session_id,
                "topics": enriched["topics"] or [],
                "sentiment": enriched["sentiment"] or "neutral",
                "intent": enriched["intent"] or "entertainment",
            })

            event_dicts.append({
                "reel_id": ev.reel_id,
                "username": ev.username,
                "caption": ev.caption,
                "hashtags": ev.hashtags,
                "watch_time": ev.watch_time,
                "session_id": ev.session_id,
            })

        # Collect all enrichment topics for persona
        all_topics = []
        for ev in req.events:
            enriched = enrichment.enrich(ev.caption, ev.hashtags)
            all_topics.extend(enriched["topics"])

        # ── STEP 4 & 5: Batch embed + store ──
        if texts_to_embed:
            embeddings = emb.encode_batch(texts_to_embed)
            logger.info("[EMBED] generated %d embeddings (dimension: %d)", len(embeddings), len(embeddings[0]) if embeddings else 0)
            embed_count = await vector_store.insert_embeddings_batch(
                user_id=user_id,
                texts=texts_to_embed,
                embeddings=embeddings,
                doc_type="event",
                metadatas=metadatas,
            )
            logger.info("[DB] inserted %d embeddings for user=%s", embed_count, user_id)

        # ── STEP 6: Feature engineering ──
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
            logger.info("Stored behavioral summary embedding")

        # ── STEP 7: Persona computation ──
        # Get unique topics
        unique_topics = list(set(all_topics))
        persona = persona_svc.compute_persona(features, enrichment_topics=unique_topics)
        await persona_svc.save_persona(user_id, persona)
        logger.info("[PERSONA] persona_label=%s confidence=%s", persona["persona_label"], persona["confidence"])

        # ── STEP 8: RL alignment ──
        alignment = rl_layer.compute_alignment(persona, features)
        suggestion = rl_layer.suggest_action(alignment, features)

        # Log the RL action
        await rl_layer.log_action(
            user_id=user_id,
            action_type=suggestion["action"]["action_id"],
            action_data=suggestion["action"],
            state=alignment["state"],
            reward=suggestion["expected_reward"],
        )

        return IngestResponse(
            success=True,
            events_stored=stored_count,
            embeddings_created=embed_count,
            persona_label=persona["persona_label"],
            alignment_score=alignment["overall_score"],
            message=f"Pipeline complete: {stored_count} events → {embed_count} embeddings → persona={persona['persona_label']}",
        )

    except Exception as e:
        logger.exception("Ingest pipeline failed")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")
