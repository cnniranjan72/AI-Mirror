"""
Alignment API endpoint
Manages user goals and behavioral targets
"""
from fastapi import APIRouter, HTTPException
import logging

from app.models.rl_schemas import UserGoal, AlignmentResponse
from app.services.alignment import get_alignment_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/alignment", response_model=AlignmentResponse)
async def set_alignment_goal(goal_request: UserGoal):
    """
    Set user behavioral goal
    
    Args:
        goal_request: User goal with targets
        
    Returns:
        AlignmentResponse with goal ID
    """
    try:
        logger.info(f"Setting goal for user {goal_request.user_id}: {goal_request.goal}")
        
        alignment_service = get_alignment_service()
        
        goal_id = alignment_service.set_goal(
            user_id=goal_request.user_id,
            goal=goal_request.goal,
            target_watch_time=goal_request.target_watch_time,
            target_attention_score=goal_request.target_attention_score,
            target_engagement_score=goal_request.target_engagement_score,
            target_activity_level=goal_request.target_activity_level,
            priority=goal_request.priority
        )
        
        return AlignmentResponse(
            status="success",
            message=f"Goal set successfully: {goal_request.goal}",
            goal_id=goal_id,
            user_id=goal_request.user_id
        )
        
    except Exception as e:
        logger.error(f"Error setting goal: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/alignment/{user_id}")
async def get_user_goal(user_id: str):
    """
    Get active goal for user
    
    Args:
        user_id: User identifier
        
    Returns:
        Active goal or None
    """
    try:
        alignment_service = get_alignment_service()
        goal = alignment_service.get_active_goal(user_id)
        
        if not goal:
            return {
                "status": "no_goal",
                "message": "No active goal set",
                "goal": None
            }
        
        return {
            "status": "success",
            "goal": goal
        }
        
    except Exception as e:
        logger.error(f"Error getting goal: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
