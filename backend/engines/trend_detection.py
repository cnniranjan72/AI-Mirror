"""
Trend Detection Engine
Detects emerging, declining, and stable behavioral trends
"""
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

from backend.shared.contracts import BehaviorEvent, BehaviorCluster


logger = logging.getLogger(__name__)


class TrendType:
    """Trend types"""
    EMERGING = "emerging"
    DECLINING = "declining"
    STABLE = "stable"
    SPIKE = "spike"
    CYCLICAL = "cyclical"


class Trend(Dict[str, Any]):
    """
    Trend representation
    
    Contains:
    - trend_type: Type of trend
    - topic: Primary topic
    - score: Trend strength score (0-1)
    - confidence: Confidence in trend (0-1)
    - growth_rate: Rate of growth/decline
    - evidence: Supporting evidence
    - time_window: Time period analyzed
    - metadata: Additional information
    """
    pass


class TrendDetectionEngine:
    """
    Trend Detection Engine
    
    Responsibilities:
    - Detect emerging interests
    - Detect declining interests
    - Detect stable interests
    - Analyze creator influence
    - Track topic drift
    - Track behavior drift
    - Track attention drift
    - Analyze learning consistency
    - Detect daily patterns
    - Detect weekly patterns
    - Detect monthly patterns
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Trend Detection Engine
        
        Args:
            config: Engine configuration
        """
        self.config = config or {}
        self.emerging_threshold = self.config.get("emerging_threshold", 0.5)
        self.declining_threshold = self.config.get("declining_threshold", -0.3)
        self.min_data_points = self.config.get("min_data_points", 5)
        
        logger.info("TrendDetectionEngine initialized")
    
    def detect_all_trends(
        self,
        events: List[BehaviorEvent],
        clusters: List[BehaviorCluster],
        lookback_days: int = 30
    ) -> Dict[str, List[Trend]]:
        """
        Detect all types of trends
        
        Args:
            events: List of behavioral events
            clusters: List of behavior clusters
            lookback_days: Days to analyze
            
        Returns:
            Dictionary of trend types to trends
        """
        try:
            logger.info(f"Detecting trends from {len(events)} events and {len(clusters)} clusters")
            
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            recent_events = [e for e in events if e.timestamp >= cutoff_date]
            recent_clusters = [c for c in clusters if c.last_seen >= cutoff_date]
            
            trends = {
                "emerging_interests": self.detect_emerging_interests(recent_events, recent_clusters),
                "declining_interests": self.detect_declining_interests(recent_events, recent_clusters),
                "stable_interests": self.detect_stable_interests(recent_events, recent_clusters),
                "creator_influence": self.analyze_creator_influence(recent_events),
                "topic_drift": self.detect_topic_drift(recent_events, lookback_days),
                "attention_drift": self.detect_attention_drift(recent_events, lookback_days),
                "daily_patterns": self.detect_daily_patterns(recent_events),
                "weekly_patterns": self.detect_weekly_patterns(recent_events)
            }
            
            logger.info(f"Detected {sum(len(v) for v in trends.values())} total trends")
            return trends
            
        except Exception as e:
            logger.error(f"Error detecting trends: {str(e)}", exc_info=True)
            return {}
    
    def detect_emerging_interests(
        self,
        events: List[BehaviorEvent],
        clusters: List[BehaviorCluster]
    ) -> List[Trend]:
        """
        Detect emerging interests
        
        Args:
            events: Recent events
            clusters: Recent clusters
            
        Returns:
            List of emerging interest trends
        """
        try:
            emerging_trends = []
            
            for cluster in clusters:
                # Check if cluster is growing rapidly
                if cluster.growth_rate > self.emerging_threshold:
                    # Check if it's recent (started in last 2 weeks)
                    days_since_first = (datetime.utcnow() - cluster.first_seen).days
                    
                    if days_since_first <= 14:
                        trend = Trend({
                            "trend_type": TrendType.EMERGING,
                            "topic": cluster.primary_topic,
                            "score": min(1.0, cluster.growth_rate),
                            "confidence": cluster.confidence,
                            "growth_rate": cluster.growth_rate,
                            "evidence": {
                                "occurrence_count": cluster.occurrence_count,
                                "days_active": days_since_first,
                                "engagement_rate": cluster.engagement_rate,
                                "creators": cluster.creators[:5]
                            },
                            "time_window": f"Last {days_since_first} days",
                            "metadata": {
                                "cluster_id": cluster.cluster_id,
                                "related_topics": cluster.related_topics
                            }
                        })
                        emerging_trends.append(trend)
            
            # Sort by growth rate
            emerging_trends.sort(key=lambda t: t["growth_rate"], reverse=True)
            
            logger.info(f"Detected {len(emerging_trends)} emerging interests")
            return emerging_trends
            
        except Exception as e:
            logger.error(f"Error detecting emerging interests: {str(e)}", exc_info=True)
            return []
    
    def detect_declining_interests(
        self,
        events: List[BehaviorEvent],
        clusters: List[BehaviorCluster]
    ) -> List[Trend]:
        """
        Detect declining interests
        
        Args:
            events: Recent events
            clusters: Recent clusters
            
        Returns:
            List of declining interest trends
        """
        try:
            declining_trends = []
            
            for cluster in clusters:
                # Check if cluster hasn't been updated recently
                days_since_last = (datetime.utcnow() - cluster.last_seen).days
                
                if days_since_last > 7:  # No activity in last week
                    # Calculate decline rate
                    days_active = (cluster.last_seen - cluster.first_seen).days or 1
                    decline_rate = -1.0 * (days_since_last / days_active)
                    
                    if decline_rate < self.declining_threshold:
                        trend = Trend({
                            "trend_type": TrendType.DECLINING,
                            "topic": cluster.primary_topic,
                            "score": abs(decline_rate),
                            "confidence": cluster.confidence * 0.8,  # Lower confidence for decline
                            "growth_rate": decline_rate,
                            "evidence": {
                                "days_since_last_seen": days_since_last,
                                "previous_occurrence_count": cluster.occurrence_count,
                                "previous_engagement_rate": cluster.engagement_rate
                            },
                            "time_window": f"Last seen {days_since_last} days ago",
                            "metadata": {
                                "cluster_id": cluster.cluster_id,
                                "related_topics": cluster.related_topics
                            }
                        })
                        declining_trends.append(trend)
            
            # Sort by decline rate
            declining_trends.sort(key=lambda t: t["score"], reverse=True)
            
            logger.info(f"Detected {len(declining_trends)} declining interests")
            return declining_trends
            
        except Exception as e:
            logger.error(f"Error detecting declining interests: {str(e)}", exc_info=True)
            return []
    
    def detect_stable_interests(
        self,
        events: List[BehaviorEvent],
        clusters: List[BehaviorCluster]
    ) -> List[Trend]:
        """
        Detect stable interests
        
        Args:
            events: Recent events
            clusters: Recent clusters
            
        Returns:
            List of stable interest trends
        """
        try:
            stable_trends = []
            
            for cluster in clusters:
                # Check if cluster has consistent activity
                days_active = (cluster.last_seen - cluster.first_seen).days or 1
                
                if days_active >= 14:  # At least 2 weeks of activity
                    # Check if growth rate is steady
                    if abs(cluster.growth_rate - cluster.occurrence_count / days_active) < 0.2:
                        trend = Trend({
                            "trend_type": TrendType.STABLE,
                            "topic": cluster.primary_topic,
                            "score": cluster.confidence,
                            "confidence": cluster.confidence,
                            "growth_rate": cluster.growth_rate,
                            "evidence": {
                                "days_active": days_active,
                                "occurrence_count": cluster.occurrence_count,
                                "engagement_rate": cluster.engagement_rate,
                                "consistency": 1.0 - abs(cluster.growth_rate - cluster.occurrence_count / days_active)
                            },
                            "time_window": f"Last {days_active} days",
                            "metadata": {
                                "cluster_id": cluster.cluster_id,
                                "related_topics": cluster.related_topics
                            }
                        })
                        stable_trends.append(trend)
            
            # Sort by confidence
            stable_trends.sort(key=lambda t: t["confidence"], reverse=True)
            
            logger.info(f"Detected {len(stable_trends)} stable interests")
            return stable_trends
            
        except Exception as e:
            logger.error(f"Error detecting stable interests: {str(e)}", exc_info=True)
            return []
    
    def analyze_creator_influence(
        self,
        events: List[BehaviorEvent]
    ) -> List[Trend]:
        """
        Analyze creator influence
        
        Args:
            events: Recent events
            
        Returns:
            List of creator influence trends
        """
        try:
            creator_stats = defaultdict(lambda: {
                "view_count": 0,
                "total_watch_time": 0.0,
                "engagement_count": 0,
                "topics": []
            })
            
            for event in events:
                if event.creator:
                    creator_stats[event.creator]["view_count"] += 1
                    creator_stats[event.creator]["total_watch_time"] += event.watch_time
                    
                    if event.liked or event.saved or event.shared or event.commented:
                        creator_stats[event.creator]["engagement_count"] += 1
                    
                    creator_stats[event.creator]["topics"].extend(event.hashtags or [])
            
            influence_trends = []
            
            for creator, stats in creator_stats.items():
                if stats["view_count"] >= self.min_data_points:
                    engagement_rate = stats["engagement_count"] / stats["view_count"]
                    avg_watch_time = stats["total_watch_time"] / stats["view_count"]
                    
                    # Calculate influence score
                    influence_score = (
                        0.4 * min(1.0, stats["view_count"] / 20) +  # View frequency
                        0.3 * engagement_rate +  # Engagement
                        0.3 * min(1.0, avg_watch_time / 30)  # Watch time
                    )
                    
                    top_topics = Counter(stats["topics"]).most_common(5)
                    
                    trend = Trend({
                        "trend_type": "creator_influence",
                        "topic": creator,
                        "score": influence_score,
                        "confidence": min(1.0, stats["view_count"] / 10),
                        "growth_rate": 0.0,  # Not applicable
                        "evidence": {
                            "view_count": stats["view_count"],
                            "avg_watch_time": round(avg_watch_time, 2),
                            "engagement_rate": round(engagement_rate, 2),
                            "top_topics": [t[0] for t in top_topics]
                        },
                        "time_window": "Recent period",
                        "metadata": {
                            "creator": creator
                        }
                    })
                    influence_trends.append(trend)
            
            # Sort by influence score
            influence_trends.sort(key=lambda t: t["score"], reverse=True)
            
            logger.info(f"Analyzed {len(influence_trends)} creator influences")
            return influence_trends[:10]  # Top 10
            
        except Exception as e:
            logger.error(f"Error analyzing creator influence: {str(e)}", exc_info=True)
            return []
    
    def detect_topic_drift(
        self,
        events: List[BehaviorEvent],
        lookback_days: int
    ) -> List[Trend]:
        """
        Detect topic drift over time
        
        Args:
            events: Recent events
            lookback_days: Days to analyze
            
        Returns:
            List of topic drift trends
        """
        try:
            # Split events into time periods
            now = datetime.utcnow()
            mid_point = now - timedelta(days=lookback_days // 2)
            
            early_events = [e for e in events if e.timestamp < mid_point]
            late_events = [e for e in events if e.timestamp >= mid_point]
            
            if not early_events or not late_events:
                return []
            
            # Get topic distributions
            early_topics = Counter()
            late_topics = Counter()
            
            for event in early_events:
                for hashtag in event.hashtags or []:
                    early_topics[hashtag] += 1
            
            for event in late_events:
                for hashtag in event.hashtags or []:
                    late_topics[hashtag] += 1
            
            # Find topics that changed significantly
            drift_trends = []
            all_topics = set(early_topics.keys()) | set(late_topics.keys())
            
            for topic in all_topics:
                early_count = early_topics.get(topic, 0)
                late_count = late_topics.get(topic, 0)
                
                early_freq = early_count / len(early_events) if early_events else 0
                late_freq = late_count / len(late_events) if late_events else 0
                
                drift = late_freq - early_freq
                
                if abs(drift) > 0.05:  # Significant drift
                    trend = Trend({
                        "trend_type": "topic_drift",
                        "topic": topic,
                        "score": abs(drift),
                        "confidence": 0.7,
                        "growth_rate": drift,
                        "evidence": {
                            "early_frequency": round(early_freq, 3),
                            "late_frequency": round(late_freq, 3),
                            "drift": round(drift, 3),
                            "direction": "increasing" if drift > 0 else "decreasing"
                        },
                        "time_window": f"Last {lookback_days} days",
                        "metadata": {}
                    })
                    drift_trends.append(trend)
            
            # Sort by drift magnitude
            drift_trends.sort(key=lambda t: t["score"], reverse=True)
            
            logger.info(f"Detected {len(drift_trends)} topic drifts")
            return drift_trends[:10]  # Top 10
            
        except Exception as e:
            logger.error(f"Error detecting topic drift: {str(e)}", exc_info=True)
            return []
    
    def detect_attention_drift(
        self,
        events: List[BehaviorEvent],
        lookback_days: int
    ) -> List[Trend]:
        """
        Detect attention span drift over time
        
        Args:
            events: Recent events
            lookback_days: Days to analyze
            
        Returns:
            List of attention drift trends
        """
        try:
            # Split events into time periods
            now = datetime.utcnow()
            mid_point = now - timedelta(days=lookback_days // 2)
            
            early_events = [e for e in events if e.timestamp < mid_point]
            late_events = [e for e in events if e.timestamp >= mid_point]
            
            if not early_events or not late_events:
                return []
            
            # Calculate average watch times
            early_avg_watch = statistics.mean([e.watch_time for e in early_events])
            late_avg_watch = statistics.mean([e.watch_time for e in late_events])
            
            drift = late_avg_watch - early_avg_watch
            drift_pct = (drift / early_avg_watch) * 100 if early_avg_watch > 0 else 0
            
            if abs(drift_pct) > 10:  # Significant drift (>10%)
                trend = Trend({
                    "trend_type": "attention_drift",
                    "topic": "attention_span",
                    "score": min(1.0, abs(drift_pct) / 50),
                    "confidence": 0.8,
                    "growth_rate": drift,
                    "evidence": {
                        "early_avg_watch_time": round(early_avg_watch, 2),
                        "late_avg_watch_time": round(late_avg_watch, 2),
                        "drift_seconds": round(drift, 2),
                        "drift_percentage": round(drift_pct, 1),
                        "direction": "increasing" if drift > 0 else "decreasing"
                    },
                    "time_window": f"Last {lookback_days} days",
                    "metadata": {}
                })
                
                logger.info(f"Detected attention drift: {drift_pct:.1f}%")
                return [trend]
            
            return []
            
        except Exception as e:
            logger.error(f"Error detecting attention drift: {str(e)}", exc_info=True)
            return []
    
    def detect_daily_patterns(
        self,
        events: List[BehaviorEvent]
    ) -> List[Trend]:
        """
        Detect daily usage patterns
        
        Args:
            events: Recent events
            
        Returns:
            List of daily pattern trends
        """
        try:
            hour_counts = defaultdict(int)
            hour_engagement = defaultdict(int)
            
            for event in events:
                hour = event.timestamp.hour
                hour_counts[hour] += 1
                
                if event.liked or event.saved or event.shared or event.commented:
                    hour_engagement[hour] += 1
            
            if not hour_counts:
                return []
            
            # Find peak hours
            peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            
            patterns = []
            for hour, count in peak_hours:
                engagement_rate = hour_engagement.get(hour, 0) / count if count > 0 else 0
                
                # Determine time of day
                if 5 <= hour < 12:
                    time_label = "morning"
                elif 12 <= hour < 17:
                    time_label = "afternoon"
                elif 17 <= hour < 21:
                    time_label = "evening"
                else:
                    time_label = "night"
                
                trend = Trend({
                    "trend_type": "daily_pattern",
                    "topic": f"peak_usage_{time_label}",
                    "score": min(1.0, count / max(hour_counts.values())),
                    "confidence": 0.7,
                    "growth_rate": 0.0,
                    "evidence": {
                        "hour": hour,
                        "time_label": time_label,
                        "event_count": count,
                        "engagement_rate": round(engagement_rate, 2)
                    },
                    "time_window": "Recent period",
                    "metadata": {}
                })
                patterns.append(trend)
            
            logger.info(f"Detected {len(patterns)} daily patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Error detecting daily patterns: {str(e)}", exc_info=True)
            return []
    
    def detect_weekly_patterns(
        self,
        events: List[BehaviorEvent]
    ) -> List[Trend]:
        """
        Detect weekly usage patterns
        
        Args:
            events: Recent events
            
        Returns:
            List of weekly pattern trends
        """
        try:
            day_counts = defaultdict(int)
            day_engagement = defaultdict(int)
            
            for event in events:
                day = event.timestamp.strftime("%A")  # Day name
                day_counts[day] += 1
                
                if event.liked or event.saved or event.shared or event.commented:
                    day_engagement[day] += 1
            
            if not day_counts:
                return []
            
            # Find peak days
            peak_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            
            patterns = []
            for day, count in peak_days:
                engagement_rate = day_engagement.get(day, 0) / count if count > 0 else 0
                
                trend = Trend({
                    "trend_type": "weekly_pattern",
                    "topic": f"peak_usage_{day.lower()}",
                    "score": min(1.0, count / max(day_counts.values())),
                    "confidence": 0.7,
                    "growth_rate": 0.0,
                    "evidence": {
                        "day": day,
                        "event_count": count,
                        "engagement_rate": round(engagement_rate, 2)
                    },
                    "time_window": "Recent period",
                    "metadata": {}
                })
                patterns.append(trend)
            
            logger.info(f"Detected {len(patterns)} weekly patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Error detecting weekly patterns: {str(e)}", exc_info=True)
            return []


def get_trend_detection_engine() -> TrendDetectionEngine:
    """Get singleton trend detection engine instance"""
    if not hasattr(get_trend_detection_engine, "_instance"):
        get_trend_detection_engine._instance = TrendDetectionEngine()
    return get_trend_detection_engine._instance
