"""
Feedback API endpoint
Processes user feedback and updates RL system
"""
from fastapi import APIRouter, HTTPException
import logging

from app.models.rl_schemas import Feedback, FeedbackResponse
from app.services.rl_bandit import get_bandit
from app.services.reward import get_reward_calculator
from app.services.alignment import get_alignment_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: Feedback):
    """
    Submit feedback on action and update RL system
    
    Process:
    1. Calculate reward based on feedback
    2. Update bandit with reward
    3. Return updated statistics
    
    Args:
        feedback: Feedback data
        
    Returns:
        FeedbackResponse with reward and updated stats
    """
    try:
        logger.info(f"Processing feedback for user {feedback.user_id}, action {feedback.action_id}")
        
        # Get services
        bandit = get_bandit()
        reward_calculator = get_reward_calculator()
        alignment_service = get_alignment_service()
        
        # Get user goal to determine alignment improvement
        goal = alignment_service.get_active_goal(feedback.user_id)
        
        # Calculate alignment improvement (if behavior_change provided)
        alignment_improvement = None
        if feedback.behavior_change is not None and goal:
            # Positive behavior change means alignment improved
            alignment_improvement = feedback.behavior_change * 0.5
        
        # Calculate reward
        reward = reward_calculator.calculate_reward(
            followed=feedback.followed,
            behavior_change=feedback.behavior_change,
            alignment_improvement=alignment_improvement,
            user_rating=feedback.user_rating
        )
        
        # Update bandit
        updated_stats = bandit.update(
            user_id=feedback.user_id,
            action_id=feedback.action_id,
            reward=reward
        )
        
        logger.info(f"Reward: {reward:.3f}, Updated avg: {updated_stats['avg_reward']:.3f}")
        
        return FeedbackResponse(
            status="success",
            message="Feedback processed successfully",
            reward=round(reward, 3),
            updated_action_value=round(updated_stats['avg_reward'], 3)
        )
        
    except Exception as e:
        logger.error(f"Error processing feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/feedback/history/{user_id}")
async def get_feedback_history(user_id: str, limit: int = 10):
    """
    Get feedback history for user
    
    Args:
        user_id: User identifier
        limit: Maximum number of records
        
    Returns:
        List of feedback records
    """
    try:
        bandit = get_bandit()
        history = bandit.get_user_history(user_id, limit=limit)
        
        return {
            "status": "success",
            "user_id": user_id,
            "history": history,
            "count": len(history)
        }
        
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/feedback/top-actions")
async def get_top_actions(top_k: int = 5):
    """
    Get top performing actions
    
    Args:
        top_k: Number of top actions to return
        
    Returns:
        List of top actions with statistics
    """
    try:
        bandit = get_bandit()
        top_actions = bandit.get_top_actions(top_k=top_k)
        
        return {
            "status": "success",
            "top_actions": top_actions
        }
        
    except Exception as e:
        logger.error(f"Error getting top actions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
