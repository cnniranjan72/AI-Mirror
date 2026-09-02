"""
Evidence Engine
Every conclusion must be supported by explicit evidence
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Tuple
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


# --- Counter-evidence -------------------------------------------------------
#
# A feed serves content; the viewer only chooses how long to stay. So a very
# short watch is not a neutral absence of data, it is a decision about that
# content, and it argues against interest in the topic rather than for it.
#
# Until this existed those events were counted as support for the very topic
# they were skipped on: the collectors filtered events by topic and put all of
# them into supporting_events, reporting the engagement rate only as a metric
# alongside. An account shown four hundred cooking reels that scrolled past
# every one produced strong evidence of interest in cooking.
#
# The line is drawn at a fraction of the viewer's own median watch time rather
# than at a number of seconds, because a short watch on a long-form feed and on
# a six-second loop are not the same duration. Measured across the deployed
# corpus, a cut at 0.40 of the median marks 19-20% of events as skips; at 0.25
# it is 13-15% and at 0.50 it is 22-23%, so the reading does not balance on the
# exact value chosen.
#
# Someone who skips nothing produces no counter-evidence, and that is the
# property worth having. Taking the bottom quartile of each history instead
# would manufacture counter-evidence for everyone by construction and could
# never report its absence.

SKIP_FRACTION_OF_MEDIAN = 0.40

# Below this there is no stable picture of what this viewer's ordinary watch
# looks like, so nothing is called a skip and no net confidence is reported.
MIN_EVENTS_FOR_BASELINE = 12

# A balance computed from three observations swings from +1 to -1 on a single
# skip. Net confidence is withheld until the ratio can carry weight.
MIN_OBSERVATIONS_FOR_NET = 5


def attention_baseline(events: List[BehaviorEvent]) -> Optional[float]:
    """This viewer's ordinary watch time, as a median over everything seen.

    The median rather than the mean: a handful of very long watches would drag
    a mean upward and reclassify ordinary viewing as skipping.
    """
    times = sorted(
        float(e.watch_time) for e in events
        if getattr(e, "watch_time", None) is not None
    )
    if len(times) < MIN_EVENTS_FOR_BASELINE:
        return None
    mid = len(times) // 2
    if len(times) % 2:
        return times[mid]
    return (times[mid - 1] + times[mid]) / 2.0


def partition_by_attention(
    relevant: List[BehaviorEvent],
    baseline: Optional[float]
) -> Tuple[List[BehaviorEvent], List[BehaviorEvent]]:
    """Split matching events into those attended to and those skipped.

    With no baseline nothing is called a skip and everything stays supporting,
    so a thin history degrades to the previous behaviour rather than inventing
    contradictions out of a handful of events.
    """
    if not baseline or baseline <= 0:
        return list(relevant), []

    threshold = baseline * SKIP_FRACTION_OF_MEDIAN
    attended, skipped = [], []
    for event in relevant:
        # A deliberate interaction outranks duration. Someone who saves a reel
        # two seconds in has not skipped it, they decided about it faster.
        if event.liked or event.saved or event.shared or event.commented:
            attended.append(event)
        elif float(getattr(event, "watch_time", 0.0) or 0.0) < threshold:
            skipped.append(event)
        else:
            attended.append(event)
    return attended, skipped


def net_confidence_from(
    confidence: float,
    support_count: int,
    counter_count: int
) -> Optional[float]:
    """Discount confidence by how one-sided the observations actually are.

    Confidence stays a statement about how much was seen. This is the separate
    question of whether what was seen pointed one way, and the two are reported
    side by side rather than folded together, so a claim resting on plenty of
    contradictory data cannot hide behind its sample size.

    Returns None when there is too little to judge, and 0.0 when skips equal or
    outnumber attention, at which point the evidence is entirely offset rather
    than merely weakened.
    """
    total = support_count + counter_count
    if total < MIN_OBSERVATIONS_FOR_NET:
        return None
    balance = (support_count - counter_count) / total
    return round(max(0.0, min(1.0, confidence * balance)), 4)


def _subject_of(evidence) -> str:
    """What a piece of evidence is about, for grouping.

    Each collector records its subject under its own key - topic for topical
    and behavioural, creator for creator evidence. Temporal and interaction
    evidence is about the history as a whole and carries neither, so it groups
    under its type alone, which is correct: there is only ever one of each.
    """
    meta = evidence.metadata or {}
    return str(meta.get("topic") or meta.get("creator") or "unknown")


def conflict_note(
    skipped_count: int,
    total: int,
    baseline: Optional[float]
) -> Optional[str]:
    """Plain-language record of how the contradiction was handled."""
    if not skipped_count or not baseline:
        return None
    threshold = baseline * SKIP_FRACTION_OF_MEDIAN
    return (
        f"{skipped_count} of {total} observations here were skipped - watched "
        f"under {threshold:.1f}s against a personal median of {baseline:.1f}s. "
        f"They are recorded as contradicting rather than supporting this "
        f"evidence, and net confidence discounts the stated confidence by the "
        f"balance between the two."
    )


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

            baseline = attention_baseline(events)
            attended, skipped = partition_by_attention(relevant_events, baseline)

            evidence = Evidence(
                evidence_id=f"evidence_behavioral_{topic.lower().replace(' ', '_')}_{datetime.utcnow().timestamp()}",
                evidence_type=EvidenceType.BEHAVIORAL,
                supporting_events=[e.event_id for e in attended],
                supporting_clusters=[],
                supporting_behavior_objects=[],
                confidence=confidence,
                weight=weight,
                conflicting_observations=[e.event_id for e in skipped],
                conflict_resolution=conflict_note(len(skipped), total_events, baseline),
                net_confidence=net_confidence_from(confidence, len(attended), len(skipped)),
                explanation=(
                    f"Watched {len(attended)} of {total_events} {topic} items "
                    f"past the usual attention threshold"
                    + (f"; {len(skipped)} were scrolled past" if skipped else "")
                ),
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

            baseline = attention_baseline(events)
            attended, skipped = partition_by_attention(creator_events, baseline)

            evidence = Evidence(
                evidence_id=f"evidence_creator_{creator}_{datetime.utcnow().timestamp()}",
                evidence_type=EvidenceType.CREATOR,
                supporting_events=[e.event_id for e in attended],
                supporting_clusters=[],
                supporting_behavior_objects=[],
                confidence=confidence,
                weight=weight,
                conflicting_observations=[e.event_id for e in skipped],
                conflict_resolution=conflict_note(len(skipped), total_events, baseline),
                net_confidence=net_confidence_from(confidence, len(attended), len(skipped)),
                explanation=f"User consistently engages with content from {creator}",
                key_metrics={
                    "occurrence_count": total_events,
                    "engagement_rate": round(engagement_rate, 3),
                    "avg_watch_time": round(avg_watch_time, 2),
                    "attended_count": len(attended),
                    "skipped_count": len(skipped),
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

            baseline = attention_baseline(events)
            attended, skipped = partition_by_attention(relevant_events, baseline)
            confidence = min(1.0, total_events / 20.0)

            evidence = Evidence(
                evidence_id=f"evidence_topical_{topic.lower().replace(' ', '_')}_{datetime.utcnow().timestamp()}",
                evidence_type=EvidenceType.TOPICAL,
                supporting_events=[e.event_id for e in attended],
                supporting_clusters=[],
                supporting_behavior_objects=[],
                confidence=confidence,
                weight=min(1.0, engagement_rate + 0.3),
                conflicting_observations=[e.event_id for e in skipped],
                conflict_resolution=conflict_note(len(skipped), total_events, baseline),
                net_confidence=net_confidence_from(confidence, len(attended), len(skipped)),
                # "User engaged with 20 pieces of crypto content" was written
                # for a topic every item of which was scrolled past. Now that
                # attention is measured, the sentence can say what happened.
                explanation=(
                    f"Watched {len(attended)} of {total_events} {topic} items "
                    f"past the usual attention threshold"
                    + (f"; {len(skipped)} were scrolled past" if skipped else "")
                ),
                key_metrics={
                    "occurrence_count": total_events,
                    "engagement_rate": round(engagement_rate, 3),
                    "avg_watch_time": round(avg_watch, 2),
                    "engaged_count": engaged,
                    "attended_count": len(attended),
                    "skipped_count": len(skipped),
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
                # Creator evidence carries {"creator": name} and no "topic", so
                # keying on topic alone filed every creator under "unknown" and
                # merged all of them into a single row whose metadata no longer
                # recorded which creator it was about. Three creators became
                # one piece of evidence, an attentively watched creator was
                # averaged together with a skipped one, and nothing downstream
                # could match the result to a rule that named a creator.
                key = (evidence.evidence_type, _subject_of(evidence))
                groups[key].append(evidence)
            
            merged = []
            
            for (etype, subject), evidences in groups.items():
                if len(evidences) == 1:
                    merged.append(evidences[0])
                else:
                    # Merge multiple evidence into one
                    all_events = []
                    all_clusters = []
                    all_behavior_objects = []
                    
                    all_conflicts = []

                    for e in evidences:
                        all_events.extend(e.supporting_events)
                        all_clusters.extend(e.supporting_clusters)
                        all_behavior_objects.extend(e.supporting_behavior_objects)
                        all_conflicts.extend(e.conflicting_observations)

                    # Calculate merged metrics
                    avg_confidence = sum(e.confidence for e in evidences) / len(evidences)
                    avg_weight = sum(e.weight for e in evidences) / len(evidences)

                    # Conflicts have to survive the merge. Dropping them here
                    # would let two pieces of evidence that each recorded their
                    # own contradictions combine into one that records none.
                    merged_events = list(set(all_events))
                    merged_conflicts = list(set(all_conflicts))
                    merged_note = next(
                        (e.conflict_resolution for e in evidences if e.conflict_resolution),
                        None
                    )
                    
                    merged_evidence = Evidence(
                        evidence_id=f"evidence_merged_{etype.value}_{subject}_{datetime.utcnow().timestamp()}",
                        evidence_type=etype,
                        supporting_events=merged_events,
                        supporting_clusters=list(set(all_clusters)),
                        supporting_behavior_objects=list(set(all_behavior_objects)),
                        confidence=avg_confidence,
                        weight=avg_weight,
                        conflicting_observations=merged_conflicts,
                        conflict_resolution=merged_note,
                        net_confidence=net_confidence_from(
                            avg_confidence, len(merged_events), len(merged_conflicts)
                        ),
                        explanation=f"Merged evidence from {len(evidences)} sources: {evidences[0].explanation}",
                        key_metrics=evidences[0].key_metrics,
                        time_window_start=min(e.time_window_start for e in evidences),
                        time_window_end=max(e.time_window_end for e in evidences),
                        created_at=datetime.utcnow(),
                        # Carry the originals' metadata forward so the merged
                        # row still says what it is about.
                        metadata=dict(evidences[0].metadata or {}, merged_count=len(evidences))
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
