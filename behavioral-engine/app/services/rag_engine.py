"""
RAG Engine - Generates responses using retrieved context
Template-based response generation without external LLMs
"""
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Generates responses using RAG pattern with template-based approach
    """
    
    def generate_response(
        self,
        query: str,
        context: Dict,
        persona: Optional[Dict] = None
    ) -> Dict:
        """
        Generate response from query and context
        
        Args:
            query: User query
            context: Retrieved context
            persona: User persona (optional)
            
        Returns:
            Response dictionary with text and metadata
        """
        query_lower = query.lower()
        
        # Detect query intent
        intent = self._detect_intent(query_lower)
        
        # Generate response based on intent
        if intent == "why_scrolling":
            return self._respond_why_scrolling(context, persona)
        elif intent == "addiction":
            return self._respond_addiction(context, persona)
        elif intent == "behavior_pattern":
            return self._respond_behavior_pattern(context, persona)
        elif intent == "improvement":
            return self._respond_improvement(context, persona)
        elif intent == "time_usage":
            return self._respond_time_usage(context, persona)
        elif intent == "attention":
            return self._respond_attention(context, persona)
        elif intent == "engagement":
            return self._respond_engagement(context, persona)
        else:
            return self._respond_general(context, persona)
    
    def _detect_intent(self, query: str) -> str:
        """Detect query intent from text"""
        if "why" in query and ("scroll" in query or "addicted" in query or "reels" in query):
            return "why_scrolling"
        elif "addict" in query or "hooked" in query:
            return "addiction"
        elif "pattern" in query or "behavior" in query:
            return "behavior_pattern"
        elif "improve" in query or "better" in query or "help" in query or "suggest" in query:
            return "improvement"
        elif "time" in query or "much" in query or "usage" in query:
            return "time_usage"
        elif "attention" in query or "focus" in query:
            return "attention"
        elif "engagement" in query or "like" in query or "interact" in query:
            return "engagement"
        else:
            return "general"
    
    def _respond_why_scrolling(self, context: Dict, persona: Optional[Dict]) -> Dict:
        """Respond to 'why am I scrolling so much' type queries"""
        traits = context.get("behavioral_traits", [])
        summaries = context.get("session_summaries", [])
        
        if not traits:
            return {
                "response": "I don't have enough data about your behavior yet. Use Instagram for a few sessions so I can analyze your patterns.",
                "confidence": 0.2,
                "context_used": []
            }
        
        # Extract key metrics from context
        attention_scores = [t["metadata"].get("attention_score", 0) for t in traits if "metadata" in t]
        engagement_scores = [t["metadata"].get("engagement_score", 0) for t in traits if "metadata" in t]
        
        avg_attention = sum(attention_scores) / len(attention_scores) if attention_scores else 0
        avg_engagement = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0
        
        # Build response
        response_parts = []
        
        if avg_attention < 0.3:
            response_parts.append("Your attention span is low - you're scrolling quickly without deeply engaging with content.")
        
        if avg_engagement < 0.3:
            response_parts.append("You rarely like or interact with reels, suggesting the content isn't resonating with you.")
        
        if avg_attention < 0.3 and avg_engagement < 0.3:
            response_parts.append("This pattern indicates you're scrolling out of habit or boredom rather than genuine interest.")
        
        if persona:
            archetype = persona.get("archetype", "")
            if "Rapid Scroller" in archetype or "Quick-Scroll" in archetype:
                response_parts.append(f"Your behavioral archetype is '{archetype}' - characterized by fast scrolling with minimal retention.")
        
        response_parts.append("The algorithm keeps you engaged through novelty and dopamine hits, even when content quality is low.")
        
        response = " ".join(response_parts)
        context_used = [t["text"][:100] for t in traits[:3]]
        
        return {
            "response": response,
            "confidence": 0.8,
            "context_used": context_used,
            "suggested_actions": [
                "Set a time limit for sessions",
                "Slow down and watch each reel fully",
                "Curate your feed by liking quality content"
            ]
        }
    
    def _respond_addiction(self, context: Dict, persona: Optional[Dict]) -> Dict:
        """Respond to addiction-related queries"""
        summaries = context.get("session_summaries", [])
        traits = context.get("behavioral_traits", [])
        
        if not summaries:
            return {
                "response": "I need more usage data to assess addiction patterns.",
                "confidence": 0.2,
                "context_used": []
            }
        
        # Calculate total usage
        total_reels = sum([s["metadata"].get("reels_count", 0) for s in summaries if "metadata" in s])
        total_time = sum([s["metadata"].get("total_watch_time", 0) for s in summaries if "metadata" in s])
        
        response_parts = []
        
        if total_time > 3600:  # More than 1 hour
            response_parts.append(f"You've spent {total_time/60:.0f} minutes watching {total_reels} reels.")
            response_parts.append("This indicates significant usage that may be affecting your productivity.")
        
        if traits:
            avg_attention = sum([t["metadata"].get("attention_score", 0) for t in traits if "metadata" in t]) / len(traits)
            if avg_attention < 0.3:
                response_parts.append("Your low attention span suggests you're seeking constant stimulation rather than meaningful content.")
        
        response_parts.append("Addiction patterns emerge when the app becomes a default response to boredom or stress.")
        response_parts.append("The infinite scroll design is engineered to keep you engaged beyond your intended usage.")
        
        response = " ".join(response_parts)
        
        return {
            "response": response,
            "confidence": 0.85,
            "context_used": [s["text"][:100] for s in summaries[:2]],
            "suggested_actions": [
                "Set strict daily time limits",
                "Remove Instagram from your home screen",
                "Replace scrolling with a healthier habit"
            ]
        }
    
    def _respond_behavior_pattern(self, context: Dict, persona: Optional[Dict]) -> Dict:
        """Respond to behavior pattern queries"""
        if persona:
            archetype = persona.get("archetype", "Unknown")
            summary = persona.get("summary", "")
            strengths = persona.get("strengths", [])
            weaknesses = persona.get("weaknesses", [])
            
            response = f"Your behavioral pattern: {archetype}. {summary} "
            
            if strengths:
                response += f"Strengths: {', '.join(strengths[:2])}. "
            
            if weaknesses:
                response += f"Areas for improvement: {', '.join(weaknesses[:2])}."
            
            return {
                "response": response,
                "confidence": 0.9,
                "context_used": [summary],
                "suggested_actions": ["Review your persona profile for detailed insights"]
            }
        
        traits = context.get("behavioral_traits", [])
        if traits:
            response = "Your behavior shows patterns of "
            
            avg_attention = sum([t["metadata"].get("attention_score", 0) for t in traits if "metadata" in t]) / len(traits)
            avg_engagement = sum([t["metadata"].get("engagement_score", 0) for t in traits if "metadata" in t]) / len(traits)
            
            if avg_attention > 0.6:
                response += "high attention and "
            else:
                response += "low attention and "
            
            if avg_engagement > 0.5:
                response += "strong engagement."
            else:
                response += "weak engagement."
            
            return {
                "response": response,
                "confidence": 0.7,
                "context_used": [t["text"][:100] for t in traits[:2]]
            }
        
        return {
            "response": "I need more data to identify your behavior patterns.",
            "confidence": 0.3,
            "context_used": []
        }
    
    def _respond_improvement(self, context: Dict, persona: Optional[Dict]) -> Dict:
        """Respond to improvement/suggestion queries"""
        traits = context.get("behavioral_traits", [])
        
        suggestions = []
        
        if traits:
            avg_attention = sum([t["metadata"].get("attention_score", 0) for t in traits if "metadata" in t]) / len(traits)
            avg_engagement = sum([t["metadata"].get("engagement_score", 0) for t in traits if "metadata" in t]) / len(traits)
            
            if avg_attention < 0.3:
                suggestions.append("Slow down your scrolling - watch each reel fully before moving on")
            
            if avg_engagement < 0.2:
                suggestions.append("Curate your feed by liking content that adds value")
            
            if avg_attention < 0.3 and avg_engagement < 0.3:
                suggestions.append("Take regular breaks - set a timer for every 10 minutes")
                suggestions.append("Ask yourself: Is this content improving my life?")
        
        if not suggestions:
            suggestions = [
                "Set daily time limits",
                "Use app timers to track usage",
                "Replace scrolling with productive activities"
            ]
        
        response = "Here's how to improve: " + ". ".join(suggestions) + "."
        
        return {
            "response": response,
            "confidence": 0.8,
            "context_used": [t["text"][:100] for t in traits[:2]] if traits else [],
            "suggested_actions": suggestions
        }
    
    def _respond_time_usage(self, context: Dict, persona: Optional[Dict]) -> Dict:
        """Respond to time usage queries"""
        summaries = context.get("session_summaries", [])
        
        if not summaries:
            return {
                "response": "No usage data available yet.",
                "confidence": 0.2,
                "context_used": []
            }
        
        total_time = sum([s["metadata"].get("total_watch_time", 0) for s in summaries if "metadata" in s])
        total_reels = sum([s["metadata"].get("reels_count", 0) for s in summaries if "metadata" in s])
        
        minutes = total_time / 60
        
        response = f"You've spent {minutes:.0f} minutes watching {total_reels} reels. "
        
        if minutes > 60:
            response += "This is significant time that could be invested in other activities. "
        elif minutes > 30:
            response += "Moderate usage - consider if this aligns with your goals. "
        else:
            response += "Light usage - relatively healthy pattern. "
        
        return {
            "response": response,
            "confidence": 0.9,
            "context_used": [s["text"][:100] for s in summaries[:2]]
        }
    
    def _respond_attention(self, context: Dict, persona: Optional[Dict]) -> Dict:
        """Respond to attention-related queries"""
        traits = context.get("behavioral_traits", [])
        
        if not traits:
            return {
                "response": "No attention data available yet.",
                "confidence": 0.2,
                "context_used": []
            }
        
        avg_attention = sum([t["metadata"].get("attention_score", 0) for t in traits if "metadata" in t]) / len(traits)
        
        if avg_attention > 0.6:
            response = f"Your attention score is {avg_attention:.2f} - you watch content carefully and thoughtfully."
        elif avg_attention > 0.3:
            response = f"Your attention score is {avg_attention:.2f} - moderate attention span."
        else:
            response = f"Your attention score is {avg_attention:.2f} - low attention, indicating rapid scrolling."
        
        return {
            "response": response,
            "confidence": 0.85,
            "context_used": [t["text"][:100] for t in traits[:2]]
        }
    
    def _respond_engagement(self, context: Dict, persona: Optional[Dict]) -> Dict:
        """Respond to engagement-related queries"""
        traits = context.get("behavioral_traits", [])
        
        if not traits:
            return {
                "response": "No engagement data available yet.",
                "confidence": 0.2,
                "context_used": []
            }
        
        avg_engagement = sum([t["metadata"].get("engagement_score", 0) for t in traits if "metadata" in t]) / len(traits)
        
        if avg_engagement > 0.5:
            response = f"Your engagement score is {avg_engagement:.2f} - you actively interact with content you enjoy."
        elif avg_engagement > 0.2:
            response = f"Your engagement score is {avg_engagement:.2f} - selective engagement."
        else:
            response = f"Your engagement score is {avg_engagement:.2f} - low engagement, suggesting content mismatch."
        
        return {
            "response": response,
            "confidence": 0.85,
            "context_used": [t["text"][:100] for t in traits[:2]]
        }
    
    def _respond_general(self, context: Dict, persona: Optional[Dict]) -> Dict:
        """General response when intent is unclear"""
        raw_docs = context.get("raw_documents", [])
        
        if not raw_docs:
            return {
                "response": "I don't have enough behavioral data yet. Start using Instagram so I can analyze your patterns.",
                "confidence": 0.3,
                "context_used": []
            }
        
        # Summarize available context
        response = "Based on your behavioral data: "
        
        if context.get("behavioral_traits"):
            response += "I can see your attention and engagement patterns. "
        
        if context.get("trends"):
            response += "I've detected trends in your behavior over time. "
        
        if persona:
            response += f"Your behavioral archetype is '{persona.get('archetype', 'Unknown')}'. "
        
        response += "Ask me specific questions about your behavior, patterns, or how to improve."
        
        return {
            "response": response,
            "confidence": 0.6,
            "context_used": [doc["text"][:100] for doc in raw_docs[:2]]
        }


def get_rag_engine() -> RAGEngine:
    """Get RAG engine instance"""
    return RAGEngine()
