import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from collections import Counter, defaultdict

from backend.reasoning.evidence_engine import Evidence
from backend.reasoning.inference_engine import Inference
from backend.reasoning.behavior_object import BehaviorObject, is_creator_behavior

logger = logging.getLogger(__name__)


class Reflection:
    def __init__(
        self,
        reflection_id: str,
        user_id: str,
        reflection_type: str,
        period_start: datetime,
        period_end: datetime,
        summary: str,
        key_insights: List[str],
        metrics: Dict[str, Any],
        patterns_identified: List[str],
        changes_detected: List[str],
        recommendations: List[str],
        confidence: float,
        event_count: int,
        memory_refs: List[str],
        metadata: Dict[str, Any],
    ):
        self.reflection_id = reflection_id
        self.user_id = user_id
        self.reflection_type = reflection_type
        self.period_start = period_start
        self.period_end = period_end
        self.summary = summary
        self.key_insights = key_insights
        self.metrics = metrics
        self.patterns_identified = patterns_identified
        self.changes_detected = changes_detected
        self.recommendations = recommendations
        self.confidence = confidence
        self.event_count = event_count
        self.memory_refs = memory_refs
        self.metadata = metadata


class ReflectionEngine:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        logger.info("ReflectionEngine initialized")

    def generate_reflection(
        self,
        user_id: str,
        behavior_objects: List[BehaviorObject],
        evidence_list: List[Evidence],
        inferences: List[Inference],
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> Optional[Reflection]:
        try:
            now = datetime.utcnow()
            period_start = period_start or now
            period_end = period_end or now

            if not behavior_objects and not evidence_list:
                logger.debug("No data for reflection generation")
                return None

            total_events = sum(
                getattr(bo.temporal_statistics, 'occurrence_count', 0) or 0
                for bo in behavior_objects
            )

            # Creator objects carry a "Content by <creator>" label, which is an
            # affinity rather than a subject — including them made reflection
            # summaries read "Key topics: travel, Content by ecaffauto, ...".
            topics = [bo.topic for bo in behavior_objects
                      if bo.topic and not is_creator_behavior(bo)]
            topic_counts = Counter(topics)
            dominant_topics = [t for t, _ in topic_counts.most_common(5)]

            evidence_by_type = defaultdict(list)
            for ev in evidence_list:
                evidence_by_type[ev.evidence_type.value].append(ev)

            patterns = []
            if len(evidence_by_type) > 2:
                patterns.append(f"Engagement across {len(evidence_by_type)} evidence dimensions")

            high_confidence = [ev for ev in evidence_list if ev.confidence > 0.7]
            if len(high_confidence) > 3:
                patterns.append(f"{len(high_confidence)} high-confidence evidence items identified")

            stable_objects = [bo for bo in behavior_objects
                              if bo.stability_score > 0.5 and not is_creator_behavior(bo)]
            if len(stable_objects) > 0:
                topics_str = ", ".join(bo.topic for bo in stable_objects[:3])
                patterns.append(f"Stable behavioral patterns in: {topics_str}")

            temporal_types = evidence_by_type.get("temporal", [])
            if temporal_types:
                peak_hours = [ev.key_metrics.get("peak_hour") for ev in temporal_types if ev.key_metrics.get("peak_hour") is not None]
                if peak_hours:
                    avg_peak = sum(peak_hours) / len(peak_hours)
                    time_label = "morning" if 5 <= avg_peak < 12 else "afternoon" if 12 <= avg_peak < 18 else "evening"
                    patterns.append(f"Peak activity during {time_label} hours")

            insights = []
            if dominant_topics:
                insights.append(f"Primary interests: {', '.join(dominant_topics[:3])}")

            avg_confidence = (
                sum(ev.confidence for ev in evidence_list) / len(evidence_list)
                if evidence_list else 0.0
            )
            insights.append(f"Overall evidence confidence: {avg_confidence:.1%}")

            if inferences:
                insights.append(f"{len(inferences)} behavioral inferences generated")

            summary_parts = [
                f"Reflection covering {len(behavior_objects)} behavior objects",
                f"across {len(evidence_list)} evidence items with {total_events} total events."
            ]
            if dominant_topics:
                summary_parts.append(f"Key topics: {', '.join(dominant_topics[:3])}.")

            creators = set()
            for bo in behavior_objects:
                creators.update(bo.creators or [])
            if creators:
                summary_parts.append(f"Interactions with {len(creators)} creators.")

            reflection = Reflection(
                reflection_id=f"ref_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                reflection_type="periodic",
                period_start=period_start,
                period_end=period_end,
                summary=" ".join(summary_parts),
                key_insights=insights,
                metrics={
                    "behavior_object_count": len(behavior_objects),
                    "evidence_count": len(evidence_list),
                    "inference_count": len(inferences),
                    "total_events": total_events,
                    "unique_creators": len(creators),
                    "dominant_topics": dominant_topics,
                    "avg_confidence": round(avg_confidence, 3),
                    "evidence_type_distribution": {k: len(v) for k, v in evidence_by_type.items()},
                },
                patterns_identified=patterns,
                changes_detected=[],
                recommendations=[],
                confidence=min(1.0, len(evidence_list) / 10.0),
                event_count=total_events,
                memory_refs=[bo.unique_id for bo in behavior_objects[:10]],
                metadata={"source": "reflection_engine", "generated_at": now.isoformat()},
            )

            logger.info(f"Generated reflection: {reflection.reflection_id} ({len(insights)} insights)")
            return reflection

        except Exception as e:
            logger.error(f"Reflection generation failed: {e}", exc_info=True)
            return None


_reflection_instance: Optional[ReflectionEngine] = None


def get_reflection_engine() -> ReflectionEngine:
    global _reflection_instance
    if _reflection_instance is None:
        _reflection_instance = ReflectionEngine()
    return _reflection_instance