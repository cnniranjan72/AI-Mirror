"""
Context Fusion Engine
Combines multiple context sources into structured narrative
"""
from typing import Dict, List, Optional
import logging
from app.services.context_builder import get_context_builder
from app.services.persona import get_persona_generator
from app.services.alignment import get_alignment_service
from app.services.rl_bandit import get_bandit
from app.models.schemas import SessionSummary, BehavioralTraits

logger = logging.getLogger(__name__)


class ContextFusionEngine:
    """
    Fuses multiple context sources into coherent narrative
    """
    
    def fuse_context(
        self,
        user_id: str,
        query: str,
        summaries: List[SessionSummary],
        traits_list: List[BehavioralTraits],
        trends: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Fuse all context sources into structured narrative
        
        Args:
            user_id: User identifier
            query: User query
            summaries: Session summaries
            traits_list: Behavioral traits
            trends: Trend data
            
        Returns:
            Fused context dictionary
        """
        # Generate persona
        persona_summary = self._generate_persona_summary(summaries, traits_list)
        
        # Analyze recent behavior
        recent_behavior = self._analyze_recent_behavior(summaries, traits_list)
        
        # Detect trends
        trend_analysis = self._analyze_trends(summaries, traits_list, trends)
        
        # Get action history
        action_history = self._get_action_history(user_id)
        
        # Get alignment goal
        goal_info = self._get_goal_info(user_id)
        
        # Build narrative context
        narrative = self._build_narrative(
            persona_summary,
            recent_behavior,
            trend_analysis,
            action_history,
            goal_info
        )
        
        fused_context = {
            "persona_summary": persona_summary,
            "recent_behavior": recent_behavior,
            "trend_analysis": trend_analysis,
            "action_history": action_history,
            "goal": goal_info,
            "narrative": narrative,
            "data_quality": self._assess_data_quality(summaries, traits_list)
        }
        
        logger.info(f"Fused context for user {user_id}: {len(summaries)} sessions, quality={fused_context['data_quality']}")
        
        return fused_context
    
    def _generate_persona_summary(
        self,
        summaries: List[SessionSummary],
        traits_list: List[BehavioralTraits]
    ) -> str:
        """Generate persona summary"""
        if not summaries or not traits_list:
            return "Insufficient data to generate persona."
        
        persona_gen = get_persona_generator()
        persona = persona_gen.generate_persona(summaries, traits_list)
        
        archetype = persona.get('archetype', 'Unknown')
        summary = persona.get('summary', '')
        
        return f"{archetype}: {summary}"
    
    def _analyze_recent_behavior(
        self,
        summaries: List[SessionSummary],
        traits_list: List[BehavioralTraits]
    ) -> str:
        """Analyze recent behavioral patterns"""
        if not traits_list:
            return "No recent behavioral data available."
        
        import statistics
        
        # Get last 3 sessions
        recent_traits = traits_list[-3:] if len(traits_list) >= 3 else traits_list
        recent_summaries = summaries[-3:] if len(summaries) >= 3 else summaries
        
        avg_attention = statistics.mean([t.attention_score for t in recent_traits])
        avg_engagement = statistics.mean([t.engagement_score for t in recent_traits])
        
        if recent_summaries:
            total_reels = sum([s.reels_count for s in recent_summaries])
            total_time = sum([s.total_watch_time for s in recent_summaries])
        else:
            total_reels = 0
            total_time = 0
        
        behavior_desc = f"In your last {len(recent_summaries)} sessions, you watched {total_reels} reels "
        behavior_desc += f"({total_time/60:.1f} minutes). "
        
        if avg_attention < 0.3:
            behavior_desc += "Your attention is low - rapid scrolling. "
        elif avg_attention > 0.6:
            behavior_desc += "Your attention is high - careful viewing. "
        else:
            behavior_desc += "Your attention is moderate. "
        
        if avg_engagement < 0.3:
            behavior_desc += "Low engagement with content."
        elif avg_engagement > 0.5:
            behavior_desc += "High engagement - actively liking content."
        else:
            behavior_desc += "Moderate engagement."
        
        return behavior_desc
    
    def _analyze_trends(
        self,
        summaries: List[SessionSummary],
        traits_list: List[BehavioralTraits],
        trends: Optional[List[Dict]]
    ) -> str:
        """Analyze behavioral trends"""
        if len(traits_list) < 3:
            return "Not enough data to detect trends."
        
        import statistics
        
        # Compare first half vs second half
        mid = len(traits_list) // 2
        first_half = traits_list[:mid]
        second_half = traits_list[mid:]
        
        first_attention = statistics.mean([t.attention_score for t in first_half])
        second_attention = statistics.mean([t.attention_score for t in second_half])
        
        change = second_attention - first_attention
        
        if change > 0.1:
            trend_desc = "Your attention is improving over time. "
        elif change < -0.1:
            trend_desc = "Your attention is declining over time. "
        else:
            trend_desc = "Your behavior is stable. "
        
        # Activity trend
        if summaries:
            first_activity = statistics.mean([s.reels_count for s in summaries[:mid]])
            second_activity = statistics.mean([s.reels_count for s in summaries[mid:]])
            
            if second_activity > first_activity * 1.2:
                trend_desc += "Activity increasing."
            elif second_activity < first_activity * 0.8:
                trend_desc += "Activity decreasing."
        
        return trend_desc
    
    def _get_action_history(self, user_id: str) -> str:
        """Get recent action history"""
        try:
            bandit = get_bandit()
            history = bandit.get_user_history(user_id, limit=3)
            
            if not history:
                return "No previous actions taken."
            
            action_desc = f"You've received {len(history)} recent suggestions. "
            
            avg_reward = statistics.mean([h['reward'] for h in history])
            if avg_reward > 0.3:
                action_desc += "Actions have been helpful."
            elif avg_reward < -0.1:
                action_desc += "Actions haven't been effective yet."
            else:
                action_desc += "Mixed results from actions."
            
            return action_desc
        except:
            return "No action history available."
    
    def _get_goal_info(self, user_id: str) -> str:
        """Get user goal information"""
        try:
            alignment_service = get_alignment_service()
            goal = alignment_service.get_active_goal(user_id)
            
            if not goal:
                return "No active goal set."
            
            goal_text = goal.get('goal', 'Unknown goal')
            priority = goal.get('priority', 'medium')
            
            return f"Goal: {goal_text} (priority: {priority})"
        except:
            return "No goal information available."
    
    def _build_narrative(
        self,
        persona: str,
        behavior: str,
        trends: str,
        actions: str,
        goal: str
    ) -> str:
        """Build coherent narrative from all context"""
        narrative_parts = []
        
        # Persona
        narrative_parts.append(f"**Your Profile:** {persona}")
        
        # Recent behavior
        narrative_parts.append(f"**Recent Activity:** {behavior}")
        
        # Trends
        if "Not enough" not in trends:
            narrative_parts.append(f"**Trends:** {trends}")
        
        # Goal
        if "No active goal" not in goal:
            narrative_parts.append(f"**Your Goal:** {goal}")
        
        # Actions
        if "No previous" not in actions:
            narrative_parts.append(f"**Action History:** {actions}")
        
        return "\n\n".join(narrative_parts)
    
    def _assess_data_quality(
        self,
        summaries: List[SessionSummary],
        traits_list: List[BehavioralTraits]
    ) -> str:
        """Assess quality of available data"""
        session_count = len(summaries)
        
        if session_count == 0:
            return "no_data"
        elif session_count < 3:
            return "low"
        elif session_count < 10:
            return "medium"
        else:
            return "high"


def get_context_fusion_engine() -> ContextFusionEngine:
    """Get context fusion engine instance"""
    return ContextFusionEngine()
