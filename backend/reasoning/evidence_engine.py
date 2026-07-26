"""
Evidence Engine
Every conclusion must be supported by explicit evidence
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import logging
from collections import defaultdict, Counter

from backend.shared.contracts import BehaviorEvent, BehaviorCluster


logger = logging.getLogger(__name__)


class EvidenceType(str, Enum):
    """Five evidence dimensions from the paper"""
    BEHAVIORAL = "behavioral"
    TEMPORAL = "temporal"
    TOPICAL = "topical"
    CREATOR = "creator"
    INTERACTION = "interaction"


class Evidence(BaseModel):
    """
    Evidence supporting a behavioral conclusion
    
    Every insight, interpretation, or conclusion must reference Evidence.
    Never return unsupported insights.
    """
    evidence_id: str = Field(..., description="Unique evidence identifier")
    evidence_type: EvidenceType = Field(..., description="Type of evidence")
    
    # Supporting data
    supporting_events: List[str] = Field(default_factory=list, description="IDs of supporting events")
    supporting_clusters: List[str] = Field(default_factory=list, description="IDs of supporting clusters")
    supporting_behavior_objects: List[str] = Field(default_factory=list, description="IDs of supporting behavior objects")
    
    # Strength
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this evidence")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight/importance of this evidence")
    
    # Counter-evidence and conflicts
    counter_evidence_ids: List[str] = Field(default_factory=list, description="IDs of conflicting evidence")
    conflicting_observations: List[str] = Field(default_factory=list, description="Observations that contradict this evidence")
    conflict_resolution: Optional[str] = Field(None, description="How conflicts were resolved")
    net_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence after accounting for counter-evidence")
    
    # Explanation
    explanation: str = Field(..., description="Human-readable explanation of evidence")
    key_metrics: Dict[str, Any] = Field(default_factory=dict, description="Key metrics supporting evidence")
    
    # Temporal context
    time_window_start: datetime = Field(..., description="Start of evidence time window")
    time_window_end: datetime = Field(..., description="End of evidence time window")
    
    # Metadata
    created_at: datetime = Field(..., description="When evidence was collected")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "evidence_id": "evidence_001",
                "evidence_type": "behavioral",
                "supporting_events": ["evt_1", "evt_2", "evt_3"],
                "supporting_clusters": ["cluster_1"],
                "supporting_behavior_objects": ["behavior_ai_learning"],
                "confidence": 0.9,
                "weight": 0.8,
                "explanation": "User consistently engages with AI learning content",
                "key_metrics": {
                    "occurrence_count": 50,
                    "engagement_rate": 0.75,
                    "avg_watch_time": 15.0
                },
                "time_window_start": "2026-05-01T00:00:00Z",
                "time_window_end": "2026-06-11T00:00:00Z",
                "created_at": "2026-06-11T00:00:00Z",
                "metadata": {}
            }
        }


class EvidenceEngine:
    """
    Evidence Engine
    
    Responsibilities:
    - Collect evidence from events, clusters, and behavior objects
    - Aggregate evidence for conclusions
    - Rank evidence by strength
    - Merge related evidence
    - Summarize evidence
    - Calculate confidence scores
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Evidence Engine
        
        Args:
            config: Engine configuration
        """
        self.config = config or {}
        self.min_confidence = self.config.get("min_confidence", 0.5)
        self.min_weight = self.config.get("min_weight", 0.3)
        
        logger.info("EvidenceEngine initialized")
    
    def collect_behavioral_evidence(
        self,
        events: List[BehaviorEvent],
        topic: str,
        time_window_days: int = 30
    ) -> Evidence:
        """
        Collect behavioral evidence for a topic
        
        Args:
            events: List of events
            topic: Topic to collect evidence for
            time_window_days: Days to look back
            
        Returns:
            Evidence object
        """
        try:
            # Filter events by topic
            relevant_events = [
                e for e in events
                if topic.lower() in [h.lower() for h in e.hashtags] or
                (e.caption and topic.lower() in e.caption.lower())
            ]
            
            if not relevant_events:
                return None
            
            # Calculate metrics
            total_events = len(relevant_events)
            engaged_events = sum(
                1 for e in relevant_events
                if e.liked or e.saved or e.shared or e.commented
            )
            engagement_rate = engaged_events / total_events if total_events > 0 else 0.0
            
            avg_watch_time = sum(e.watch_time for e in relevant_events) / total_events
            
            # Time window
            timestamps = [e.timestamp for e in relevant_events]
            time_window_start = min(timestamps)
            time_window_end = max(timestamps)
            
            # Calculate confidence based on data volume
            confidence = min(1.0, total_events / 20.0)  # Full confidence at 20+ events
            
            # Calculate weight based on engagement
            weight = min(1.0, engagement_rate + 0.3)  # Minimum 0.3 weight
            
            evidence = Evidence(
                evidence_id=f"evidence_behavioral_{topic.lower().replace(' ', '_')}_{datetime.utcnow().timestamp()}",
                evidence_type=EvidenceType.BEHAVIORAL,
                supporting_events=[e.event_id for e in relevant_events],
                supporting_clusters=[],
                supporting_behavior_objects=[],
                confidence=confidence,
                weight=weight,
                explanation=f"User engaged with {total_events} pieces of {topic} content with {engagement_rate:.1%} engagement rate",
                key_metrics={
                    "occurrence_count": total_events,
                    "engagement_rate": round(engagement_rate, 3),
                    "avg_watch_time": round(avg_watch_time, 2),
                    "engaged_count": engaged_events
                },
                time_window_start=time_window_start,
                time_window_end=time_window_end,
                created_at=datetime.utcnow(),
                metadata={"topic": topic}
            )
            
            logger.debug(f"Collected behavioral evidence for {topic}: {total_events} events")
            return evidence
            
        except Exception as e:
            logger.error(f"Error collecting behavioral evidence: {str(e)}", exc_info=True)
            return None
    
    def collect_temporal_evidence(
        self,
        events: List[BehaviorEvent],
        pattern_description: str
    ) -> Evidence:
        """
        Collect temporal pattern evidence
        
        Args:
            events: List of events
            pattern_description: Description of temporal pattern
            
        Returns:
            Evidence object
        """
        try:
            if not events:
                return None
            
            # Analyze temporal patterns
            hour_counts = defaultdict(int)
            day_counts = defaultdict(int)
            
            for event in events:
                hour_counts[event.timestamp.hour] += 1
                day_counts[event.timestamp.strftime("%A")] += 1
            
            # Find peak hour and day
            peak_hour = max(hour_counts.items(), key=lambda x: x[1])
            peak_day = max(day_counts.items(), key=lambda x: x[1])
            
            # Calculate confidence based on consistency
            total_events = len(events)
            peak_hour_percentage = peak_hour[1] / total_events
            confidence = min(1.0, peak_hour_percentage * 2)  # Higher if concentrated
            
            timestamps = [e.timestamp for e in events]
            
            evidence = Evidence(
                evidence_id=f"evidence_temporal_{datetime.utcnow().timestamp()}",
                evidence_type=EvidenceType.TEMPORAL,
                supporting_events=[e.event_id for e in events],
                supporting_clusters=[],
                supporting_behavior_objects=[],
                confidence=confidence,
                weight=0.7,
                explanation=pattern_description,
                key_metrics={
                    "peak_hour": peak_hour[0],
                    "peak_hour_count": peak_hour[1],
                    "peak_day": peak_day[0],
                    "peak_day_count": peak_day[1],
                    "total_events": total_events
                },
                time_window_start=min(timestamps),
                time_window_end=max(timestamps),
                created_at=datetime.utcnow(),
                metadata={}
            )
            
            logger.debug(f"Collected temporal evidence: {pattern_description}")
            return evidence
            
        except Exception as e:
            logger.error(f"Error collecting temporal evidence: {str(e)}", exc_info=True)
            return None
    
    def collect_creator_evidence(
        self,
        events: List[BehaviorEvent],
        creator: str
    ) -> Evidence:
        """
        Collect creator influence evidence
        
        Args:
            events: List of events
            creator: Creator username
            
        Returns:
            Evidence object
        """
        try:
            # Filter events by creator
            creator_events = [e for e in events if e.creator == creator]
            
            if not creator_events:
                return None
            
            total_events = len(creator_events)
            engaged_events = sum(
                1 for e in creator_events
                if e.liked or e.saved or e.shared or e.commented
            )
            engagement_rate = engaged_events / total_events if total_events > 0 else 0.0
            
            avg_watch_time = sum(e.watch_time for e in creator_events) / total_events
            
            # Collect topics
            all_topics = []
            for event in creator_events:
                all_topics.extend(event.hashtags or [])
            
            from collections import Counter
            top_topics = Counter(all_topics).most_common(5)
            
            timestamps = [e.timestamp for e in creator_events]
            
            confidence = min(1.0, total_events / 10.0)
            weight = min(1.0, engagement_rate + 0.4)
            
            evidence = Evidence(
                evidence_id=f"evidence_creator_{creator}_{datetime.utcnow().timestamp()}",
                evidence_type=EvidenceType.CREATOR,
                supporting_events=[e.event_id for e in creator_events],
                supporting_clusters=[],
                supporting_behavior_objects=[],
                confidence=confidence,
                weight=weight,
                explanation=f"User consistently engages with content from {creator}",
                key_metrics={
                    "occurrence_count": total_events,
                    "engagement_rate": round(engagement_rate, 3),
                    "avg_watch_time": round(avg_watch_time, 2),
                    "top_topics": [t[0] for t in top_topics]
                },
                time_window_start=min(timestamps),
                time_window_end=max(timestamps),
                created_at=datetime.utcnow(),
                metadata={"creator": creator}
            )
            
            logger.debug(f"Collected creator evidence for {creator}: {total_events} events")
            return evidence
            
        except Exception as e:
            logger.error(f"Error collecting creator evidence: {str(e)}", exc_info=True)
            return None
    
    def collect_topical_evidence(
        self,
        events: List[BehaviorEvent],
        topic: str,
        time_window_days: int = 30
    ) -> Evidence:
        try:
            relevant_events = [
                e for e in events
                if topic.lower() in [h.lower() for h in e.hashtags] or
                (e.caption and topic.lower() in e.caption.lower())
            ]

            if not relevant_events:
                return None

            total_events = len(relevant_events)
            engaged = sum(1 for e in relevant_events if e.liked or e.saved or e.shared or e.commented)
            engagement_rate = engaged / total_events if total_events > 0 else 0.0
            avg_watch = sum(e.watch_time for e in relevant_events) / total_events
            timestamps = [e.timestamp for e in relevant_events]

            all_hashtags = [h for e in relevant_events for h in (e.hashtags or [])]
            top_hashtags = Counter(all_hashtags).most_common(5)

            evidence = Evidence(
                evidence_id=f"evidence_topical_{topic.lower().replace(' ', '_')}_{datetime.utcnow().timestamp()}",
                evidence_type=EvidenceType.TOPICAL,
                supporting_events=[e.event_id for e in relevant_events],
                supporting_clusters=[],
                supporting_behavior_objects=[],
                confidence=min(1.0, total_events / 20.0),
                weight=min(1.0, engagement_rate + 0.3),
                explanation=f"User engaged with {total_events} pieces of {topic} content ({engagement_rate:.1%} engagement)",
                key_metrics={
                    "occurrence_count": total_events,
                    "engagement_rate": round(engagement_rate, 3),
                    "avg_watch_time": round(avg_watch, 2),
                    "engaged_count": engaged,
                    "top_hashtags": [h[0] for h in top_hashtags],
                },
                time_window_start=min(timestamps),
                time_window_end=max(timestamps),
                created_at=datetime.utcnow(),
                metadata={"topic": topic}
            )
            return evidence
        except Exception as e:
            logger.error(f"Error collecting topical evidence: {e}", exc_info=True)
            return None

    def collect_interaction_evidence(
        self,
        events: List[BehaviorEvent],
        time_window_days: int = 30
    ) -> Evidence:
        try:
            if not events:
                return None

            total = len(events)
            liked = sum(1 for e in events if e.liked)
            saved = sum(1 for e in events if getattr(e, 'saved', False))
            shared = sum(1 for e in events if getattr(e, 'shared', False))
            commented = sum(1 for e in events if getattr(e, 'commented', False))
            replayed = sum(getattr(e, 'replay_count', 0) for e in events)

            like_rate = liked / total if total > 0 else 0
            save_rate = saved / total if total > 0 else 0
            replay_rate = replayed / total if total > 0 else 0
            interaction_depth = (liked + saved + shared + commented) / total if total > 0 else 0

            timestamps = [e.timestamp for e in events]

            confidence = min(1.0, total / 15.0)
            weight = min(1.0, interaction_depth + 0.3)

            level = "high" if interaction_depth > 0.5 else "moderate" if interaction_depth > 0.2 else "low"

            evidence = Evidence(
                evidence_id=f"evidence_interaction_{datetime.utcnow().timestamp()}",
                evidence_type=EvidenceType.INTERACTION,
                supporting_events=[e.event_id for e in events],
                supporting_clusters=[],
                supporting_behavior_objects=[],
                confidence=confidence,
                weight=weight,
                explanation=f"User shows {level} interaction depth ({interaction_depth:.1%} rate, {like_rate:.0%} likes)",
                key_metrics={
                    "total_interactions": total,
                    "like_rate": round(like_rate, 3),
                    "save_rate": round(save_rate, 3),
                    "replay_rate": round(replay_rate, 3),
                    "interaction_depth": round(interaction_depth, 3),
                    "replay_count": replayed,
                },
                time_window_start=min(timestamps),
                time_window_end=max(timestamps),
                created_at=datetime.utcnow(),
                metadata={}
            )
            return evidence
        except Exception as e:
            logger.error(f"Error collecting interaction evidence: {e}", exc_info=True)
            return None

    def aggregate_evidence(
        self,
        evidence_list: List[Evidence]
    ) -> Dict[str, Any]:
        """
        Aggregate multiple pieces of evidence
        
        Args:
            evidence_list: List of evidence objects
            
        Returns:
            Aggregated evidence summary
        """
        try:
            if not evidence_list:
                return {
                    "total_evidence_count": 0,
                    "overall_confidence": 0.0,
                    "overall_weight": 0.0,
                    "evidence_types": {},
                    "strongest_evidence": None
                }
            
            # Calculate overall metrics
            total_confidence = sum(e.confidence * e.weight for e in evidence_list)
            total_weight = sum(e.weight for e in evidence_list)
            overall_confidence = total_confidence / total_weight if total_weight > 0 else 0.0
            
            # Group by type
            by_type = defaultdict(list)
            for evidence in evidence_list:
                by_type[evidence.evidence_type].append(evidence)
            
            # Find strongest evidence
            strongest = max(evidence_list, key=lambda e: e.confidence * e.weight)
            
            return {
                "total_evidence_count": len(evidence_list),
                "overall_confidence": round(overall_confidence, 3),
                "overall_weight": round(total_weight / len(evidence_list), 3),
                "evidence_types": {
                    etype.value: len(evidences)
                    for etype, evidences in by_type.items()
                },
                "strongest_evidence": {
                    "type": strongest.evidence_type.value,
                    "explanation": strongest.explanation,
                    "confidence": strongest.confidence
                }
            }
            
        except Exception as e:
            logger.error(f"Error aggregating evidence: {str(e)}", exc_info=True)
            return {}
    
    def rank_evidence(
        self,
        evidence_list: List[Evidence]
    ) -> List[Evidence]:
        """
        Rank evidence by strength (confidence * weight)
        
        Args:
            evidence_list: List of evidence objects
            
        Returns:
            Sorted list of evidence
        """
        try:
            return sorted(
                evidence_list,
                key=lambda e: e.confidence * e.weight,
                reverse=True
            )
        except Exception as e:
            logger.error(f"Error ranking evidence: {str(e)}", exc_info=True)
            return evidence_list
    
    def merge_similar_evidence(
        self,
        evidence_list: List[Evidence]
    ) -> List[Evidence]:
        """
        Merge similar evidence to avoid redundancy
        
        Args:
            evidence_list: List of evidence objects
            
        Returns:
            Merged evidence list
        """
        try:
            # Group by type and topic
            groups = defaultdict(list)
            
            for evidence in evidence_list:
                key = (evidence.evidence_type, evidence.metadata.get("topic", "unknown"))
                groups[key].append(evidence)
            
            merged = []
            
            for (etype, topic), evidences in groups.items():
                if len(evidences) == 1:
                    merged.append(evidences[0])
                else:
                    # Merge multiple evidence into one
                    all_events = []
                    all_clusters = []
                    all_behavior_objects = []
                    
                    for e in evidences:
                        all_events.extend(e.supporting_events)
                        all_clusters.extend(e.supporting_clusters)
                        all_behavior_objects.extend(e.supporting_behavior_objects)
                    
                    # Calculate merged metrics
                    avg_confidence = sum(e.confidence for e in evidences) / len(evidences)
                    avg_weight = sum(e.weight for e in evidences) / len(evidences)
                    
                    merged_evidence = Evidence(
                        evidence_id=f"evidence_merged_{etype.value}_{topic}_{datetime.utcnow().timestamp()}",
                        evidence_type=etype,
                        supporting_events=list(set(all_events)),
                        supporting_clusters=list(set(all_clusters)),
                        supporting_behavior_objects=list(set(all_behavior_objects)),
                        confidence=avg_confidence,
                        weight=avg_weight,
                        explanation=f"Merged evidence from {len(evidences)} sources: {evidences[0].explanation}",
                        key_metrics=evidences[0].key_metrics,
                        time_window_start=min(e.time_window_start for e in evidences),
                        time_window_end=max(e.time_window_end for e in evidences),
                        created_at=datetime.utcnow(),
                        metadata={"merged_count": len(evidences), "topic": topic}
                    )
                    merged.append(merged_evidence)
            
            logger.debug(f"Merged {len(evidence_list)} evidence into {len(merged)}")
            return merged
            
        except Exception as e:
            logger.error(f"Error merging evidence: {str(e)}", exc_info=True)
            return evidence_list
    
    def summarize_evidence(
        self,
        evidence_list: List[Evidence]
    ) -> str:
        """
        Create human-readable summary of evidence
        
        Args:
            evidence_list: List of evidence objects
            
        Returns:
            Summary string
        """
        try:
            if not evidence_list:
                return "No evidence available"
            
            # Rank evidence
            ranked = self.rank_evidence(evidence_list)
            
            # Take top 3
            top_evidence = ranked[:3]
            
            summary_parts = []
            for i, evidence in enumerate(top_evidence, 1):
                summary_parts.append(
                    f"{i}. {evidence.explanation} "
                    f"(confidence: {evidence.confidence:.1%}, weight: {evidence.weight:.1%})"
                )
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error summarizing evidence: {str(e)}", exc_info=True)
            return "Error generating summary"
    
    def calculate_confidence(
        self,
        evidence_list: List[Evidence],
        min_evidence_count: int = 2
    ) -> float:
        """
        Calculate overall confidence from evidence
        
        Args:
            evidence_list: List of evidence objects
            min_evidence_count: Minimum evidence required for high confidence
            
        Returns:
            Overall confidence score (0-1)
        """
        try:
            if not evidence_list:
                return 0.0
            
            # Aggregate confidence
            aggregated = self.aggregate_evidence(evidence_list)
            base_confidence = aggregated["overall_confidence"]
            
            # Penalize if insufficient evidence
            evidence_count_factor = min(1.0, len(evidence_list) / min_evidence_count)
            
            # Final confidence
            final_confidence = base_confidence * evidence_count_factor
            
            return round(final_confidence, 3)
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}", exc_info=True)
            return 0.0


def get_evidence_engine() -> EvidenceEngine:
    """Get singleton evidence engine instance"""
    if not hasattr(get_evidence_engine, "_instance"):
        get_evidence_engine._instance = EvidenceEngine()
    return get_evidence_engine._instance
