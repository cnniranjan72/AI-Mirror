"""
Insight engine for generating human-readable behavioral insights
No heavy LLM required - uses rule-based reasoning
"""
from typing import List, Dict, Any
import statistics


class InsightEngine:
    """
    Generates actionable insights from behavioral data
    Uses rule-based reasoning without external LLMs
    """
    
    def generate_insight(self, query: str, retrieved_docs: List[Dict[str, Any]]) -> Dict:
        """
        Generate insight from query and retrieved documents
        
        Args:
            query: User's query
            retrieved_docs: Retrieved documents from vector store
            
        Returns:
            Dictionary with insight and supporting evidence
        """
        if not retrieved_docs:
            return {
                "insight": "No behavioral data available yet. Start using Instagram to build your profile.",
                "supporting_evidence": [],
                "confidence": 0.0
            }
        
        # Extract metadata from documents
        summaries = []
        traits = []
        trends = []
        
        for doc in retrieved_docs:
            metadata = doc.get('metadata', {})
            doc_type = metadata.get('type', '')
            
            if doc_type == 'session_summary':
                summaries.append(metadata)
            elif doc_type == 'behavioral_traits':
                traits.append(metadata)
            elif doc_type == 'trend':
                trends.append(metadata)
        
        # Analyze query intent
        query_lower = query.lower()
        
        if 'pattern' in query_lower or 'behavior' in query_lower:
            return self._generate_pattern_insight(summaries, traits, trends, retrieved_docs)
        elif 'attention' in query_lower or 'focus' in query_lower:
            return self._generate_attention_insight(summaries, traits, retrieved_docs)
        elif 'engagement' in query_lower or 'like' in query_lower:
            return self._generate_engagement_insight(summaries, traits, retrieved_docs)
        elif 'time' in query_lower or 'usage' in query_lower:
            return self._generate_usage_insight(summaries, retrieved_docs)
        elif 'improve' in query_lower or 'suggest' in query_lower:
            return self._generate_suggestions(summaries, traits, retrieved_docs)
        else:
            return self._generate_general_insight(summaries, traits, trends, retrieved_docs)
    
    def _generate_pattern_insight(
        self,
        summaries: List[Dict],
        traits: List[Dict],
        trends: List[Dict],
        docs: List[Dict]
    ) -> Dict:
        """Generate insight about behavioral patterns"""
        
        if not traits:
            return {
                "insight": "Not enough data to identify behavioral patterns yet.",
                "supporting_evidence": [],
                "confidence": 0.3
            }
        
        # Calculate average traits
        avg_attention = statistics.mean([t.get('attention_score', 0) for t in traits])
        avg_engagement = statistics.mean([t.get('engagement_score', 0) for t in traits])
        
        # Classify behavior
        if avg_attention > 0.6 and avg_engagement > 0.5:
            pattern = "highly engaged viewer"
            description = "You show strong attention and engagement with content."
        elif avg_attention > 0.6 and avg_engagement < 0.3:
            pattern = "passive consumer"
            description = "You watch content carefully but rarely engage with likes."
        elif avg_attention < 0.3 and avg_engagement > 0.5:
            pattern = "quick-scroll engager"
            description = "You scroll quickly but engage with content you like."
        elif avg_attention < 0.3 and avg_engagement < 0.3:
            pattern = "rapid scroller"
            description = "You scroll through content very quickly with minimal engagement."
        else:
            pattern = "moderate user"
            description = "You show balanced attention and engagement patterns."
        
        insight = f"Your behavioral pattern: {pattern}. {description}"
        
        evidence = [doc['text'] for doc in docs[:3]]
        
        return {
            "insight": insight,
            "supporting_evidence": evidence,
            "confidence": 0.8,
            "pattern_type": pattern
        }
    
    def _generate_attention_insight(
        self,
        summaries: List[Dict],
        traits: List[Dict],
        docs: List[Dict]
    ) -> Dict:
        """Generate insight about attention patterns"""
        
        if not summaries:
            return {
                "insight": "No attention data available yet.",
                "supporting_evidence": [],
                "confidence": 0.0
            }
        
        avg_watch_times = [s.get('total_watch_time', 0) / s.get('reels_count', 1) for s in summaries]
        avg_watch = statistics.mean(avg_watch_times) if avg_watch_times else 0
        
        if avg_watch > 10:
            insight = f"High attention span: You watch reels for an average of {avg_watch:.1f} seconds, indicating deep engagement."
            suggestion = "You're consuming content thoughtfully."
        elif avg_watch > 5:
            insight = f"Moderate attention: You watch reels for an average of {avg_watch:.1f} seconds."
            suggestion = "Balanced content consumption."
        else:
            insight = f"Low attention span: You watch reels for only {avg_watch:.1f} seconds on average."
            suggestion = "Consider if you're getting value from such quick scrolling."
        
        evidence = [doc['text'] for doc in docs[:3]]
        
        return {
            "insight": f"{insight} {suggestion}",
            "supporting_evidence": evidence,
            "confidence": 0.85,
            "avg_watch_time": round(avg_watch, 2)
        }
    
    def _generate_engagement_insight(
        self,
        summaries: List[Dict],
        traits: List[Dict],
        docs: List[Dict]
    ) -> Dict:
        """Generate insight about engagement patterns"""
        
        if not summaries:
            return {
                "insight": "No engagement data available yet.",
                "supporting_evidence": [],
                "confidence": 0.0
            }
        
        like_ratios = [s.get('like_ratio', 0) for s in summaries]
        avg_like_ratio = statistics.mean(like_ratios) if like_ratios else 0
        
        if avg_like_ratio > 0.5:
            insight = f"High engagement: You like {avg_like_ratio*100:.0f}% of reels you watch."
            suggestion = "You're actively curating your feed."
        elif avg_like_ratio > 0.2:
            insight = f"Moderate engagement: You like {avg_like_ratio*100:.0f}% of reels."
            suggestion = "Selective engagement with content."
        else:
            insight = f"Low engagement: You like only {avg_like_ratio*100:.0f}% of reels."
            suggestion = "Consider if the content matches your interests."
        
        evidence = [doc['text'] for doc in docs[:3]]
        
        return {
            "insight": f"{insight} {suggestion}",
            "supporting_evidence": evidence,
            "confidence": 0.8,
            "like_ratio": round(avg_like_ratio, 2)
        }
    
    def _generate_usage_insight(
        self,
        summaries: List[Dict],
        docs: List[Dict]
    ) -> Dict:
        """Generate insight about time usage"""
        
        if not summaries:
            return {
                "insight": "No usage data available yet.",
                "supporting_evidence": [],
                "confidence": 0.0
            }
        
        total_watch = sum([s.get('total_watch_time', 0) for s in summaries])
        total_reels = sum([s.get('reels_count', 0) for s in summaries])
        
        total_minutes = total_watch / 60
        
        if total_minutes > 60:
            insight = f"Heavy usage: You've spent {total_minutes:.0f} minutes watching {total_reels} reels."
            suggestion = "Consider setting time limits for healthier usage."
        elif total_minutes > 20:
            insight = f"Moderate usage: You've spent {total_minutes:.0f} minutes watching {total_reels} reels."
            suggestion = "Balanced usage pattern."
        else:
            insight = f"Light usage: You've spent {total_minutes:.0f} minutes watching {total_reels} reels."
            suggestion = "Minimal time investment in Instagram Reels."
        
        evidence = [doc['text'] for doc in docs[:3]]
        
        return {
            "insight": f"{insight} {suggestion}",
            "supporting_evidence": evidence,
            "confidence": 0.9,
            "total_minutes": round(total_minutes, 1),
            "total_reels": total_reels
        }
    
    def _generate_suggestions(
        self,
        summaries: List[Dict],
        traits: List[Dict],
        docs: List[Dict]
    ) -> Dict:
        """Generate actionable suggestions"""
        
        if not traits:
            return {
                "insight": "Not enough data for personalized suggestions yet.",
                "supporting_evidence": [],
                "confidence": 0.3
            }
        
        avg_attention = statistics.mean([t.get('attention_score', 0) for t in traits])
        avg_engagement = statistics.mean([t.get('engagement_score', 0) for t in traits])
        
        suggestions = []
        
        if avg_attention < 0.3:
            suggestions.append("Your attention span is low - try watching fewer, higher-quality reels")
        
        if avg_engagement < 0.2:
            suggestions.append("Low engagement suggests content mismatch - curate your feed better")
        
        if avg_attention < 0.3 and avg_engagement < 0.3:
            suggestions.append("Consider taking a break - you're scrolling without meaningful engagement")
        
        if not suggestions:
            suggestions.append("Your usage patterns are healthy - maintain this balance")
        
        insight = "Suggestions: " + ". ".join(suggestions) + "."
        evidence = [doc['text'] for doc in docs[:3]]
        
        return {
            "insight": insight,
            "supporting_evidence": evidence,
            "confidence": 0.75,
            "suggestions": suggestions
        }
    
    def _generate_general_insight(
        self,
        summaries: List[Dict],
        traits: List[Dict],
        trends: List[Dict],
        docs: List[Dict]
    ) -> Dict:
        """Generate general behavioral insight"""
        
        if not summaries:
            return {
                "insight": "Start using Instagram to build your behavioral profile.",
                "supporting_evidence": [],
                "confidence": 0.0
            }
        
        total_reels = sum([s.get('reels_count', 0) for s in summaries])
        total_sessions = len(summaries)
        
        if traits:
            avg_attention = statistics.mean([t.get('attention_score', 0) for t in traits])
            avg_engagement = statistics.mean([t.get('engagement_score', 0) for t in traits])
            
            insight = (
                f"You've watched {total_reels} reels across {total_sessions} sessions. "
                f"Your attention score is {avg_attention:.2f} and engagement score is {avg_engagement:.2f}."
            )
        else:
            insight = f"You've watched {total_reels} reels across {total_sessions} sessions."
        
        evidence = [doc['text'] for doc in docs[:3]]
        
        return {
            "insight": insight,
            "supporting_evidence": evidence,
            "confidence": 0.7
        }


def get_insight_engine() -> InsightEngine:
    """Get insight engine instance"""
    return InsightEngine()
