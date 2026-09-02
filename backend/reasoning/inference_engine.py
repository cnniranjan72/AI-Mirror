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
            
            # What this rule actually reasoned over, as declared by the rule.
            #
            # This used to be the eight most active behaviour objects, computed
            # identically for every rule — the loop never looked at
            # rule_result. So every inference for a user carried the same
            # topics, creators and behaviours, and surfacing them as "why the
            # system thinks this" meant showing evidence with no bearing on the
            # conclusion. Verified in production: 10 of 10 users had exactly
            # one distinct creator set spanning all of their claims.
            #
            # A rule that has not implemented subjects() yields EMPTY lists on
            # purpose. Falling back to the global set would restore the very
            # problem this replaces; showing nothing is the honest answer, and
            # downstream (see services/calibration.py) reports the absence
            # rather than inventing a basis.
            subjects = rule_result.get("subjects") or {}
            affected_topics = list(subjects.get("topics", []))
            affected_creators = list(subjects.get("creators", []))
            affected_behaviors = list(subjects.get("behaviors", []))
            
            # An inference used to cite every piece of evidence in the context.
            # That made the citation say nothing: a claim about creator
            # dependence listed cooking-topic evidence among its support, and
            # once evidence started carrying its own contradictions every
            # belief inherited every other belief's counter-evidence, so all of
            # them reported the same net strength to three decimal places.
            # Rules declare their subjects, so the evidence bearing on the
            # claim can be picked out instead.
            relevant_evidence = self._evidence_for_subjects(
                context.evidence, affected_topics, affected_creators
            )
            if relevant_evidence:
                supporting_evidence = [e.evidence_id for e in relevant_evidence]
                evidence_basis = "subjects"
            else:
                # The structural rules - about the shape of a history rather
                # than any topic in it - declare no subjects and genuinely do
                # rest on the whole context. They say so rather than appearing
                # to have made a selection they did not make.
                supporting_evidence = [e.evidence_id for e in context.evidence]
                evidence_basis = "all"

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
                supporting_evidence=supporting_evidence,
                evidence_summary=f"{len(supporting_evidence)} pieces of evidence with {context.overall_confidence:.1%} confidence",
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
                    "rule_score": rule_result["score"],
                    # Marks affected_topics/creators/behaviors as this rule's
                    # declared subjects rather than the old global fallback.
                    # Rows written before this cannot be told apart by shape —
                    # an eight-item global set looks exactly like a genuine
                    # one — so consumers gate on the marker, not the contents.
                    # Inferences are regenerated wholesale on every ingest, so
                    # old rows age out on their own.
                    "basis_version": 2,
                    # "subjects" means the cited evidence was selected by what
                    # this rule says its claim is about; "all" means the rule
                    # declared no subjects and the whole context is cited. A
                    # reader cannot tell the two apart from the list alone.
                    "evidence_basis": evidence_basis,
                    "subjects_declared": bool(
                        affected_topics or affected_creators or affected_behaviors
                    ),
                    # The line this rule fired on, frozen with the claim so it
                    # matches the numbers in the description rather than
                    # drifting as new events arrive.
                    "exit_condition": rule_result.get("exit_condition"),
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
        elif "Habit" in rule_name or "Temporal" in rule_name:
            return "habit"
        elif "Depth" in rule_name or "Engagement" in rule_name or "Improvement" in rule_name:
            return "preference"
        elif "Interest" in rule_name or "Diversity" in rule_name:
            return "preference"
        elif "Dominance" in rule_name or "Dependence" in rule_name:
            return "pattern"
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
    
    @staticmethod
    def _evidence_for_subjects(evidence, topics, creators):
        """The evidence bearing on a rule's declared subjects.

        Matching is on the metadata the collectors write - topic for topical
        evidence, creator for creator evidence - so temporal and interaction
        evidence, which is about no particular subject, is never selected here
        and reaches only the rules that declare nothing.

        Returns an empty list when nothing matches, which the caller reads as
        "this rule made no selection" rather than "this rule has no evidence".
        """
        wanted_topics = {str(t).lower().lstrip("#") for t in topics if t}
        wanted_creators = {str(c).lower() for c in creators if c}
        if not wanted_topics and not wanted_creators:
            return []

        picked = []
        for ev in evidence:
            meta = ev.metadata or {}
            topic = str(meta.get("topic", "")).lower().lstrip("#")
            creator = str(meta.get("creator", "")).lower()
            if (topic and topic in wanted_topics) or (creator and creator in wanted_creators):
                picked.append(ev)
        return picked

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
