"""
Impact Analysis Layer
Analyzes consequences of behavioral patterns
"""
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """
    Analyzes impact and consequences of behavioral patterns
    """
    
    def analyze_impact(
        self,
        attention_score: float,
        engagement_score: float,
        activity_level: float,
        total_watch_time: float
    ) -> Dict:
        """
        Analyze impact of current behavioral patterns
        
        Args:
            attention_score: Attention score (0-1)
            engagement_score: Engagement score (0-1)
            activity_level: Activity level (reels/min)
            total_watch_time: Total watch time in minutes
            
        Returns:
            Impact analysis dictionary
        """
        impacts = {
            "attention_impact": self._analyze_attention_impact(attention_score),
            "productivity_impact": self._analyze_productivity_impact(total_watch_time, activity_level),
            "habit_formation_risk": self._analyze_habit_risk(activity_level, total_watch_time),
            "cognitive_impact": self._analyze_cognitive_impact(attention_score, activity_level),
            "overall_severity": "low"
        }
        
        # Calculate overall severity
        severity_score = 0
        if attention_score < 0.3:
            severity_score += 2
        if total_watch_time > 60:
            severity_score += 2
        if activity_level > 15:
            severity_score += 1
        
        if severity_score >= 4:
            impacts["overall_severity"] = "high"
        elif severity_score >= 2:
            impacts["overall_severity"] = "medium"
        else:
            impacts["overall_severity"] = "low"
        
        logger.info(f"Impact analysis: severity={impacts['overall_severity']}, attention={attention_score:.2f}")
        
        return impacts
    
    def _analyze_attention_impact(self, attention_score: float) -> str:
        """Analyze attention impact"""
        if attention_score < 0.2:
            return "Critical: Very low attention span may significantly reduce your ability to focus on long-form tasks, deep work, and sustained reading. This pattern trains your brain to seek constant novelty."
        elif attention_score < 0.4:
            return "Moderate: Low attention span may reduce your ability to focus on complex tasks. You might find it harder to concentrate on work, reading, or conversations."
        elif attention_score < 0.6:
            return "Mild: Attention span is moderate. Some impact on focus but manageable with conscious effort."
        else:
            return "Positive: Good attention span maintained. You're consuming content thoughtfully."
    
    def _analyze_productivity_impact(self, watch_time: float, activity_level: float) -> str:
        """Analyze productivity impact"""
        if watch_time > 120:  # 2 hours
            return f"Severe: {watch_time:.0f} minutes spent on reels represents significant time that could be invested in productive activities, learning, or meaningful social connections."
        elif watch_time > 60:  # 1 hour
            return f"Moderate: {watch_time:.0f} minutes daily on reels may impact your productivity. Consider if this aligns with your goals and priorities."
        elif watch_time > 30:
            return f"Mild: {watch_time:.0f} minutes is moderate usage. Monitor to ensure it doesn't increase."
        else:
            return f"Low: {watch_time:.0f} minutes is light usage with minimal productivity impact."
    
    def _analyze_habit_risk(self, activity_level: float, watch_time: float) -> str:
        """Analyze habit formation risk"""
        if activity_level > 20 and watch_time > 60:
            return "High Risk: Rapid scrolling combined with high usage time creates strong habit formation. The dopamine-driven feedback loop is reinforcing addictive patterns. This behavior may become automatic and difficult to control."
        elif activity_level > 15 or watch_time > 60:
            return "Medium Risk: Usage patterns show signs of habit formation. The behavior is becoming automatic. Early intervention recommended."
        elif activity_level > 10 or watch_time > 30:
            return "Low Risk: Some habit formation visible but still manageable. Good time to set boundaries."
        else:
            return "Minimal Risk: Usage is controlled and intentional. Low risk of problematic habit formation."
    
    def _analyze_cognitive_impact(self, attention_score: float, activity_level: float) -> str:
        """Analyze cognitive impact"""
        if attention_score < 0.3 and activity_level > 15:
            return "Concerning: Rapid content switching with low attention trains your brain for distraction. This may reduce your capacity for deep thinking, creativity, and problem-solving. Long-term exposure can affect memory consolidation and learning ability."
        elif attention_score < 0.4:
            return "Moderate: Frequent context switching may reduce cognitive performance. You might experience difficulty with sustained attention and working memory."
        else:
            return "Minimal: Cognitive impact is limited. You're maintaining reasonable attention patterns."
    
    def generate_impact_summary(self, impacts: Dict) -> str:
        """Generate human-readable impact summary"""
        severity = impacts['overall_severity']
        
        summary_parts = []
        
        if severity == "high":
            summary_parts.append("⚠️ **High Impact Detected**")
        elif severity == "medium":
            summary_parts.append("⚡ **Moderate Impact**")
        else:
            summary_parts.append("✓ **Low Impact**")
        
        summary_parts.append(f"\n**Attention:** {impacts['attention_impact']}")
        summary_parts.append(f"\n**Productivity:** {impacts['productivity_impact']}")
        summary_parts.append(f"\n**Habit Risk:** {impacts['habit_formation_risk']}")
        summary_parts.append(f"\n**Cognitive:** {impacts['cognitive_impact']}")
        
        return "\n".join(summary_parts)


def get_impact_analyzer() -> ImpactAnalyzer:
    """Get impact analyzer instance"""
    return ImpactAnalyzer()
