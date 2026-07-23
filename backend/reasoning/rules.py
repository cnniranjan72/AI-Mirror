"""
Rule Engine
Modular behavioral interpretation rules
All behavioral logic must be defined here, not hardcoded in interpreters
"""
from typing import List, Optional, Dict, Any, Callable
from abc import ABC, abstractmethod
import logging
from datetime import datetime, timedelta

from backend.shared.contracts import BehaviorEvent
from .behavior_object import BehaviorObject, TrendDirection
from .evidence_engine import Evidence


logger = logging.getLogger(__name__)


class Rule(ABC):
    """
    Abstract base class for behavioral rules
    
    All rules must implement:
    - condition(): Check if rule applies
    - score(): Calculate rule strength
    - confidence(): Calculate confidence in rule
    - explanation(): Generate human-readable explanation
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize rule
        
        Args:
            config: Rule-specific configuration
        """
        self.config = config or {}
        self.name = self.__class__.__name__
    
    @abstractmethod
    def condition(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> bool:
        """
        Check if rule condition is met
        
        Args:
            behavior_objects: List of behavior objects
            events: List of events
            evidence: List of evidence
            
        Returns:
            True if rule applies
        """
        pass
    
    @abstractmethod
    def score(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> float:
        """
        Calculate rule strength score
        
        Args:
            behavior_objects: List of behavior objects
            events: List of events
            evidence: List of evidence
            
        Returns:
            Score (0-1)
        """
        pass
    
    @abstractmethod
    def confidence(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> float:
        """
        Calculate confidence in rule application
        
        Args:
            behavior_objects: List of behavior objects
            events: List of events
            evidence: List of evidence
            
        Returns:
            Confidence (0-1)
        """
        pass
    
    @abstractmethod
    def explanation(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> str:
        """
        Generate human-readable explanation
        
        Args:
            behavior_objects: List of behavior objects
            events: List of events
            evidence: List of evidence
            
        Returns:
            Explanation string
        """
        pass


class LearningMotivationRule(Rule):
    """
    Detects increasing learning motivation
    
    Condition: Educational content increasing + High engagement
    """
    
    _EDU_KEYWORDS = ["learn", "tutorial", "education", "course", "study", "skill",
                     "how to", "guide", "programming", "coding", "science", "tech"]

    def _educational(self, behavior_objects):
        out = []
        for b in behavior_objects:
            hay = (b.topic or "").lower() + " " + " ".join(getattr(b, "subtopics", []) or []).lower() \
                  + " " + " ".join(getattr(b, "keywords", []) or []).lower()
            if any(k in hay for k in self._EDU_KEYWORDS):
                out.append(b)
        return out

    def _edu_share(self, behavior_objects, educational):
        total = sum(b.temporal_statistics.occurrence_count for b in behavior_objects) or 1
        edu = sum(b.temporal_statistics.occurrence_count for b in educational)
        return edu / total

    def condition(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> bool:
        """Fires when educational content is a meaningful share of consumption."""
        try:
            educational = self._educational(behavior_objects)
            if not educational:
                return False
            # A meaningful learning signal: at least ~10% of activity is educational.
            return self._edu_share(behavior_objects, educational) >= 0.10
        except Exception as e:
            logger.error(f"Error in LearningMotivationRule condition: {str(e)}", exc_info=True)
            return False
    
    def score(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> float:
        """Score = weighted blend of educational share and its engagement."""
        try:
            educational = self._educational(behavior_objects)
            if not educational:
                return 0.0
            share = self._edu_share(behavior_objects, educational)
            avg_engagement = sum(b.engagement_statistics.overall_engagement_rate for b in educational) / len(educational)
            return min(1.0, max(0.0, share * 0.6 + avg_engagement * 0.4))
        except Exception as e:
            logger.error(f"Error in LearningMotivationRule score: {str(e)}", exc_info=True)
            return 0.0
    
    def confidence(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> float:
        """Confidence reflects how strongly the learning pattern holds — driven by
        the educational SHARE and how many distinct educational topics support it,
        not the (intentionally conservative) per-object confidence_score."""
        try:
            educational = self._educational(behavior_objects)
            if not educational:
                return 0.0
            share = self._edu_share(behavior_objects, educational)
            count_factor = min(1.0, len(educational) / 4.0)
            return min(0.95, 0.55 + share * 0.3 + count_factor * 0.1)
        except Exception as e:
            logger.error(f"Error in LearningMotivationRule confidence: {str(e)}", exc_info=True)
            return 0.0
    
    def explanation(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> str:
        """Generate explanation for learning motivation"""
        try:
            educational = self._educational(behavior_objects)
            if not educational:
                return "No educational content detected"
            topics = [b.topic for b in sorted(educational, key=lambda b: b.temporal_statistics.occurrence_count, reverse=True)[:3]]
            share = self._edu_share(behavior_objects, educational)
            avg_engagement = sum(b.engagement_statistics.overall_engagement_rate for b in educational) / len(educational)
            return (
                f"Strong learning orientation: {len(educational)} educational topics "
                f"({', '.join(topics)}) make up {share:.0%} of activity, "
                f"with {avg_engagement:.0%} average engagement"
            )
        except Exception as e:
            logger.error(f"Error in LearningMotivationRule explanation: {str(e)}", exc_info=True)
            return "Error generating explanation"


class EntertainmentDominanceRule(Rule):
    """
    Detects entertainment content dominance
    
    Condition: Entertainment content > 60% of total consumption
    """
    
    def condition(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> bool:
        """Check if entertainment dominates"""
        try:
            if not behavior_objects:
                return False
            
            entertainment_behaviors = [
                b for b in behavior_objects
                if any(keyword in b.topic.lower() for keyword in ["entertainment", "funny", "meme", "comedy", "music", "dance"])
            ]
            
            entertainment_count = sum(b.temporal_statistics.occurrence_count for b in entertainment_behaviors)
            total_count = sum(b.temporal_statistics.occurrence_count for b in behavior_objects)
            
            if total_count == 0:
                return False
            
            entertainment_ratio = entertainment_count / total_count
            
            return entertainment_ratio > 0.6
            
        except Exception as e:
            logger.error(f"Error in EntertainmentDominanceRule condition: {str(e)}", exc_info=True)
            return False
    
    def score(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> float:
        """Calculate entertainment dominance score"""
        try:
            if not behavior_objects:
                return 0.0
            
            entertainment_behaviors = [
                b for b in behavior_objects
                if any(keyword in b.topic.lower() for keyword in ["entertainment", "funny", "meme", "comedy", "music", "dance"])
            ]
            
            entertainment_count = sum(b.temporal_statistics.occurrence_count for b in entertainment_behaviors)
            total_count = sum(b.temporal_statistics.occurrence_count for b in behavior_objects)
            
            if total_count == 0:
                return 0.0
            
            return entertainment_count / total_count
            
        except Exception as e:
            logger.error(f"Error in EntertainmentDominanceRule score: {str(e)}", exc_info=True)
            return 0.0
    
    def confidence(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> float:
        """Calculate confidence in entertainment dominance"""
        try:
            if not behavior_objects:
                return 0.0
            
            # Higher confidence with more data
            total_count = sum(b.temporal_statistics.occurrence_count for b in behavior_objects)
            
            return min(1.0, total_count / 50.0)
            
        except Exception as e:
            logger.error(f"Error in EntertainmentDominanceRule confidence: {str(e)}", exc_info=True)
            return 0.0
    
    def explanation(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> str:
        """Generate explanation for entertainment dominance"""
        try:
            if not behavior_objects:
                return "No behavior data"
            
            entertainment_behaviors = [
                b for b in behavior_objects
                if any(keyword in b.topic.lower() for keyword in ["entertainment", "funny", "meme", "comedy", "music", "dance"])
            ]
            
            entertainment_count = sum(b.temporal_statistics.occurrence_count for b in entertainment_behaviors)
            total_count = sum(b.temporal_statistics.occurrence_count for b in behavior_objects)
            
            ratio = entertainment_count / total_count if total_count > 0 else 0
            
            return f"Entertainment content dominates: {ratio:.1%} of total consumption ({entertainment_count}/{total_count} events)"
            
        except Exception as e:
            logger.error(f"Error in EntertainmentDominanceRule explanation: {str(e)}", exc_info=True)
            return "Error generating explanation"


class CreatorDependenceRule(Rule):
    """
    Detects dependence on specific creators
    
    Condition: Top 3 creators account for > 50% of consumption
    """
    
    def condition(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> bool:
        """Check if user is dependent on few creators"""
        try:
            if not behavior_objects:
                return False
            
            # Count occurrences per creator
            from collections import Counter
            creator_counts = Counter()
            
            for behavior in behavior_objects:
                for creator in behavior.creators:
                    creator_counts[creator] += behavior.temporal_statistics.occurrence_count
            
            if not creator_counts:
                return False
            
            total_count = sum(creator_counts.values())
            top_3_count = sum(count for _, count in creator_counts.most_common(3))
            
            ratio = top_3_count / total_count if total_count > 0 else 0
            
            return ratio > 0.5
            
        except Exception as e:
            logger.error(f"Error in CreatorDependenceRule condition: {str(e)}", exc_info=True)
            return False
    
    def score(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> float:
        """Calculate creator dependence score"""
        try:
            if not behavior_objects:
                return 0.0
            
            from collections import Counter
            creator_counts = Counter()
            
            for behavior in behavior_objects:
                for creator in behavior.creators:
                    creator_counts[creator] += behavior.temporal_statistics.occurrence_count
            
            if not creator_counts:
                return 0.0
            
            total_count = sum(creator_counts.values())
            top_3_count = sum(count for _, count in creator_counts.most_common(3))
            
            return top_3_count / total_count if total_count > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error in CreatorDependenceRule score: {str(e)}", exc_info=True)
            return 0.0
    
    def confidence(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> float:
        """Calculate confidence in creator dependence"""
        try:
            if not behavior_objects:
                return 0.0
            
            total_count = sum(b.temporal_statistics.occurrence_count for b in behavior_objects)
            
            return min(1.0, total_count / 30.0)
            
        except Exception as e:
            logger.error(f"Error in CreatorDependenceRule confidence: {str(e)}", exc_info=True)
            return 0.0
    
    def explanation(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> str:
        """Generate explanation for creator dependence"""
        try:
            from collections import Counter
            creator_counts = Counter()
            
            for behavior in behavior_objects:
                for creator in behavior.creators:
                    creator_counts[creator] += behavior.temporal_statistics.occurrence_count
            
            if not creator_counts:
                return "No creator data"
            
            top_3 = creator_counts.most_common(3)
            total_count = sum(creator_counts.values())
            top_3_count = sum(count for _, count in top_3)
            
            ratio = top_3_count / total_count if total_count > 0 else 0
            creator_names = [name for name, _ in top_3]
            
            return f"Creator dependence detected: Top 3 creators ({', '.join(creator_names)}) account for {ratio:.1%} of consumption"
            
        except Exception as e:
            logger.error(f"Error in CreatorDependenceRule explanation: {str(e)}", exc_info=True)
            return "Error generating explanation"


class AttentionImprovementRule(Rule):
    """
    Detects improving attention span
    
    Condition: Average watch time increasing over time
    """
    
    def condition(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> bool:
        """Check if attention span is improving"""
        try:
            if len(events) < 10:
                return False
            
            # Split events into early and late periods
            sorted_events = sorted(events, key=lambda e: e.timestamp)
            mid_point = len(sorted_events) // 2
            
            early_events = sorted_events[:mid_point]
            late_events = sorted_events[mid_point:]
            
            early_avg = sum(e.watch_time for e in early_events) / len(early_events)
            late_avg = sum(e.watch_time for e in late_events) / len(late_events)
            
            improvement = (late_avg - early_avg) / early_avg if early_avg > 0 else 0
            
            return improvement > 0.1  # 10% improvement
            
        except Exception as e:
            logger.error(f"Error in AttentionImprovementRule condition: {str(e)}", exc_info=True)
            return False
    
    def score(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> float:
        """Calculate attention improvement score"""
        try:
            if len(events) < 10:
                return 0.0
            
            sorted_events = sorted(events, key=lambda e: e.timestamp)
            mid_point = len(sorted_events) // 2
            
            early_events = sorted_events[:mid_point]
            late_events = sorted_events[mid_point:]
            
            early_avg = sum(e.watch_time for e in early_events) / len(early_events)
            late_avg = sum(e.watch_time for e in late_events) / len(late_events)
            
            improvement = (late_avg - early_avg) / early_avg if early_avg > 0 else 0
            
            return min(1.0, max(0.0, improvement))
            
        except Exception as e:
            logger.error(f"Error in AttentionImprovementRule score: {str(e)}", exc_info=True)
            return 0.0
    
    def confidence(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> float:
        """Calculate confidence in attention improvement"""
        try:
            # Higher confidence with more data
            return min(1.0, len(events) / 50.0)
            
        except Exception as e:
            logger.error(f"Error in AttentionImprovementRule confidence: {str(e)}", exc_info=True)
            return 0.0
    
    def explanation(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> str:
        """Generate explanation for attention improvement"""
        try:
            if len(events) < 10:
                return "Insufficient data"
            
            sorted_events = sorted(events, key=lambda e: e.timestamp)
            mid_point = len(sorted_events) // 2
            
            early_events = sorted_events[:mid_point]
            late_events = sorted_events[mid_point:]
            
            early_avg = sum(e.watch_time for e in early_events) / len(early_events)
            late_avg = sum(e.watch_time for e in late_events) / len(late_events)
            
            improvement = (late_avg - early_avg) / early_avg if early_avg > 0 else 0
            
            return f"Attention span improving: {improvement:.1%} increase (from {early_avg:.1f}s to {late_avg:.1f}s average watch time)"
            
        except Exception as e:
            logger.error(f"Error in AttentionImprovementRule explanation: {str(e)}", exc_info=True)
            return "Error generating explanation"


class PrimaryInterestRule(Rule):
    """
    Identifies the user's dominant interest areas.

    Condition: at least 2 behavior objects with recorded activity.
    """

    def _ranked(self, behavior_objects):
        return sorted(
            [b for b in behavior_objects if b.temporal_statistics.occurrence_count > 0],
            key=lambda b: b.temporal_statistics.occurrence_count, reverse=True,
        )

    def _top_share(self, behavior_objects, n=3):
        ranked = self._ranked(behavior_objects)
        total = sum(b.temporal_statistics.occurrence_count for b in ranked) or 1
        top = sum(b.temporal_statistics.occurrence_count for b in ranked[:n])
        return top / total

    def condition(self, behavior_objects, events, evidence):
        try:
            return len(self._ranked(behavior_objects)) >= 2
        except Exception:
            return False

    def score(self, behavior_objects, events, evidence):
        try:
            return min(1.0, self._top_share(behavior_objects))
        except Exception:
            return 0.0

    def confidence(self, behavior_objects, events, evidence):
        try:
            ranked = self._ranked(behavior_objects)
            total = sum(b.temporal_statistics.occurrence_count for b in ranked)
            share = self._top_share(behavior_objects)
            return min(0.95, 0.55 + share * 0.25 + min(total, 40) / 40 * 0.15)
        except Exception:
            return 0.0

    def explanation(self, behavior_objects, events, evidence):
        try:
            ranked = self._ranked(behavior_objects)
            topics = [b.topic for b in ranked[:3]]
            share = self._top_share(behavior_objects)
            return (
                f"Primary interests: {', '.join(topics)} account for "
                f"{share:.0%} of activity across {len(ranked)} tracked topics"
            )
        except Exception:
            return "Error generating explanation"


class CreatorDiversityRule(Rule):
    """
    Detects broad creator exploration (the healthy opposite of dependence).

    Condition: many distinct creators AND no small set dominating.
    """

    def _creator_counts(self, behavior_objects):
        from collections import Counter
        counts = Counter()
        for b in behavior_objects:
            for c in (b.creators or []):
                counts[c] += b.temporal_statistics.occurrence_count
        return counts

    def condition(self, behavior_objects, events, evidence):
        try:
            counts = self._creator_counts(behavior_objects)
            if len(counts) < 6:
                return False
            total = sum(counts.values()) or 1
            top3 = sum(c for _, c in counts.most_common(3))
            return (top3 / total) < 0.5  # no small clique dominates
        except Exception:
            return False

    def score(self, behavior_objects, events, evidence):
        try:
            counts = self._creator_counts(behavior_objects)
            total = sum(counts.values()) or 1
            top3 = sum(c for _, c in counts.most_common(3))
            return min(1.0, 1.0 - top3 / total)  # higher = more diverse
        except Exception:
            return 0.0

    def confidence(self, behavior_objects, events, evidence):
        try:
            unique = len(self._creator_counts(behavior_objects))
            return min(0.95, 0.55 + min(unique, 20) / 20 * 0.35)
        except Exception:
            return 0.0

    def explanation(self, behavior_objects, events, evidence):
        try:
            counts = self._creator_counts(behavior_objects)
            total = sum(counts.values()) or 1
            top3 = sum(c for _, c in counts.most_common(3))
            return (
                f"Broad creator exploration: {len(counts)} distinct creators, "
                f"top 3 only {top3 / total:.0%} of activity — low creator dependence"
            )
        except Exception:
            return "Error generating explanation"


class TemporalHabitRule(Rule):
    """
    Detects consistent, routine viewing habits.

    Condition: sustained behaviors (active over multiple days / recurring),
    signalling routine rather than one-off consumption.
    """

    def _habitual(self, behavior_objects):
        out = []
        for b in behavior_objects:
            ts = b.temporal_statistics
            if getattr(ts, "days_active", 0) >= 2 or ts.occurrence_count >= 3:
                out.append(b)
        return out

    def _avg_consistency(self, behaviors):
        if not behaviors:
            return 0.0
        return sum(getattr(b.temporal_statistics, "consistency_score", 0.0) for b in behaviors) / len(behaviors)

    def condition(self, behavior_objects, events, evidence):
        try:
            return len(self._habitual(behavior_objects)) >= 2
        except Exception:
            return False

    def score(self, behavior_objects, events, evidence):
        try:
            return min(1.0, self._avg_consistency(self._habitual(behavior_objects)))
        except Exception:
            return 0.0

    def confidence(self, behavior_objects, events, evidence):
        try:
            hab = self._habitual(behavior_objects)
            cons = self._avg_consistency(hab)
            return min(0.95, 0.55 + cons * 0.25 + min(len(hab), 6) / 6 * 0.15)
        except Exception:
            return 0.0

    def explanation(self, behavior_objects, events, evidence):
        try:
            hab = sorted(self._habitual(behavior_objects),
                         key=lambda b: getattr(b.temporal_statistics, "days_active", 0), reverse=True)
            if not hab:
                return "No recurring viewing habits detected"
            top = hab[0]
            topics = [b.topic for b in hab[:3]]
            days = getattr(top.temporal_statistics, "days_active", 0)
            return (
                f"Consistent viewing habit: {len(hab)} recurring topics "
                f"({', '.join(topics)}), '{top.topic}' active across {days} days"
            )
        except Exception:
            return "Error generating explanation"


class EngagementDepthRule(Rule):
    """
    Characterises HOW the user engages — deep/attentive vs quick/passive —
    from watch completion and interaction quality.
    """

    def _stats(self, behavior_objects):
        active = [b for b in behavior_objects if b.temporal_statistics.occurrence_count > 0]
        if not active:
            return None
        completion = sum(getattr(b.watch_statistics, "completion_rate", 0.0) for b in active) / len(active)
        quality = sum(getattr(b.engagement_statistics, "engagement_quality_score",
                              b.engagement_statistics.overall_engagement_rate) for b in active) / len(active)
        interactions = sum(getattr(b.engagement_statistics, "total_interactions", 0) for b in active)
        return {"completion": completion, "quality": quality, "interactions": interactions, "n": len(active)}

    def condition(self, behavior_objects, events, evidence):
        try:
            s = self._stats(behavior_objects)
            return bool(s and s["n"] >= 2)
        except Exception:
            return False

    def score(self, behavior_objects, events, evidence):
        try:
            s = self._stats(behavior_objects)
            return min(1.0, (s["completion"] * 0.6 + s["quality"] * 0.4)) if s else 0.0
        except Exception:
            return 0.0

    def confidence(self, behavior_objects, events, evidence):
        try:
            s = self._stats(behavior_objects)
            if not s:
                return 0.0
            return min(0.95, 0.55 + min(s["interactions"], 60) / 60 * 0.3 + min(s["n"], 8) / 8 * 0.1)
        except Exception:
            return 0.0

    def explanation(self, behavior_objects, events, evidence):
        try:
            s = self._stats(behavior_objects)
            if not s:
                return "Insufficient engagement data"
            style = "deep, attentive" if s["completion"] >= 0.55 else ("selective" if s["completion"] >= 0.35 else "quick, scanning")
            return (
                f"Engagement style is {style}: {s['completion']:.0%} average watch completion "
                f"and {s['quality']:.0%} engagement quality across {s['n']} topics"
            )
        except Exception:
            return "Error generating explanation"


class RuleEngine:
    """
    Rule Engine

    Manages and executes behavioral interpretation rules
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Rule Engine
        
        Args:
            config: Engine configuration
        """
        self.config = config or {}
        
        # Register all rules
        self.rules: List[Rule] = [
            LearningMotivationRule(config),
            EntertainmentDominanceRule(config),
            CreatorDependenceRule(config),
            CreatorDiversityRule(config),
            PrimaryInterestRule(config),
            TemporalHabitRule(config),
            EngagementDepthRule(config),
            AttentionImprovementRule(config),
        ]
        
        logger.info(f"RuleEngine initialized with {len(self.rules)} rules")
    
    def add_rule(self, rule: Rule):
        """
        Add a custom rule
        
        Args:
            rule: Rule instance
        """
        self.rules.append(rule)
        logger.info(f"Added rule: {rule.name}")
    
    def evaluate_all_rules(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate all rules
        
        Args:
            behavior_objects: List of behavior objects
            events: List of events
            evidence: List of evidence
            
        Returns:
            List of rule results
        """
        try:
            results = []
            
            for rule in self.rules:
                try:
                    if rule.condition(behavior_objects, events, evidence):
                        result = {
                            "rule_name": rule.name,
                            "applies": True,
                            "score": rule.score(behavior_objects, events, evidence),
                            "confidence": rule.confidence(behavior_objects, events, evidence),
                            "explanation": rule.explanation(behavior_objects, events, evidence)
                        }
                        results.append(result)
                except Exception as e:
                    logger.error(f"Error evaluating rule {rule.name}: {str(e)}", exc_info=True)
            
            logger.debug(f"Evaluated {len(self.rules)} rules, {len(results)} applied")
            return results
            
        except Exception as e:
            logger.error(f"Error evaluating rules: {str(e)}", exc_info=True)
            return []


def get_rule_engine() -> RuleEngine:
    """Get singleton rule engine instance"""
    if not hasattr(get_rule_engine, "_instance"):
        get_rule_engine._instance = RuleEngine()
    return get_rule_engine._instance
