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
    
    def condition(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> bool:
        """Check if learning motivation is increasing"""
        try:
            # Find educational behavior objects
            educational_behaviors = [
                b for b in behavior_objects
                if any(keyword in b.topic.lower() for keyword in ["learn", "tutorial", "education", "course", "study"])
                or any(keyword in " ".join(b.subtopics).lower() for keyword in ["learn", "tutorial", "education"])
            ]
            
            if not educational_behaviors:
                return False
            
            # Check if any are emerging or growing
            growing = any(
                b.trend_information.trend_direction in [TrendDirection.EMERGING, TrendDirection.GROWING]
                for b in educational_behaviors
            )
            
            # Check engagement
            high_engagement = any(
                b.engagement_statistics.overall_engagement_rate > 0.6
                for b in educational_behaviors
            )
            
            return growing and high_engagement
            
        except Exception as e:
            logger.error(f"Error in LearningMotivationRule condition: {str(e)}", exc_info=True)
            return False
    
    def score(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> float:
        """Calculate learning motivation score"""
        try:
            educational_behaviors = [
                b for b in behavior_objects
                if any(keyword in b.topic.lower() for keyword in ["learn", "tutorial", "education", "course", "study"])
            ]
            
            if not educational_behaviors:
                return 0.0
            
            # Average growth rate
            avg_growth = sum(b.trend_information.growth_rate for b in educational_behaviors) / len(educational_behaviors)
            
            # Average engagement
            avg_engagement = sum(b.engagement_statistics.overall_engagement_rate for b in educational_behaviors) / len(educational_behaviors)
            
            # Combined score
            score = (avg_growth * 0.6 + avg_engagement * 0.4)
            
            return min(1.0, max(0.0, score))
            
        except Exception as e:
            logger.error(f"Error in LearningMotivationRule score: {str(e)}", exc_info=True)
            return 0.0
    
    def confidence(
        self,
        behavior_objects: List[BehaviorObject],
        events: List[BehaviorEvent],
        evidence: List[Evidence]
    ) -> float:
        """Calculate confidence in learning motivation detection"""
        try:
            educational_behaviors = [
                b for b in behavior_objects
                if any(keyword in b.topic.lower() for keyword in ["learn", "tutorial", "education", "course", "study"])
            ]
            
            if not educational_behaviors:
                return 0.0
            
            # Average confidence of behavior objects
            avg_confidence = sum(b.confidence_score for b in educational_behaviors) / len(educational_behaviors)
            
            # Boost confidence if multiple behaviors
            count_factor = min(1.0, len(educational_behaviors) / 3.0)
            
            return avg_confidence * count_factor
            
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
            educational_behaviors = [
                b for b in behavior_objects
                if any(keyword in b.topic.lower() for keyword in ["learn", "tutorial", "education", "course", "study"])
            ]
            
            if not educational_behaviors:
                return "No educational content detected"
            
            topics = [b.topic for b in educational_behaviors[:3]]
            avg_engagement = sum(b.engagement_statistics.overall_engagement_rate for b in educational_behaviors) / len(educational_behaviors)
            
            return (
                f"Learning motivation increasing: {len(educational_behaviors)} educational topics "
                f"({', '.join(topics)}) with {avg_engagement:.1%} average engagement"
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
            AttentionImprovementRule(config)
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
