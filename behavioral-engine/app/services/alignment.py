"""
Alignment service for storing and managing user goals
"""
from typing import Dict, Optional, List
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AlignmentService:
    """
    Manages user goals and alignment targets
    """
    
    def __init__(self, storage_path: str = "./alignment_data"):
        """
        Initialize alignment service
        
        Args:
            storage_path: Directory to store alignment data
        """
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        self.goals_file = os.path.join(storage_path, "goals.json")
        self.goals = self._load_goals()
    
    def _load_goals(self) -> Dict:
        """Load goals from disk"""
        if os.path.exists(self.goals_file):
            try:
                with open(self.goals_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_goals(self):
        """Save goals to disk"""
        with open(self.goals_file, 'w') as f:
            json.dump(self.goals, f, indent=2)
    
    def set_goal(
        self,
        user_id: str,
        goal: str,
        target_watch_time: Optional[float] = None,
        target_attention_score: Optional[float] = None,
        target_engagement_score: Optional[float] = None,
        target_activity_level: Optional[float] = None,
        priority: str = "medium"
    ) -> str:
        """
        Set user goal
        
        Args:
            user_id: User identifier
            goal: Goal description
            target_watch_time: Target watch time in minutes
            target_attention_score: Target attention score (0-1)
            target_engagement_score: Target engagement score (0-1)
            target_activity_level: Target activity level (reels/min)
            priority: Priority level
            
        Returns:
            Goal ID
        """
        goal_id = f"goal_{user_id}_{datetime.utcnow().timestamp()}"
        
        goal_data = {
            "goal_id": goal_id,
            "user_id": user_id,
            "goal": goal,
            "target_watch_time": target_watch_time,
            "target_attention_score": target_attention_score,
            "target_engagement_score": target_engagement_score,
            "target_activity_level": target_activity_level,
            "priority": priority,
            "created_at": datetime.utcnow().isoformat(),
            "active": True
        }
        
        if user_id not in self.goals:
            self.goals[user_id] = []
        
        self.goals[user_id].append(goal_data)
        self._save_goals()
        
        logger.info(f"Set goal for user {user_id}: {goal}")
        return goal_id
    
    def get_active_goal(self, user_id: str) -> Optional[Dict]:
        """
        Get active goal for user
        
        Args:
            user_id: User identifier
            
        Returns:
            Goal data or None
        """
        if user_id not in self.goals:
            return None
        
        # Return most recent active goal
        active_goals = [g for g in self.goals[user_id] if g.get('active', True)]
        if active_goals:
            return active_goals[-1]
        return None
    
    def get_all_goals(self, user_id: str) -> List[Dict]:
        """
        Get all goals for user
        
        Args:
            user_id: User identifier
            
        Returns:
            List of goals
        """
        return self.goals.get(user_id, [])
    
    def calculate_alignment_gap(
        self,
        user_id: str,
        current_metrics: Dict
    ) -> Dict:
        """
        Calculate gap between current behavior and goal
        
        Args:
            user_id: User identifier
            current_metrics: Current behavioral metrics
            
        Returns:
            Dictionary with gap information
        """
        goal = self.get_active_goal(user_id)
        if not goal:
            return {
                "has_goal": False,
                "total_gap": 0.0,
                "gaps": {}
            }
        
        gaps = {}
        total_gap = 0.0
        count = 0
        
        # Calculate individual gaps
        if goal.get('target_watch_time') is not None:
            current = current_metrics.get('avg_watch_time', 0)
            target = goal['target_watch_time']
            gap = abs(current - target) / max(target, 1.0)
            gaps['watch_time'] = gap
            total_gap += gap
            count += 1
        
        if goal.get('target_attention_score') is not None:
            current = current_metrics.get('attention_score', 0)
            target = goal['target_attention_score']
            gap = abs(current - target)
            gaps['attention'] = gap
            total_gap += gap
            count += 1
        
        if goal.get('target_engagement_score') is not None:
            current = current_metrics.get('engagement_score', 0)
            target = goal['target_engagement_score']
            gap = abs(current - target)
            gaps['engagement'] = gap
            total_gap += gap
            count += 1
        
        if goal.get('target_activity_level') is not None:
            current = current_metrics.get('activity_level', 0)
            target = goal['target_activity_level']
            gap = abs(current - target) / max(target, 1.0)
            gaps['activity'] = gap
            total_gap += gap
            count += 1
        
        avg_gap = total_gap / count if count > 0 else 0.0
        
        return {
            "has_goal": True,
            "goal": goal['goal'],
            "total_gap": round(avg_gap, 3),
            "gaps": gaps,
            "priority": goal['priority']
        }


# Global instance
_alignment_service = None


def get_alignment_service() -> AlignmentService:
    """Get or create alignment service instance"""
    global _alignment_service
    if _alignment_service is None:
        _alignment_service = AlignmentService()
    return _alignment_service
