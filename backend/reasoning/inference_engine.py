"""
Inference Engine (formerly Behavior Interpreter)
Rule-based behavioral inference without LLMs or ML
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from backend.shared.contracts import BehaviorEvent
from .behavior_object import BehaviorObject
from .evidence_engine import Evidence
from .reasoning_context import ReasoningContext
from .rules import RuleEngine, get_rule_engine


logger = logging.getLogger(__name__)


class Inference(BaseModel):
    """
    Behavioral Inference
    
    Represents a conclusion drawn from behavioral patterns.
    Inferences do NOT directly update Persona - they are intermediate reasoning outputs
    that feed into Persona generation, Character reasoning, and decision engines.
    """
    inference_id: str = Field(..., description="Unique inference identifier")
    inference_type: str = Field(..., description="Type of inference (motivation/pattern/preference/goal_signal)")
    
    # Core inference
    label: str = Field(..., description="Short label for inference")
    description: str = Field(..., description="Detailed description")
    
    # Strength
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in inference")
    importance: float = Field(..., ge=0.0, le=1.0, description="Importance of inference")
    strength: float = Field(..., ge=0.0, le=1.0, description="Overall strength (confidence × importance)")
    
    # Supporting evidence
    supporting_evidence: List[str] = Field(default_factory=list, description="IDs of supporting evidence")
    evidence_summary: str = Field(..., description="Summary of supporting evidence")
    
    # Affected entities
    affected_topics: List[str] = Field(default_factory=list, description="Topics affected by this inference")
    affected_creators: List[str] = Field(default_factory=list, description="Creators affected by this inference")
    affected_behaviors: List[str] = Field(default_factory=list, description="Behavior object IDs affected")
    
    # Recommendations
    recommendation_seed: Optional[str] = Field(None, description="Seed for generating recommendations")
    suggested_actions: List[str] = Field(default_factory=list, description="Suggested actions based on inference")
    
    # Temporal context
    inferred_at: datetime = Field(..., description="When inference was made")
    valid_from: datetime = Field(..., description="Start of validity period")
    valid_until: Optional[datetime] = Field(None, description="End of validity period")
    
    # Metadata
    rule_name: Optional[str] = Field(None, description="Rule that generated this inference")
    context_id: Optional[str] = Field(None, description="Reasoning context ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "inference_id": "inference_001",
                "inference_type": "motivation",
                "label": "Learning Motivation Increasing",
                "description": "User shows increasing motivation to learn AI and ML topics",
                "confidence": 0.85,
                "importance": 0.9,
                "strength": 0.765,
                "supporting_evidence": ["evidence_001", "evidence_002"],
                "evidence_summary": "3 pieces of behavioral evidence with 85% avg confidence",
                "affected_topics": ["AI", "Machine Learning", "Tutorials"],
                "affected_creators": ["ai_educator", "ml_expert"],
                "affected_behaviors": ["behavior_ai_learning"],
                "recommendation_seed": "Recommend advanced AI courses",
                "suggested_actions": ["Suggest ML fundamentals course", "Recommend AI project tutorials"],
                "inferred_at": "2026-06-12T00:30:00Z",
                "valid_from": "2026-06-12T00:00:00Z",
                "valid_until": None,
                "rule_name": "LearningMotivationRule",
                "context_id": "context_20260612_001",
                "metadata": {}
            }
        }
    
    def is_valid(self) -> bool:
        """
        Check if inference is currently valid
        
        Returns:
            True if valid
        """
        now = datetime.utcnow()
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True
    
    def is_strong(self, threshold: float = 0.7) -> bool:
        """
        Check if inference is strong
        
        Args:
            threshold: Strength threshold
            
        Returns:
            True if strong
        """
        return self.strength >= threshold
    
    def get_summary(self) -> str:
        """
        Get human-readable summary
        
        Returns:
            Summary string
        """
        return (
            f"{self.label}: {self.description} "
            f"(confidence: {self.confidence:.1%}, importance: {self.importance:.1%})"
        )


class InferenceEngine:
    """
    Inference Engine (formerly Behavior Interpreter)
    
    Responsibilities:
    - Convert behavioral patterns into meaningful inferences
    - Use Rule Engine for all logic (NO LLM, NO ML)
    - Generate Inference objects (not direct Persona updates)
    - Provide evidence-based reasoning
    - Support goal-aware interpretation
    
    Purpose:
    Transform raw behavioral patterns into structured inferences that can be
    consumed by Persona Engine, Virtual Character, Character RAG, and Adaptive Decision Engine.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Inference Engine
        
        Args:
            config: Engine configuration
        """
        self.config = config or {}
        self.rule_engine = get_rule_engine()
        self.min_confidence = self.config.get("min_confidence", 0.5)
        self.min_importance = self.config.get("min_importance", 0.3)
        
        logger.info("InferenceEngine initialized")
    
    def infer_from_context(
        self,
        context: ReasoningContext
    ) -> List[Inference]:
        """
        Generate inferences from reasoning context
        
        Args:
            context: ReasoningContext with all relevant data
            
        Returns:
            List of Inference objects
        """
        try:
            logger.info(f"Generating inferences from context {context.context_id}")
            
            # Evaluate all rules
            rule_results = self.rule_engine.evaluate_all_rules(
                behavior_objects=context.behavior_objects,
                events=[],  # Events are already consolidated into behavior objects
                evidence=context.evidence
            )
            
            # Convert rule results to inferences
            inferences = []
            
            for result in rule_results:
                if result["confidence"] >= self.min_confidence:
                    inference = self._create_inference_from_rule(
                        result,
                        context
                    )
                    inferences.append(inference)
            
            logger.info(f"Generated {len(inferences)} inferences from {len(rule_results)} rules")
            return inferences
            
        except Exception as e:
            logger.error(f"Error generating inferences: {str(e)}", exc_info=True)
            return []
    
    def infer_from_behaviors(
        self,
        behavior_objects: List[BehaviorObject],
        evidence: List[Evidence],
        user_id: str
    ) -> List[Inference]:
        """
        Generate inferences from behavior objects (convenience method)
        
        Args:
            behavior_objects: List of behavior objects
            evidence: List of evidence
            user_id: User identifier
            
        Returns:
            List of Inference objects
        """
        try:
            # Create minimal reasoning context
            from .reasoning_context import TemporalContext
            
            now = datetime.utcnow()
            temporal_context = TemporalContext(
                current_time=now,
                time_window_start=now - timedelta(days=30),
                time_window_end=now,
                time_of_day=self._get_time_of_day(now),
                day_of_week=now.strftime("%A"),
                is_weekend=now.weekday() >= 5
            )
            
            context = ReasoningContext(
                context_id=f"context_{now.timestamp()}",
                created_at=now,
                behavior_objects=behavior_objects,
                evidence=evidence,
                overall_confidence=0.8,
                temporal_context=temporal_context,
                user_id=user_id
            )
            
            return self.infer_from_context(context)
            
        except Exception as e:
            logger.error(f"Error generating inferences from behaviors: {str(e)}", exc_info=True)
            return []
    
    def _create_inference_from_rule(
        self,
        rule_result: Dict[str, Any],
        context: ReasoningContext
    ) -> Inference:
        """
        Create Inference object from rule result
        
        Args:
            rule_result: Rule evaluation result
            context: Reasoning context
            
        Returns:
            Inference object
        """
        try:
            # Determine inference type from rule name
            rule_name = rule_result["rule_name"]
            inference_type = self._infer_type_from_rule(rule_name)
            
            # Calculate importance (can be customized per rule)
            importance = self._calculate_importance(rule_result, context)
            
            # Calculate strength
            confidence = rule_result["confidence"]
            strength = confidence * importance
            
            # Extract affected entities
            affected_topics = []
            affected_creators = []
            affected_behaviors = []
            
            for behavior in context.behavior_objects:
                if behavior.confidence_score >= 0.6:
                    affected_topics.append(behavior.topic)
                    affected_creators.extend(behavior.creators[:3])
                    affected_behaviors.append(behavior.unique_id)
            
            # Generate recommendation seed
            recommendation_seed = self._generate_recommendation_seed(
                rule_name,
                rule_result,
                context
            )
            
            # Create inference
            inference = Inference(
                inference_id=f"inference_{rule_name}_{context.context_id}_{datetime.utcnow().timestamp()}",
                inference_type=inference_type,
                label=rule_result["explanation"].split(":")[0] if ":" in rule_result["explanation"] else rule_name,
                description=rule_result["explanation"],
                confidence=confidence,
                importance=importance,
                strength=strength,
                supporting_evidence=[e.evidence_id for e in context.evidence],
                evidence_summary=f"{len(context.evidence)} pieces of evidence with {context.overall_confidence:.1%} confidence",
                affected_topics=list(set(affected_topics))[:5],
                affected_creators=list(set(affected_creators))[:5],
                affected_behaviors=affected_behaviors,
                recommendation_seed=recommendation_seed,
                suggested_actions=[],
                inferred_at=datetime.utcnow(),
                valid_from=context.temporal_context.current_time,
                valid_until=None,
                rule_name=rule_name,
                context_id=context.context_id,
                metadata={
                    "rule_score": rule_result["score"]
                }
            )
            
            return inference
            
        except Exception as e:
            logger.error(f"Error creating inference from rule: {str(e)}", exc_info=True)
            raise
    
    def _infer_type_from_rule(self, rule_name: str) -> str:
        """
        Infer inference type from rule name
        
        Args:
            rule_name: Name of rule
            
        Returns:
            Inference type
        """
        if "Motivation" in rule_name:
            return "motivation"
        elif "Dominance" in rule_name or "Dependence" in rule_name:
            return "pattern"
        elif "Improvement" in rule_name:
            return "preference"
        else:
            return "general"
    
    def _calculate_importance(
        self,
        rule_result: Dict[str, Any],
        context: ReasoningContext
    ) -> float:
        """
        Calculate importance of inference
        
        Args:
            rule_result: Rule evaluation result
            context: Reasoning context
            
        Returns:
            Importance score (0-1)
        """
        try:
            # Base importance from rule score
            base_importance = rule_result["score"]
            
            # Boost if goal-aligned
            if context.is_goal_aligned():
                base_importance *= 1.2
            
            # Boost if strong evidence
            if context.has_sufficient_evidence(min_evidence=3):
                base_importance *= 1.1
            
            return min(1.0, base_importance)
            
        except Exception as e:
            logger.error(f"Error calculating importance: {str(e)}", exc_info=True)
            return 0.5
    
    def _generate_recommendation_seed(
        self,
        rule_name: str,
        rule_result: Dict[str, Any],
        context: ReasoningContext
    ) -> str:
        """
        Generate recommendation seed from inference
        
        Args:
            rule_name: Name of rule
            rule_result: Rule evaluation result
            context: Reasoning context
            
        Returns:
            Recommendation seed
        """
        try:
            if "LearningMotivation" in rule_name:
                topics = context.get_emerging_topics(limit=2)
                return f"Recommend advanced content in {', '.join(topics)}"
            elif "EntertainmentDominance" in rule_name:
                return "Suggest balancing entertainment with educational content"
            elif "CreatorDependence" in rule_name:
                return "Recommend diverse creators in similar topics"
            elif "AttentionImprovement" in rule_name:
                return "Recommend longer-form content to maintain attention growth"
            else:
                return "No specific recommendation"
                
        except Exception as e:
            logger.error(f"Error generating recommendation seed: {str(e)}", exc_info=True)
            return "Error generating recommendation"
    
    def _get_time_of_day(self, dt: datetime) -> str:
        """
        Get time of day label
        
        Args:
            dt: Datetime
            
        Returns:
            Time of day label
        """
        hour = dt.hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"
    
    def filter_strong_inferences(
        self,
        inferences: List[Inference],
        min_strength: float = 0.7
    ) -> List[Inference]:
        """
        Filter inferences by strength
        
        Args:
            inferences: List of inferences
            min_strength: Minimum strength threshold
            
        Returns:
            Filtered inferences
        """
        return [inf for inf in inferences if inf.strength >= min_strength]
    
    def rank_inferences(
        self,
        inferences: List[Inference]
    ) -> List[Inference]:
        """
        Rank inferences by strength
        
        Args:
            inferences: List of inferences
            
        Returns:
            Sorted inferences
        """
        return sorted(inferences, key=lambda inf: inf.strength, reverse=True)


def get_inference_engine() -> InferenceEngine:
    """Get singleton inference engine instance"""
    if not hasattr(get_inference_engine, "_instance"):
        get_inference_engine._instance = InferenceEngine()
    return get_inference_engine._instance
