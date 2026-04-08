"""
Chat API endpoint
Conversational interface with RAG and virtual character
"""
from fastapi import APIRouter, HTTPException
import logging

from app.models.rl_schemas import ChatRequest, ChatResponse
from app.services.context_builder import get_context_builder
from app.services.rag_engine import get_rag_engine
from app.services.virtual_character import get_virtual_character
from app.services.chat_memory import get_chat_memory
from app.services.persona import get_persona_generator
from app.services.vector_store import get_vector_store
from app.services.embedding import get_embedding_service
from app.models.schemas import SessionSummary, BehavioralTraits

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_mirror(request: ChatRequest):
    """
    Chat with AI Mirror using RAG
    
    Process:
    1. Build context from vector database
    2. Retrieve user persona
    3. Generate response using RAG engine
    4. Apply virtual character voice
    5. Store in chat memory
    6. Return response
    
    Args:
        request: ChatRequest with user query
        
    Returns:
        ChatResponse with AI Mirror response
    """
    try:
        logger.info(f"Chat request from user {request.user_id}: '{request.query}'")
        
        # Get services
        context_builder = get_context_builder()
        rag_engine = get_rag_engine()
        virtual_character = get_virtual_character()
        chat_memory = get_chat_memory()
        
        # Store user message
        chat_memory.add_message(request.user_id, "user", request.query)
        
        # Build context if requested
        context = {}
        if request.include_context:
            context = context_builder.build_context(
                query=request.query,
                user_id=request.user_id,
                top_k=10
            )
            logger.info(f"Retrieved context: {len(context.get('raw_documents', []))} documents")
        
        # Get user persona
        persona = None
        try:
            # Retrieve persona from vector store
            embedding_service = get_embedding_service()
            vector_store = get_vector_store()
            
            # Query for behavioral traits to build persona
            traits_query = embedding_service.embed_text("behavioral traits attention engagement")
            traits_results = vector_store.query(query_embedding=traits_query, top_k=10)
            
            summary_query = embedding_service.embed_text("session summary watch time")
            summary_results = vector_store.query(query_embedding=summary_query, top_k=10)
            
            # Extract summaries and traits
            summaries = []
            traits_list = []
            
            if summary_results.get('metadatas'):
                for metadata in summary_results['metadatas'][0]:
                    if metadata.get('type') == 'session_summary':
                        summaries.append(SessionSummary(
                            session_id=metadata.get('session_id', ''),
                            total_watch_time=metadata.get('total_watch_time', 0),
                            avg_watch_time=metadata.get('total_watch_time', 0) / max(metadata.get('reels_count', 1), 1),
                            like_ratio=0.0,
                            reels_count=metadata.get('reels_count', 0),
                            session_duration=0.0,
                            timestamp=metadata.get('timestamp', '')
                        ))
            
            if traits_results.get('metadatas'):
                for metadata in traits_results['metadatas'][0]:
                    if metadata.get('type') == 'behavioral_traits':
                        traits_list.append(BehavioralTraits(
                            session_id=metadata.get('session_id', ''),
                            attention_score=metadata.get('attention_score', 0.0),
                            engagement_score=metadata.get('engagement_score', 0.0),
                            activity_level=0.0,
                            timestamp=metadata.get('timestamp', '')
                        ))
            
            # Generate persona if we have data
            if summaries and traits_list:
                persona_generator = get_persona_generator()
                persona = persona_generator.generate_persona(summaries, traits_list)
                logger.info(f"Generated persona: {persona.get('archetype', 'Unknown')}")
        
        except Exception as e:
            logger.warning(f"Could not generate persona: {str(e)}")
        
        # Generate RAG response
        rag_response = rag_engine.generate_response(
            query=request.query,
            context=context,
            persona=persona
        )
        
        # Apply virtual character voice
        base_response = rag_response.get("response", "")
        suggestions = rag_response.get("suggested_actions", [])
        
        # Determine sentiment
        sentiment = "neutral"
        if "low attention" in base_response.lower() or "addiction" in base_response.lower():
            sentiment = "negative"
        elif "positive" in base_response.lower() or "healthy" in base_response.lower():
            sentiment = "positive"
        
        enhanced_response = virtual_character.format_as_mirror(
            response=base_response,
            persona=persona,
            sentiment=sentiment,
            suggestions=suggestions
        )
        
        # Store assistant message
        chat_memory.add_message(request.user_id, "assistant", enhanced_response)
        
        # Prepare response
        context_used = rag_response.get("context_used", [])
        confidence = rag_response.get("confidence", 0.5)
        
        persona_text = None
        if persona:
            persona_text = f"{persona.get('archetype', 'Unknown')}: {persona.get('summary', '')}"
        
        logger.info(f"Generated response with confidence {confidence}")
        
        return ChatResponse(
            response=enhanced_response,
            context_used=context_used,
            persona=persona_text,
            confidence=confidence,
            suggested_actions=suggestions
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/chat/history/{user_id}")
async def get_chat_history(user_id: str, limit: int = 10):
    """
    Get chat history for user
    
    Args:
        user_id: User identifier
        limit: Maximum messages to return
        
    Returns:
        Chat history
    """
    try:
        chat_memory = get_chat_memory()
        history = chat_memory.get_history(user_id, limit=limit)
        
        return {
            "status": "success",
            "user_id": user_id,
            "history": history,
            "count": len(history)
        }
        
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/chat/history/{user_id}")
async def clear_chat_history(user_id: str):
    """
    Clear chat history for user
    
    Args:
        user_id: User identifier
        
    Returns:
        Success message
    """
    try:
        chat_memory = get_chat_memory()
        chat_memory.clear_history(user_id)
        
        return {
            "status": "success",
            "message": f"Chat history cleared for user {user_id}"
        }
        
    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
