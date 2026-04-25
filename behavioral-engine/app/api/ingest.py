"""
Ingest API endpoint
Processes behavioral events and stores them in vector database
"""
from fastapi import APIRouter, HTTPException
from typing import List
import logging
from datetime import datetime
import uuid

from app.models.schemas import EventBatch, IngestResponse
from app.services.feature_engineering import (
    group_events_by_session,
    compute_session_summary,
    compute_behavioral_traits,
    summary_to_text,
    traits_to_text
)
from app.services.embedding import get_embedding_service
from app.services.vector_store import get_vector_store
from app.services.trends import get_trend_analyzer

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_events(batch: EventBatch):
    """
    Ingest a batch of behavioral events
    
    Process:
    1. Group events by session
    2. Compute summaries and traits
    3. Convert to text
    4. Generate embeddings
    5. Store in ChromaDB
    
    Args:
        batch: EventBatch containing list of events
        
    Returns:
        IngestResponse with processing statistics
    """
    try:
        logger.info(f"Received batch with {len(batch.events)} events")
        
        if not batch.events:
            raise HTTPException(status_code=400, detail="No events provided")
        
        # Get services
        embedding_service = get_embedding_service()
        vector_store = get_vector_store()
        
        # Group events by session
        sessions = group_events_by_session(batch.events)
        logger.info(f"Grouped into {len(sessions)} sessions")
        
        # Process each session
        texts = []
        embeddings = []
        metadatas = []
        doc_ids = []
        summaries_created = 0
        
        for session_id, events in sessions.items():
            try:
                # Compute session summary
                summary = compute_session_summary(events)
                summary_text = summary_to_text(summary)
                
                # Compute behavioral traits
                traits = compute_behavioral_traits(events)
                traits_text = traits_to_text(traits)
                
                # Generate embeddings
                summary_embedding = embedding_service.embed_text(summary_text)
                traits_embedding = embedding_service.embed_text(traits_text)
                
                # Prepare for batch storage
                # Store summary
                texts.append(summary_text)
                embeddings.append(summary_embedding)
                
                # Create metadata for summary
                summary_metadata = {
                    "type": "session_summary",
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "total_watch_time": summary.total_watch_time,
                    "reels_count": summary.reels_count,
                    "captions": summary.captions,
                    "hashtags": summary.hashtags if summary.hashtags else ["none"],
                    "audio_info": summary.audio_info
                }
                metadatas.append(summary_metadata)
                doc_ids.append(f"summary_{session_id}_{uuid.uuid4().hex[:8]}")
                
                # Store traits
                texts.append(traits_text)
                embeddings.append(traits_embedding)
                metadatas.append({
                    "type": "behavioral_traits",
                    "session_id": session_id,
                    "timestamp": traits.timestamp,
                    "attention_score": traits.attention_score,
                    "engagement_score": traits.engagement_score
                })
                doc_ids.append(f"traits_{session_id}_{uuid.uuid4().hex[:8]}")
                
                summaries_created += 2  # summary + traits
                
            except Exception as e:
                logger.error(f"Error processing session {session_id}: {str(e)}")
                continue
        
        # Store all embeddings in batch
        if embeddings:
            vector_store.add_embeddings_batch(
                embeddings=embeddings,
                texts=texts,
                metadatas=metadatas,
                doc_ids=doc_ids
            )
            logger.info(f"Stored {len(embeddings)} embeddings in ChromaDB")
        
        # Detect trends across sessions (if we have enough data)
        all_summaries = []
        all_traits = []
        
        for session_id, events in sessions.items():
            try:
                all_summaries.append(compute_session_summary(events))
                all_traits.append(compute_behavioral_traits(events))
            except:
                pass
        
        if len(all_summaries) >= 3:
            # Generate trend summary
            trend_analyzer = get_trend_analyzer()
            trend_summary_text = trend_analyzer.generate_trend_summary(all_summaries, all_traits)
            
            # Embed and store trend
            trend_embedding = embedding_service.embed_text(trend_summary_text)
            
            vector_store.add_embedding(
                embedding=trend_embedding,
                text=trend_summary_text,
                metadata={
                    "type": "trend",
                    "timestamp": datetime.utcnow().isoformat(),
                    "sessions_analyzed": len(all_summaries)
                },
                doc_id=f"trend_{uuid.uuid4().hex[:12]}"
            )
            
            logger.info("Stored trend analysis")
        
        return IngestResponse(
            status="success",
            events_processed=len(batch.events),
            summaries_created=summaries_created,
            embeddings_stored=len(embeddings),
            message=f"Successfully processed {len(batch.events)} events from {len(sessions)} sessions"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in ingest endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
