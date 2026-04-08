"""
Profile API endpoint
Generates and retrieves user behavioral persona
"""
from fastapi import APIRouter, HTTPException
import logging
from typing import List

from app.models.schemas import SessionSummary, BehavioralTraits
from app.services.persona import get_persona_generator
from app.services.vector_store import get_vector_store
from app.services.embedding import get_embedding_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/profile")
async def get_user_profile():
    """
    Get user's behavioral profile and persona
    
    Process:
    1. Retrieve all session summaries and traits from vector store
    2. Generate persona from aggregated data
    3. Return comprehensive profile
    
    Returns:
        Dictionary with persona and profile information
    """
    try:
        logger.info("Generating user profile")
        
        # Get services
        vector_store = get_vector_store()
        
        # Check if we have data
        collection_count = vector_store.get_collection_count()
        if collection_count == 0:
            logger.warning("No data available for profile generation")
            return {
                "status": "no_data",
                "message": "No behavioral data available. Start using Instagram to build your profile.",
                "persona": None
            }
        
        logger.info(f"Found {collection_count} items in collection")
        
        # Query for all session summaries
        embedding_service = get_embedding_service()
        summary_query_embedding = embedding_service.embed_text("session summary watch time reels")
        
        summary_results = vector_store.query(
            query_embedding=summary_query_embedding,
            top_k=50  # Get more results for comprehensive profile
        )
        
        # Query for all behavioral traits
        traits_query_embedding = embedding_service.embed_text("behavioral traits attention engagement")
        
        traits_results = vector_store.query(
            query_embedding=traits_query_embedding,
            top_k=50
        )
        
        # Extract summaries and traits from results
        summaries = []
        traits_list = []
        
        # Process summary results
        if summary_results.get('metadatas'):
            for metadata in summary_results['metadatas'][0]:
                if metadata.get('type') == 'session_summary':
                    summaries.append(SessionSummary(
                        session_id=metadata.get('session_id', ''),
                        total_watch_time=metadata.get('total_watch_time', 0),
                        avg_watch_time=metadata.get('total_watch_time', 0) / max(metadata.get('reels_count', 1), 1),
                        like_ratio=0.0,  # Not stored in metadata, use default
                        reels_count=metadata.get('reels_count', 0),
                        session_duration=0.0,  # Not stored in metadata
                        timestamp=metadata.get('timestamp', '')
                    ))
        
        # Process traits results
        if traits_results.get('metadatas'):
            for metadata in traits_results['metadatas'][0]:
                if metadata.get('type') == 'behavioral_traits':
                    traits_list.append(BehavioralTraits(
                        session_id=metadata.get('session_id', ''),
                        attention_score=metadata.get('attention_score', 0.0),
                        engagement_score=metadata.get('engagement_score', 0.0),
                        activity_level=0.0,  # Not stored in metadata
                        timestamp=metadata.get('timestamp', '')
                    ))
        
        logger.info(f"Retrieved {len(summaries)} summaries and {len(traits_list)} traits")
        
        if not summaries and not traits_list:
            return {
                "status": "insufficient_data",
                "message": "Not enough data to generate profile yet.",
                "persona": None
            }
        
        # Generate persona
        persona_generator = get_persona_generator()
        persona = persona_generator.generate_persona(summaries, traits_list)
        
        logger.info(f"Generated persona: {persona['archetype']}")
        
        return {
            "status": "success",
            "message": "Profile generated successfully",
            "persona": persona,
            "data_summary": {
                "total_sessions": len(summaries),
                "total_traits": len(traits_list),
                "collection_size": collection_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating profile: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
