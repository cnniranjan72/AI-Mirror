"""
Persona generation service
Creates behavioral archetypes and user profiles
"""
from typing import List, Dict, Optional
import statistics
from app.models.schemas import SessionSummary, BehavioralTraits


class PersonaGenerator:
    """
    Generates behavioral personas from user data
    """
    
    def generate_persona(
        self,
        summaries: List[SessionSummary],
        traits_list: List[BehavioralTraits]
    ) -> Dict:
        """
        Generate comprehensive behavioral persona
        
        Args:
            summaries: List of session summaries
            traits_list: List of behavioral traits
            
        Returns:
            Dictionary with persona information
        """
        if not summaries or not traits_list:
            return {
                "archetype": "Unknown",
                "summary": "Insufficient data to generate persona",
                "strengths": [],
                "weaknesses": [],
                "confidence": 0.0
            }
        
        # Calculate aggregate metrics
        avg_attention = statistics.mean([t.attention_score for t in traits_list])
        avg_engagement = statistics.mean([t.engagement_score for t in traits_list])
        avg_activity = statistics.mean([t.activity_level for t in traits_list])
        
        total_reels = sum([s.reels_count for s in summaries])
        total_sessions = len(summaries)
        
        # Determine archetype
        archetype = self._classify_archetype(avg_attention, avg_engagement, avg_activity)
        
        # Generate summary
        summary = self._generate_summary(archetype, avg_attention, avg_engagement, avg_activity)
        
        # Identify strengths and weaknesses
        strengths = self._identify_strengths(avg_attention, avg_engagement, avg_activity)
        weaknesses = self._identify_weaknesses(avg_attention, avg_engagement, avg_activity)
        
        # Calculate confidence based on data volume
        confidence = min(total_sessions / 10.0, 1.0)
        
        return {
            "archetype": archetype,
            "summary": summary,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "metrics": {
                "attention_score": round(avg_attention, 2),
                "engagement_score": round(avg_engagement, 2),
                "activity_level": round(avg_activity, 2),
                "total_reels": total_reels,
                "total_sessions": total_sessions
            },
            "confidence": round(confidence, 2)
        }
    
    def _classify_archetype(
        self,
        attention: float,
        engagement: float,
        activity: float
    ) -> str:
        """
        Classify user into behavioral archetype
        
        Args:
            attention: Attention score (0-1)
            engagement: Engagement score (0-1)
            activity: Activity level (reels/min)
            
        Returns:
            Archetype name
        """
        # High attention, high engagement
        if attention > 0.6 and engagement > 0.5:
            return "Engaged Curator"
        
        # High attention, low engagement
        if attention > 0.6 and engagement < 0.3:
            return "Passive Observer"
        
        # Low attention, high engagement
        if attention < 0.3 and engagement > 0.5:
            return "Quick-Scroll Engager"
        
        # Low attention, low engagement, high activity
        if attention < 0.3 and engagement < 0.3 and activity > 10:
            return "Rapid Scroller"
        
        # Low attention, low engagement, low activity
        if attention < 0.3 and engagement < 0.3 and activity < 5:
            return "Casual Browser"
        
        # High activity
        if activity > 15:
            return "High-Volume Consumer"
        
        # Moderate across all
        if 0.3 <= attention <= 0.6 and 0.3 <= engagement <= 0.6:
            return "Balanced User"
        
        # Default
        return "Exploratory User"
    
    def _generate_summary(
        self,
        archetype: str,
        attention: float,
        engagement: float,
        activity: float
    ) -> str:
        """
        Generate natural language summary of persona
        
        Args:
            archetype: Classified archetype
            attention: Attention score
            engagement: Engagement score
            activity: Activity level
            
        Returns:
            Summary text
        """
        summaries = {
            "Engaged Curator": (
                "You are a highly engaged user who carefully watches content and actively "
                "curates your feed through likes. You show deep attention and meaningful engagement."
            ),
            "Passive Observer": (
                "You watch content carefully but rarely engage with likes. You're a thoughtful "
                "consumer who prefers observation over interaction."
            ),
            "Quick-Scroll Engager": (
                "You scroll quickly through content but engage with what catches your eye. "
                "You're decisive about what you like despite brief viewing times."
            ),
            "Rapid Scroller": (
                "You scroll through content very quickly with minimal engagement. "
                "You consume high volumes of content but rarely interact with it."
            ),
            "Casual Browser": (
                "You browse Instagram Reels casually with moderate attention and engagement. "
                "You're a light user who doesn't invest heavily in the platform."
            ),
            "High-Volume Consumer": (
                "You consume large volumes of content at a fast pace. You're an active user "
                "who spends significant time scrolling through reels."
            ),
            "Balanced User": (
                "You show balanced behavior across attention, engagement, and activity. "
                "You use Instagram Reels in a moderate, healthy way."
            ),
            "Exploratory User": (
                "You're still developing your usage patterns. Your behavior shows variety "
                "as you explore different types of content."
            )
        }
        
        return summaries.get(archetype, "Your behavioral pattern is still emerging.")
    
    def _identify_strengths(
        self,
        attention: float,
        engagement: float,
        activity: float
    ) -> List[str]:
        """
        Identify behavioral strengths
        
        Args:
            attention: Attention score
            engagement: Engagement score
            activity: Activity level
            
        Returns:
            List of strengths
        """
        strengths = []
        
        if attention > 0.6:
            strengths.append("Strong attention span - you watch content thoughtfully")
        
        if engagement > 0.5:
            strengths.append("High engagement - you actively curate your feed")
        
        if 0.3 <= attention <= 0.6 and 0.3 <= engagement <= 0.6:
            strengths.append("Balanced usage - healthy relationship with content")
        
        if activity < 10:
            strengths.append("Moderate consumption - not excessive scrolling")
        
        if engagement > 0.4 and attention > 0.4:
            strengths.append("Intentional usage - you know what you like")
        
        if not strengths:
            strengths.append("Developing healthy usage patterns")
        
        return strengths
    
    def _identify_weaknesses(
        self,
        attention: float,
        engagement: float,
        activity: float
    ) -> List[str]:
        """
        Identify areas for improvement
        
        Args:
            attention: Attention score
            engagement: Engagement score
            activity: Activity level
            
        Returns:
            List of weaknesses/areas for improvement
        """
        weaknesses = []
        
        if attention < 0.3:
            weaknesses.append("Low attention span - consider watching fewer, higher-quality reels")
        
        if engagement < 0.2:
            weaknesses.append("Low engagement - content may not match your interests")
        
        if activity > 15:
            weaknesses.append("High scrolling activity - may indicate mindless consumption")
        
        if attention < 0.3 and engagement < 0.3:
            weaknesses.append("Passive consumption - not getting meaningful value from content")
        
        if activity > 20 and attention < 0.4:
            weaknesses.append("Rapid scrolling without retention - consider taking breaks")
        
        if not weaknesses:
            weaknesses.append("No significant areas of concern")
        
        return weaknesses
    
    def persona_to_text(self, persona: Dict) -> str:
        """
        Convert persona to natural language text for embedding
        
        Args:
            persona: Persona dictionary
            
        Returns:
            Natural language description
        """
        archetype = persona.get('archetype', 'Unknown')
        summary = persona.get('summary', '')
        strengths = persona.get('strengths', [])
        weaknesses = persona.get('weaknesses', [])
        
        text = f"User archetype: {archetype}. {summary} "
        
        if strengths:
            text += f"Strengths: {', '.join(strengths)}. "
        
        if weaknesses:
            text += f"Areas for improvement: {', '.join(weaknesses)}."
        
        return text


def get_persona_generator() -> PersonaGenerator:
    """Get persona generator instance"""
    return PersonaGenerator()
