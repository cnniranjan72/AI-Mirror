"""
Trend detection service
Analyzes behavioral patterns across multiple sessions
"""
from typing import List, Dict, Optional
from datetime import datetime
import statistics
from app.models.schemas import SessionSummary, BehavioralTraits


class TrendAnalyzer:
    """
    Analyzes trends across sessions to detect behavioral changes
    """
    
    def __init__(self, window_size: int = 5):
        """
        Initialize trend analyzer
        
        Args:
            window_size: Number of recent sessions to analyze
        """
        self.window_size = window_size
    
    def detect_attention_trend(self, summaries: List[SessionSummary]) -> Dict:
        """
        Detect trend in attention (watch time) across sessions
        
        Args:
            summaries: List of session summaries (chronologically ordered)
            
        Returns:
            Dictionary with trend information
        """
        if len(summaries) < 2:
            return {
                "type": "trend",
                "category": "attention",
                "direction": "stable",
                "description": "Insufficient data for trend analysis",
                "confidence": 0.0
            }
        
        # Get recent sessions
        recent = summaries[-self.window_size:]
        watch_times = [s.avg_watch_time for s in recent]
        
        # Calculate trend
        if len(watch_times) >= 3:
            # Simple linear trend detection
            first_half = statistics.mean(watch_times[:len(watch_times)//2])
            second_half = statistics.mean(watch_times[len(watch_times)//2:])
            
            change_pct = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0
            
            if change_pct > 15:
                direction = "increasing"
                description = f"User attention increasing over last {len(recent)} sessions (↑{abs(change_pct):.1f}%)"
            elif change_pct < -15:
                direction = "decreasing"
                description = f"User attention decreasing over last {len(recent)} sessions (↓{abs(change_pct):.1f}%)"
            else:
                direction = "stable"
                description = f"User attention stable over last {len(recent)} sessions"
            
            confidence = min(abs(change_pct) / 50.0, 1.0)
        else:
            direction = "stable"
            description = "Insufficient data for trend analysis"
            confidence = 0.0
        
        return {
            "type": "trend",
            "category": "attention",
            "direction": direction,
            "description": description,
            "confidence": round(confidence, 2),
            "data_points": len(recent)
        }
    
    def detect_engagement_trend(self, summaries: List[SessionSummary]) -> Dict:
        """
        Detect trend in engagement (like ratio) across sessions
        
        Args:
            summaries: List of session summaries
            
        Returns:
            Dictionary with trend information
        """
        if len(summaries) < 2:
            return {
                "type": "trend",
                "category": "engagement",
                "direction": "stable",
                "description": "Insufficient data for trend analysis",
                "confidence": 0.0
            }
        
        recent = summaries[-self.window_size:]
        like_ratios = [s.like_ratio for s in recent]
        
        if len(like_ratios) >= 3:
            first_half = statistics.mean(like_ratios[:len(like_ratios)//2])
            second_half = statistics.mean(like_ratios[len(like_ratios)//2:])
            
            change = second_half - first_half
            
            if change > 0.1:
                direction = "increasing"
                description = f"User engagement increasing over last {len(recent)} sessions"
            elif change < -0.1:
                direction = "decreasing"
                description = f"User engagement decreasing over last {len(recent)} sessions"
            else:
                direction = "stable"
                description = f"User engagement stable over last {len(recent)} sessions"
            
            confidence = min(abs(change) / 0.5, 1.0)
        else:
            direction = "stable"
            description = "Insufficient data for trend analysis"
            confidence = 0.0
        
        return {
            "type": "trend",
            "category": "engagement",
            "direction": direction,
            "description": description,
            "confidence": round(confidence, 2),
            "data_points": len(recent)
        }
    
    def detect_activity_spikes(self, summaries: List[SessionSummary]) -> Dict:
        """
        Detect unusual spikes in activity
        
        Args:
            summaries: List of session summaries
            
        Returns:
            Dictionary with spike information
        """
        if len(summaries) < 3:
            return {
                "type": "trend",
                "category": "activity",
                "spike_detected": False,
                "description": "Insufficient data for spike detection"
            }
        
        recent = summaries[-self.window_size:]
        reel_counts = [s.reels_count for s in recent]
        
        avg = statistics.mean(reel_counts)
        stdev = statistics.stdev(reel_counts) if len(reel_counts) > 1 else 0
        
        # Check if latest session is a spike (>2 std deviations)
        latest = reel_counts[-1]
        
        if stdev > 0 and latest > avg + 2 * stdev:
            spike_detected = True
            description = f"Unusual activity spike detected: {latest} reels (avg: {avg:.1f})"
        elif stdev > 0 and latest < avg - 2 * stdev:
            spike_detected = True
            description = f"Unusual activity drop detected: {latest} reels (avg: {avg:.1f})"
        else:
            spike_detected = False
            description = f"Normal activity levels: {latest} reels (avg: {avg:.1f})"
        
        return {
            "type": "trend",
            "category": "activity",
            "spike_detected": spike_detected,
            "description": description,
            "latest_count": latest,
            "average_count": round(avg, 1)
        }
    
    def detect_behavioral_drift(self, traits_list: List[BehavioralTraits]) -> Dict:
        """
        Detect overall behavioral drift across sessions
        
        Args:
            traits_list: List of behavioral traits
            
        Returns:
            Dictionary with drift information
        """
        if len(traits_list) < 3:
            return {
                "type": "trend",
                "category": "drift",
                "drift_detected": False,
                "description": "Insufficient data for drift detection"
            }
        
        recent = traits_list[-self.window_size:]
        
        # Calculate variance in attention and engagement
        attention_scores = [t.attention_score for t in recent]
        engagement_scores = [t.engagement_score for t in recent]
        
        attention_var = statistics.variance(attention_scores) if len(attention_scores) > 1 else 0
        engagement_var = statistics.variance(engagement_scores) if len(engagement_scores) > 1 else 0
        
        # High variance indicates drift
        drift_score = (attention_var + engagement_var) / 2
        
        if drift_score > 0.1:
            drift_detected = True
            description = "Significant behavioral drift detected - user behavior is inconsistent"
        else:
            drift_detected = False
            description = "Stable behavioral patterns - user behavior is consistent"
        
        return {
            "type": "trend",
            "category": "drift",
            "drift_detected": drift_detected,
            "drift_score": round(drift_score, 3),
            "description": description
        }
    
    def generate_trend_summary(
        self,
        summaries: List[SessionSummary],
        traits_list: List[BehavioralTraits]
    ) -> str:
        """
        Generate comprehensive trend summary text for embedding
        
        Args:
            summaries: List of session summaries
            traits_list: List of behavioral traits
            
        Returns:
            Natural language trend summary
        """
        attention_trend = self.detect_attention_trend(summaries)
        engagement_trend = self.detect_engagement_trend(summaries)
        activity_spike = self.detect_activity_spikes(summaries)
        drift = self.detect_behavioral_drift(traits_list)
        
        summary_parts = [
            f"Behavioral trends: {attention_trend['description']}.",
            f"{engagement_trend['description']}.",
            f"{activity_spike['description']}.",
            f"{drift['description']}."
        ]
        
        return " ".join(summary_parts)


def get_trend_analyzer() -> TrendAnalyzer:
    """Get trend analyzer instance"""
    return TrendAnalyzer(window_size=5)
