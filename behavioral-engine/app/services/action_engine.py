"""
Action Engine - Generates behavioral intervention suggestions
"""
from typing import List, Dict
import uuid
import logging

logger = logging.getLogger(__name__)


class ActionEngine:
    """
    Generates contextual behavioral actions based on state and goals
    """
    
    def __init__(self):
        """Initialize action engine with predefined action templates"""
        self.action_templates = self._initialize_actions()
    
    def _initialize_actions(self) -> List[Dict]:
        """
        Initialize action templates
        
        Returns:
            List of action templates
        """
        return [
            # Time limit actions
            {
                "type": "suggestion",
                "category": "time_limit",
                "description": "Take a 5-minute break after every 10 reels",
                "intensity": "low",
                "conditions": {"activity_level": ">10", "attention_score": "<0.4"}
            },
            {
                "type": "intervention",
                "category": "time_limit",
                "description": "Limit your session to 15 minutes",
                "intensity": "medium",
                "conditions": {"activity_level": ">15", "alignment_gap": ">0.5"}
            },
            {
                "type": "intervention",
                "category": "time_limit",
                "description": "Stop scrolling - you've reached your daily limit",
                "intensity": "high",
                "conditions": {"total_watch_time": ">60", "alignment_gap": ">0.7"}
            },
            
            # Content switch actions
            {
                "type": "suggestion",
                "category": "content_switch",
                "description": "Switch to educational or informative content",
                "intensity": "low",
                "conditions": {"engagement_score": "<0.3", "attention_score": "<0.3"}
            },
            {
                "type": "suggestion",
                "category": "content_switch",
                "description": "Explore new creators - your feed seems repetitive",
                "intensity": "medium",
                "conditions": {"engagement_score": "<0.2"}
            },
            
            # Break actions
            {
                "type": "reminder",
                "category": "break",
                "description": "Take a short walk - you've been scrolling for a while",
                "intensity": "medium",
                "conditions": {"activity_level": ">12", "session_duration": ">20"}
            },
            {
                "type": "intervention",
                "category": "break",
                "description": "Close the app and do something else for 30 minutes",
                "intensity": "high",
                "conditions": {"alignment_gap": ">0.8", "activity_level": ">20"}
            },
            
            # Mindfulness actions
            {
                "type": "suggestion",
                "category": "mindfulness",
                "description": "Slow down - watch each reel fully before scrolling",
                "intensity": "low",
                "conditions": {"attention_score": "<0.3", "activity_level": ">15"}
            },
            {
                "type": "suggestion",
                "category": "mindfulness",
                "description": "Ask yourself: Is this content adding value?",
                "intensity": "medium",
                "conditions": {"engagement_score": "<0.2", "attention_score": "<0.4"}
            },
            {
                "type": "reminder",
                "category": "mindfulness",
                "description": "Notice your scrolling pattern - are you seeking or escaping?",
                "intensity": "medium",
                "conditions": {"activity_level": ">18"}
            },
            
            # Engagement actions
            {
                "type": "suggestion",
                "category": "engagement",
                "description": "Like content you enjoy to improve your feed",
                "intensity": "low",
                "conditions": {"engagement_score": "<0.2", "attention_score": ">0.5"}
            },
            {
                "type": "suggestion",
                "category": "engagement",
                "description": "Unfollow creators that don't resonate with you",
                "intensity": "medium",
                "conditions": {"engagement_score": "<0.15"}
            }
        ]
    
    def generate_actions(
        self,
        state: Dict,
        alignment_gap: float,
        top_k: int = 3
    ) -> List[Dict]:
        """
        Generate relevant actions based on current state
        
        Args:
            state: Current behavioral state
            alignment_gap: Gap between current and target behavior
            top_k: Number of actions to return
            
        Returns:
            List of relevant actions
        """
        relevant_actions = []
        
        for template in self.action_templates:
            if self._matches_conditions(template['conditions'], state, alignment_gap):
                action = {
                    "action_id": f"action_{uuid.uuid4().hex[:12]}",
                    "type": template['type'],
                    "description": template['description'],
                    "intensity": template['intensity'],
                    "category": template['category']
                }
                relevant_actions.append(action)
        
        # Sort by intensity (high priority first when alignment gap is large)
        intensity_order = {"high": 3, "medium": 2, "low": 1}
        if alignment_gap > 0.6:
            relevant_actions.sort(key=lambda x: intensity_order[x['intensity']], reverse=True)
        else:
            relevant_actions.sort(key=lambda x: intensity_order[x['intensity']])
        
        return relevant_actions[:top_k]
    
    def _matches_conditions(
        self,
        conditions: Dict,
        state: Dict,
        alignment_gap: float
    ) -> bool:
        """
        Check if state matches action conditions
        
        Args:
            conditions: Condition dictionary
            state: Current state
            alignment_gap: Alignment gap value
            
        Returns:
            True if conditions match
        """
        for key, condition in conditions.items():
            if key == "alignment_gap":
                value = alignment_gap
            else:
                value = state.get(key, 0)
            
            # Parse condition (e.g., ">10", "<0.4")
            if isinstance(condition, str):
                if condition.startswith(">"):
                    threshold = float(condition[1:])
                    if value <= threshold:
                        return False
                elif condition.startswith("<"):
                    threshold = float(condition[1:])
                    if value >= threshold:
                        return False
                elif condition.startswith("="):
                    threshold = float(condition[1:])
                    if value != threshold:
                        return False
        
        return True
    
    def get_action_by_id(self, action_id: str) -> Dict:
        """
        Get action details by ID (for feedback tracking)
        
        Args:
            action_id: Action identifier
            
        Returns:
            Action details
        """
        # In production, this would query a database
        # For now, return a placeholder
        return {
            "action_id": action_id,
            "type": "suggestion",
            "description": "Action details",
            "intensity": "medium",
            "category": "general"
        }


def get_action_engine() -> ActionEngine:
    """Get action engine instance"""
    return ActionEngine()
