"""
State Builder - Constructs RL state representation from behavioral data
"""
from typing import Dict, List, Optional
import statistics
import logging
from app.models.schemas import SessionSummary, BehavioralTraits

logger = logging.getLogger(__name__)


class StateBuilder:
    """
    Builds state representation for RL system
    """
    
    def build_state(
        self,
        recent_summaries: List[SessionSummary],
        recent_traits: List[BehavioralTraits],
        alignment_gap: float,
        goal: Optional[str] = None
    ) -> Dict:
        """
        Build state representation from behavioral data
        
        Args:
            recent_summaries: Recent session summaries
            recent_traits: Recent behavioral traits
            alignment_gap: Current alignment gap
            goal: User goal description
            
        Returns:
            State dictionary
        """
        if not recent_traits:
            return self._default_state(alignment_gap, goal)
        
        # Calculate aggregate metrics
        avg_attention = statistics.mean([t.attention_score for t in recent_traits])
        avg_engagement = statistics.mean([t.engagement_score for t in recent_traits])
        avg_activity = statistics.mean([t.activity_level for t in recent_traits])
        
        # Calculate trend
        if len(recent_traits) >= 3:
            recent_attention = statistics.mean([t.attention_score for t in recent_traits[-3:]])
            older_attention = statistics.mean([t.attention_score for t in recent_traits[:-3]]) if len(recent_traits) > 3 else recent_attention
            
            if recent_attention > older_attention + 0.1:
                trend = "improving"
            elif recent_attention < older_attention - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "unknown"
        
        # Calculate session metrics
        if recent_summaries:
            total_watch_time = sum([s.total_watch_time for s in recent_summaries])
            total_reels = sum([s.reels_count for s in recent_summaries])
            avg_watch_time = total_watch_time / max(total_reels, 1)
            session_duration = statistics.mean([s.session_duration for s in recent_summaries])
        else:
            total_watch_time = 0
            total_reels = 0
            avg_watch_time = 0
            session_duration = 0
        
        state = {
            "attention_score": round(avg_attention, 3),
            "engagement_score": round(avg_engagement, 3),
            "activity_level": round(avg_activity, 2),
            "recent_trend": trend,
            "alignment_gap": round(alignment_gap, 3),
            "goal": goal or "none",
            "total_watch_time": round(total_watch_time / 60, 2),  # in minutes
            "avg_watch_time": round(avg_watch_time, 2),
            "session_duration": round(session_duration / 60, 2),  # in minutes
            "total_reels": total_reels,
            "data_points": len(recent_traits)
        }
        
        return state
    
    def _default_state(self, alignment_gap: float, goal: Optional[str]) -> Dict:
        """
        Return default state when no data available
        
        Args:
            alignment_gap: Alignment gap
            goal: User goal
            
        Returns:
            Default state dictionary
        """
        return {
            "attention_score": 0.0,
            "engagement_score": 0.0,
            "activity_level": 0.0,
            "recent_trend": "unknown",
            "alignment_gap": round(alignment_gap, 3),
            "goal": goal or "none",
            "total_watch_time": 0.0,
            "avg_watch_time": 0.0,
            "session_duration": 0.0,
            "total_reels": 0,
            "data_points": 0
        }
    
    def state_to_vector(self, state: Dict) -> List[float]:
        """
        Convert state to numerical vector for RL
        
        Args:
            state: State dictionary
            
        Returns:
            State vector
        """
        # Encode trend
        trend_encoding = {
            "improving": 1.0,
            "stable": 0.0,
            "declining": -1.0,
            "unknown": 0.0
        }
        
        vector = [
            state.get("attention_score", 0.0),
            state.get("engagement_score", 0.0),
            state.get("activity_level", 0.0) / 20.0,  # normalize
            trend_encoding.get(state.get("recent_trend", "unknown"), 0.0),
            state.get("alignment_gap", 0.0),
            min(state.get("total_watch_time", 0.0) / 60.0, 1.0),  # normalize to hours
        ]
        
        return vector


def get_state_builder() -> StateBuilder:
    """Get state builder instance"""
    return StateBuilder()
