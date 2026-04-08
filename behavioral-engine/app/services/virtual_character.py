"""
Virtual Character Layer
Adds persona-aware voice and tone to responses
"""
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class VirtualCharacter:
    """
    Generates persona-aware responses with reflective, analytical tone
    Acts as an "AI Mirror" - reflective and insightful
    """
    
    def generate_persona_voice(
        self,
        response: str,
        persona: Optional[Dict] = None,
        context: Optional[Dict] = None
    ) -> str:
        """
        Add persona-aware voice to response
        
        Args:
            response: Base response text
            persona: User persona data
            context: Additional context
            
        Returns:
            Enhanced response with persona voice
        """
        if not persona:
            return self._add_mirror_voice(response)
        
        archetype = persona.get("archetype", "")
        
        # Add archetype-specific framing
        if "Rapid Scroller" in archetype:
            prefix = "As a rapid scroller, "
        elif "Engaged Curator" in archetype:
            prefix = "As an engaged curator, "
        elif "Passive Observer" in archetype:
            prefix = "As a passive observer, "
        elif "Quick-Scroll Engager" in archetype:
            prefix = "As someone who scrolls quickly but engages selectively, "
        else:
            prefix = ""
        
        # Add reflective tone
        enhanced = self._add_mirror_voice(response, prefix)
        
        return enhanced
    
    def _add_mirror_voice(self, response: str, prefix: str = "") -> str:
        """
        Add AI Mirror voice characteristics
        
        Args:
            response: Base response
            prefix: Optional prefix
            
        Returns:
            Enhanced response
        """
        # Add reflective framing if not already present
        reflective_starters = [
            "Your behavior suggests",
            "You tend to",
            "This pattern indicates",
            "Based on your",
            "I notice that",
            "Your data shows"
        ]
        
        has_reflective_start = any(response.startswith(starter) for starter in reflective_starters)
        
        if not has_reflective_start and prefix:
            response = prefix + response
        
        return response
    
    def add_empathy(self, response: str, sentiment: str = "neutral") -> str:
        """
        Add empathetic elements to response
        
        Args:
            response: Base response
            sentiment: Sentiment (positive, negative, neutral)
            
        Returns:
            Response with empathy
        """
        if sentiment == "negative":
            # User might be struggling
            empathy_phrases = [
                "I understand this can be challenging. ",
                "It's common to struggle with this. ",
                "Many people face similar patterns. "
            ]
            prefix = empathy_phrases[0]
            return prefix + response
        
        elif sentiment == "positive":
            # User is doing well
            encouragement = [
                "You're showing positive patterns. ",
                "This is encouraging progress. ",
                "You're on the right track. "
            ]
            prefix = encouragement[0]
            return prefix + response
        
        return response
    
    def add_actionable_close(
        self,
        response: str,
        suggestions: Optional[list] = None
    ) -> str:
        """
        Add actionable closing to response
        
        Args:
            response: Base response
            suggestions: Optional list of suggestions
            
        Returns:
            Response with actionable close
        """
        if suggestions:
            close = f"\n\nNext steps: {', '.join(suggestions[:2])}."
            return response + close
        
        return response
    
    def format_as_mirror(
        self,
        response: str,
        persona: Optional[Dict] = None,
        sentiment: str = "neutral",
        suggestions: Optional[list] = None
    ) -> str:
        """
        Complete formatting as AI Mirror
        
        Args:
            response: Base response
            persona: User persona
            sentiment: Response sentiment
            suggestions: Action suggestions
            
        Returns:
            Fully formatted response
        """
        # Add persona voice
        response = self.generate_persona_voice(response, persona)
        
        # Add empathy
        response = self.add_empathy(response, sentiment)
        
        # Add actionable close
        response = self.add_actionable_close(response, suggestions)
        
        return response


def get_virtual_character() -> VirtualCharacter:
    """Get virtual character instance"""
    return VirtualCharacter()
