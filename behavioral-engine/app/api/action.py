"""
Action API endpoint
Provides RL-based action suggestions
"""
from fastapi import APIRouter, HTTPException
import logging

from app.models.rl_schemas import ActionRequest, ActionResponse
from app.services.alignment import get_alignment_service
from app.services.action_engine import get_action_engine
from app.services.state_builder import get_state_builder
from app.services.rl_bandit import get_bandit
from app.services.vector_store import get_vector_store
from app.services.embedding import get_embedding_service
from app.models.schemas import SessionSummary, BehavioralTraits

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/action", response_model=ActionResponse)
async def get_action_suggestion(request: ActionRequest):
    """
    Get RL-based action suggestion for user
    
    Process:
    1. Retrieve recent behavioral data
    2. Build current state
    3. Calculate alignment gap
    4. Generate candidate actions
    5. Select best action via RL bandit
    6. Return action with context
    
    Args:
        request: ActionRequest with user_id
        
    Returns:
        ActionResponse with suggested action
    """
    try:
        logger.info(f"Generating action for user {request.user_id}")
        
        # Get services
        alignment_service = get_alignment_service()
        action_engine = get_action_engine()
        state_builder = get_state_builder()
        bandit = get_bandit()
        vector_store = get_vector_store()
        embedding_service = get_embedding_service()
        
        # Get user goal
        goal = alignment_service.get_active_goal(request.user_id)
        goal_text = goal['goal'] if goal else None
        
        # Retrieve recent behavioral data from vector store
        traits_query = embedding_service.embed_text("behavioral traits attention engagement")
        traits_results = vector_store.query(query_embedding=traits_query, top_k=10)
        
        summary_query = embedding_service.embed_text("session summary watch time")
        summary_results = vector_store.query(query_embedding=summary_query, top_k=10)
        
        # Extract recent summaries and traits
        recent_summaries = []
        recent_traits = []
        
        if summary_results.get('metadatas'):
            for metadata in summary_results['metadatas'][0]:
                if metadata.get('type') == 'session_summary':
                    recent_summaries.append(SessionSummary(
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
                    recent_traits.append(BehavioralTraits(
                        session_id=metadata.get('session_id', ''),
                        attention_score=metadata.get('attention_score', 0.0),
                        engagement_score=metadata.get('engagement_score', 0.0),
                        activity_level=0.0,
                        timestamp=metadata.get('timestamp', '')
                    ))
        
        # Calculate current metrics for alignment gap
        if recent_traits:
            import statistics
            current_metrics = {
                'attention_score': statistics.mean([t.attention_score for t in recent_traits]),
                'engagement_score': statistics.mean([t.engagement_score for t in recent_traits]),
                'activity_level': statistics.mean([t.activity_level for t in recent_traits]),
                'avg_watch_time': statistics.mean([s.avg_watch_time for s in recent_summaries]) if recent_summaries else 0
            }
        else:
            current_metrics = {
                'attention_score': 0.0,
                'engagement_score': 0.0,
                'activity_level': 0.0,
                'avg_watch_time': 0.0
            }
        
        # Calculate alignment gap
        alignment_data = alignment_service.calculate_alignment_gap(request.user_id, current_metrics)
        alignment_gap = alignment_data['total_gap']
        
        # Build state
        state = state_builder.build_state(
            recent_summaries=recent_summaries,
            recent_traits=recent_traits,
            alignment_gap=alignment_gap,
            goal=goal_text
        )
        
        logger.info(f"State: attention={state['attention_score']}, gap={alignment_gap}")
        
        # Generate candidate actions
        candidate_actions = action_engine.generate_actions(
            state=state,
            alignment_gap=alignment_gap,
            top_k=5
        )
        
        if not candidate_actions:
            raise HTTPException(status_code=404, detail="No suitable actions found")
        
        # Select action via RL bandit
        selected_action = bandit.select_action(
            available_actions=candidate_actions,
            user_id=request.user_id,
            state=state
        )
        
        logger.info(f"Selected action: {selected_action['description']}")
        
        # Calculate confidence based on data availability and alignment gap
        confidence = min(1.0, len(recent_traits) / 5.0) * (1.0 - alignment_gap * 0.5)
        
        return ActionResponse(
            action=selected_action,
            state=state,
            alignment_gap=alignment_gap,
            confidence=round(confidence, 2)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating action: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
