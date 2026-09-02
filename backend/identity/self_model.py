"""
Self Model
AI's internal beliefs about the user (not facts)
Includes uncertainty tracking and counter-evidence
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import logging
import uuid

from backend.reasoning import Inference, Evidence
from .identity_snapshot import IdentitySnapshot


logger = logging.getLogger(__name__)


# One observation in three arguing the other way makes a belief contested.
# Stated as a share rather than a count so it does not drift with how much
# the account has been used: net strength is (support - counter) / total, so
# a third of observations dissenting lands exactly here.
CONTESTED_NET_STRENGTH = 1.0 / 3.0


class BeliefType(str, Enum):
    """Type of belief"""
    MOTIVATION = "motivation"
    PREFERENCE = "preference"
    GOAL = "goal"
    PATTERN = "pattern"
    TRAIT = "trait"
    TRANSITION = "transition"
    CAPABILITY = "capability"


class Belief(BaseModel):
    """
    Individual Belief
    
    Represents AI's belief about the user.
    Beliefs are NOT facts - they are interpretations with uncertainty.
    """
    belief_id: str = Field(..., description="Unique belief identifier")
    belief_type: BeliefType = Field(..., description="Type of belief")
    
    # Core belief
    statement: str = Field(..., description="Belief statement")
    description: str = Field(..., description="Detailed description")
    
    # Strength
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in belief")
    uncertainty: float = Field(..., ge=0.0, le=1.0, description="Uncertainty level")
    strength: float = Field(..., ge=0.0, le=1.0, description="Overall belief strength")
    
    # Evidence
    supporting_evidence: List[str] = Field(default_factory=list, description="Supporting evidence IDs")
    counter_evidence: List[str] = Field(default_factory=list, description="Counter evidence IDs")
    supporting_inferences: List[str] = Field(default_factory=list, description="Supporting inference IDs")
    
    # Evidence summary
    evidence_count: int = Field(default=0, description="Total evidence count")
    counter_evidence_count: int = Field(default=0, description="Counter evidence count")
    net_evidence_strength: float = Field(..., ge=-1.0, le=1.0, description="Net evidence strength")
    
    # Temporal
    formed_at: datetime = Field(..., description="When belief was formed")
    updated_at: datetime = Field(..., description="Last update")
    last_reinforced: Optional[datetime] = Field(None, description="Last reinforcement")
    last_challenged: Optional[datetime] = Field(None, description="Last challenge")
    
    # Evolution
    version: int = Field(default=1, description="Belief version")
    evolution_history: List[Dict[str, Any]] = Field(default_factory=list, description="Belief evolution")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    def update_version(self):
        """Increment version and update timestamp"""
        self.version += 1
        self.updated_at = datetime.utcnow()
    
    def reinforce(self, evidence_id: str):
        """Reinforce belief with new evidence"""
        if evidence_id not in self.supporting_evidence:
            self.supporting_evidence.append(evidence_id)
            self.evidence_count += 1
            self.last_reinforced = datetime.utcnow()
            self.update_version()
    
    def challenge(self, counter_evidence_id: str):
        """Challenge belief with counter evidence"""
        if counter_evidence_id not in self.counter_evidence:
            self.counter_evidence.append(counter_evidence_id)
            self.counter_evidence_count += 1
            self.last_challenged = datetime.utcnow()
            self.update_version()
    
    def is_strong(self, threshold: float = 0.7) -> bool:
        """Strong when the belief is well supported AND not contested.

        The second half matters: without it STRONG and UNCERTAIN were
        independent predicates and a belief could be both at once, which is
        not a classification.

        The bar is deliberately not "no counter-evidence at all". Measured on
        real histories almost every claim accumulates some skipped
        observations, so a zero-counter requirement would make STRONG
        unreachable and collapse the distinction it exists to draw.
        """
        return self.strength >= threshold and not self.is_uncertain()
    
    def is_uncertain(self, threshold: float = 0.5) -> bool:
        """Uncertain when the inference behind it was weak, or when the
        observations underneath it are close to evenly split.

        The second half is the part that was missing. Uncertainty was
        1 - confidence and nothing else, so a belief resting on evidence that
        contradicted itself as often as it supported it was still reported as
        settled. A third of the observations pointing the other way is enough
        to say the question is open.
        """
        if self.uncertainty >= threshold:
            return True
        return self.net_evidence_strength <= CONTESTED_NET_STRENGTH


class UncertaintyMap(BaseModel):
    """
    Uncertainty Map
    
    Tracks uncertainty levels across different domains.
    Character knows where it is uncertain - critical for research.
    """
    # Domain uncertainties
    domain_uncertainties: Dict[str, float] = Field(
        default_factory=dict,
        description="Uncertainty by domain (0=certain, 1=uncertain)"
    )
    
    # Topic uncertainties
    topic_uncertainties: Dict[str, float] = Field(
        default_factory=dict,
        description="Uncertainty by topic"
    )
    
    # Overall uncertainty
    overall_uncertainty: float = Field(..., ge=0.0, le=1.0, description="Overall uncertainty")
    
    # High uncertainty areas
    high_uncertainty_domains: List[str] = Field(default_factory=list, description="High uncertainty domains")
    low_uncertainty_domains: List[str] = Field(default_factory=list, description="Low uncertainty domains")
    
    # Metadata
    last_updated: datetime = Field(..., description="Last update timestamp")
    
    def add_domain_uncertainty(self, domain: str, uncertainty: float):
        """
        Add or update domain uncertainty
        
        Args:
            domain: Domain name
            uncertainty: Uncertainty level (0-1)
        """
        self.domain_uncertainties[domain] = max(0.0, min(1.0, uncertainty))
        self._update_categorization()
        self.last_updated = datetime.utcnow()
    
    def get_domain_uncertainty(self, domain: str) -> float:
        """
        Get uncertainty for domain
        
        Args:
            domain: Domain name
            
        Returns:
            Uncertainty level (0-1)
        """
        return self.domain_uncertainties.get(domain, 0.5)
    
    def _update_categorization(self):
        """Update high/low uncertainty categorization"""
        self.high_uncertainty_domains = [
            domain for domain, unc in self.domain_uncertainties.items()
            if unc > 0.6
        ]
        
        self.low_uncertainty_domains = [
            domain for domain, unc in self.domain_uncertainties.items()
            if unc < 0.3
        ]
        
        # Update overall
        if self.domain_uncertainties:
            self.overall_uncertainty = sum(self.domain_uncertainties.values()) / len(self.domain_uncertainties)
        else:
            self.overall_uncertainty = 0.5


class SelfModel(BaseModel):
    """
    Self Model
    
    AI's internal belief system about the user.
    
    Difference from Identity:
    - Identity = FACTS (measurable, evidence-based)
    - Self Model = BELIEFS (interpretations with uncertainty)
    
    Example:
    - Identity: "User watched 50 AI tutorials with 0.82 engagement"
    - Self Model: "I believe the user is transitioning into AI engineering"
    """
    # Core identification
    self_model_id: str = Field(..., description="Unique self model identifier")
    user_id: str = Field(..., description="User identifier")
    identity_snapshot_id: str = Field(..., description="Source identity snapshot ID")
    
    # Beliefs
    beliefs: List[Belief] = Field(default_factory=list, description="Active beliefs")
    strong_beliefs: List[str] = Field(default_factory=list, description="Strong belief IDs")
    uncertain_beliefs: List[str] = Field(default_factory=list, description="Uncertain belief IDs")
    
    # Uncertainty map
    uncertainty_map: UncertaintyMap = Field(..., description="Uncertainty tracking")
    
    # Primary beliefs (most important)
    primary_motivation_belief: Optional[str] = Field(None, description="Primary motivation belief")
    primary_goal_belief: Optional[str] = Field(None, description="Primary goal belief")
    primary_transition_belief: Optional[str] = Field(None, description="Primary transition belief")
    
    # Confidence
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall model confidence")
    model_completeness: float = Field(..., ge=0.0, le=1.0, description="Model completeness")
    
    # Versioning
    model_version: int = Field(default=1, description="Model version")
    
    # Temporal
    created_at: datetime = Field(..., description="When model was created")
    updated_at: datetime = Field(..., description="Last update")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    def update_version(self):
        """Increment version and update timestamp"""
        self.model_version += 1
        self.updated_at = datetime.utcnow()
    
    def add_belief(self, belief: Belief):
        """
        Add belief to model
        
        Args:
            belief: Belief to add
        """
        self.beliefs.append(belief)
        
        if belief.is_strong():
            self.strong_beliefs.append(belief.belief_id)
        
        if belief.is_uncertain():
            self.uncertain_beliefs.append(belief.belief_id)
        
        self.update_version()
    
    def get_belief(self, belief_id: str) -> Optional[Belief]:
        """
        Get belief by ID
        
        Args:
            belief_id: Belief identifier
            
        Returns:
            Belief if found
        """
        for belief in self.beliefs:
            if belief.belief_id == belief_id:
                return belief
        return None
    
    def get_beliefs_by_type(self, belief_type: BeliefType) -> List[Belief]:
        """
        Get beliefs by type
        
        Args:
            belief_type: Belief type
            
        Returns:
            List of beliefs
        """
        return [b for b in self.beliefs if b.belief_type == belief_type]
    
    def get_strong_beliefs(self) -> List[Belief]:
        """Get all strong beliefs"""
        return [b for b in self.beliefs if b.is_strong()]
    
    def get_uncertain_beliefs(self) -> List[Belief]:
        """Get all uncertain beliefs"""
        return [b for b in self.beliefs if b.is_uncertain()]


class SelfModelEngine:
    """
    Self Model Engine
    
    Constructs and maintains AI's belief system about the user.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Self Model Engine
        
        Args:
            config: Engine configuration
        """
        self.config = config or {}
        self.min_evidence_for_belief = self.config.get("min_evidence", 2)
        self.belief_confidence_threshold = self.config.get("confidence_threshold", 0.6)
        
        logger.info("SelfModelEngine initialized")
    
    def construct_self_model(
        self,
        user_id: str,
        identity_snapshot: IdentitySnapshot,
        inferences: List[Inference],
        evidence: List[Evidence],
        existing_model: Optional[SelfModel] = None
    ) -> SelfModel:
        """
        Construct or update self model from identity snapshot and inferences
        
        Args:
            user_id: User identifier
            identity_snapshot: Identity snapshot
            inferences: List of inferences
            evidence: List of evidence
            existing_model: Existing model to update
            
        Returns:
            SelfModel
        """
        try:
            logger.info(f"Constructing self model for user {user_id} from snapshot {identity_snapshot.snapshot_id}")
            
            # Generate beliefs from inferences
            beliefs = self._generate_beliefs_from_inferences(inferences, evidence)
            
            # Build uncertainty map
            uncertainty_map = self._build_uncertainty_map(identity_snapshot, beliefs)
            
            # Identify primary beliefs
            motivation_belief = self._identify_primary_motivation_belief(beliefs)
            goal_belief = self._identify_primary_goal_belief(beliefs)
            transition_belief = self._identify_primary_transition_belief(beliefs)
            
            # Calculate confidence
            overall_confidence = self._calculate_model_confidence(beliefs, evidence)
            model_completeness = self._calculate_model_completeness(beliefs)
            
            # Categorize beliefs
            strong_beliefs = [b.belief_id for b in beliefs if b.is_strong()]
            uncertain_beliefs = [b.belief_id for b in beliefs if b.is_uncertain()]
            
            # Create or update model
            if existing_model:
                model = existing_model
                model.beliefs = beliefs
                model.strong_beliefs = strong_beliefs
                model.uncertain_beliefs = uncertain_beliefs
                model.uncertainty_map = uncertainty_map
                model.primary_motivation_belief = motivation_belief
                model.primary_goal_belief = goal_belief
                model.primary_transition_belief = transition_belief
                model.overall_confidence = overall_confidence
                model.model_completeness = model_completeness
                model.update_version()
            else:
                model = SelfModel(
                    self_model_id=f"selfmodel_{user_id}_{uuid.uuid4().hex[:8]}",
                    user_id=user_id,
                    identity_snapshot_id=identity_snapshot.snapshot_id,
                    beliefs=beliefs,
                    strong_beliefs=strong_beliefs,
                    uncertain_beliefs=uncertain_beliefs,
                    uncertainty_map=uncertainty_map,
                    primary_motivation_belief=motivation_belief,
                    primary_goal_belief=goal_belief,
                    primary_transition_belief=transition_belief,
                    overall_confidence=overall_confidence,
                    model_completeness=model_completeness,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            
            logger.info(f"Self model constructed: {model.self_model_id}, {len(beliefs)} beliefs, confidence {overall_confidence:.2f}")
            return model
            
        except Exception as e:
            logger.error(f"Error constructing self model: {str(e)}", exc_info=True)
            raise
    
    def _generate_beliefs_from_inferences(
        self,
        inferences: List[Inference],
        evidence: List[Evidence]
    ) -> List[Belief]:
        """Generate beliefs from inferences"""
        try:
            beliefs = []
            
            for inference in inferences:
                # Map inference type to belief type
                if inference.inference_type == "motivation":
                    belief_type = BeliefType.MOTIVATION
                elif inference.inference_type == "pattern":
                    belief_type = BeliefType.PATTERN
                elif inference.inference_type == "preference":
                    belief_type = BeliefType.PREFERENCE
                elif inference.inference_type == "goal_signal":
                    belief_type = BeliefType.GOAL
                else:
                    belief_type = BeliefType.TRAIT
                
                # Create belief statement
                statement = f"I believe {inference.description.lower()}"
                
                # Calculate uncertainty
                uncertainty = 1.0 - inference.confidence
                
                # Get supporting evidence
                supporting_evidence_ids = inference.supporting_evidence
                
                # Counter-evidence reaches a belief two ways: another piece of
                # evidence conflicting with a supporting one, and the single
                # observations a supporting piece recorded as contradicting
                # itself. The second is what the collectors actually produce -
                # a skipped reel is not its own Evidence object - so a belief
                # reading only the first went on reporting none of either.
                counter_evidence_ids = []
                support_observations = 0
                matched_evidence = 0
                for evidence_id in supporting_evidence_ids:
                    for ev in evidence:
                        if ev.evidence_id != evidence_id:
                            continue
                        matched_evidence += 1
                        support_observations += len(ev.supporting_events)
                        counter_evidence_ids.extend(ev.counter_evidence_ids)
                        counter_evidence_ids.extend(ev.conflicting_observations)

                evidence_count = len(supporting_evidence_ids)
                counter_count = len(counter_evidence_ids)

                # Both sides of the ratio have to be in the same unit. The
                # supporting side is a count of evidence objects and the
                # contradicting side is a count of individual observations, so
                # comparing them directly would let three pieces of evidence
                # carrying thirty skips between them read as -0.82 and bury a
                # belief that is merely mixed. Where the evidence objects are
                # in hand their own observations are counted instead; where
                # they are not, nothing is known to contradict and the old
                # object-level count still applies.
                if matched_evidence:
                    support_side = support_observations
                else:
                    support_side = evidence_count
                net_strength = (
                    (support_side - counter_count) / max(1, support_side + counter_count)
                )
                net_strength = max(-1.0, min(1.0, net_strength))
                
                belief = Belief(
                    belief_id=f"belief_{inference.inference_id}_{uuid.uuid4().hex[:6]}",
                    belief_type=belief_type,
                    statement=statement,
                    description=inference.description,
                    confidence=inference.confidence,
                    uncertainty=uncertainty,
                    strength=inference.strength,
                    supporting_evidence=supporting_evidence_ids,
                    counter_evidence=counter_evidence_ids,
                    supporting_inferences=[inference.inference_id],
                    evidence_count=evidence_count,
                    counter_evidence_count=counter_count,
                    net_evidence_strength=net_strength,
                    formed_at=inference.inferred_at,
                    updated_at=datetime.utcnow()
                )
                
                beliefs.append(belief)
            
            logger.debug(f"Generated {len(beliefs)} beliefs from {len(inferences)} inferences")
            return beliefs
            
        except Exception as e:
            logger.error(f"Error generating beliefs: {str(e)}", exc_info=True)
            return []
    
    def _build_uncertainty_map(
        self,
        identity_snapshot: IdentitySnapshot,
        beliefs: List[Belief]
    ) -> UncertaintyMap:
        """Build uncertainty map from identity and beliefs"""
        try:
            uncertainty_map = UncertaintyMap(
                overall_uncertainty=0.5,
                last_updated=datetime.utcnow()
            )
            
            # Add domain uncertainties from dominant topics
            for topic in identity_snapshot.dominant_topics:
                # Find beliefs related to this topic
                topic_beliefs = [
                    b for b in beliefs
                    if topic.lower() in b.description.lower()
                ]
                
                if topic_beliefs:
                    avg_uncertainty = sum(b.uncertainty for b in topic_beliefs) / len(topic_beliefs)
                    uncertainty_map.add_domain_uncertainty(topic, avg_uncertainty)
                else:
                    # No beliefs = high uncertainty
                    uncertainty_map.add_domain_uncertainty(topic, 0.8)
            
            # Add uncertainties for emerging topics (higher uncertainty)
            for topic in identity_snapshot.emerging_topics:
                uncertainty_map.add_domain_uncertainty(topic, 0.7)
            
            logger.debug(f"Built uncertainty map with {len(uncertainty_map.domain_uncertainties)} domains")
            return uncertainty_map
            
        except Exception as e:
            logger.error(f"Error building uncertainty map: {str(e)}", exc_info=True)
            return UncertaintyMap(overall_uncertainty=0.5, last_updated=datetime.utcnow())
    
    def _identify_primary_motivation_belief(self, beliefs: List[Belief]) -> Optional[str]:
        """Identify primary motivation belief"""
        motivation_beliefs = [b for b in beliefs if b.belief_type == BeliefType.MOTIVATION]
        if not motivation_beliefs:
            return None
        
        # Return strongest motivation belief
        motivation_beliefs.sort(key=lambda b: b.strength, reverse=True)
        return motivation_beliefs[0].belief_id
    
    def _identify_primary_goal_belief(self, beliefs: List[Belief]) -> Optional[str]:
        """Identify primary goal belief"""
        goal_beliefs = [b for b in beliefs if b.belief_type == BeliefType.GOAL]
        if not goal_beliefs:
            return None
        
        goal_beliefs.sort(key=lambda b: b.strength, reverse=True)
        return goal_beliefs[0].belief_id
    
    def _identify_primary_transition_belief(self, beliefs: List[Belief]) -> Optional[str]:
        """Identify primary transition belief"""
        transition_beliefs = [b for b in beliefs if b.belief_type == BeliefType.TRANSITION]
        if not transition_beliefs:
            return None
        
        transition_beliefs.sort(key=lambda b: b.strength, reverse=True)
        return transition_beliefs[0].belief_id
    
    def _calculate_model_confidence(
        self,
        beliefs: List[Belief],
        evidence: List[Evidence]
    ) -> float:
        """Calculate overall model confidence"""
        if not beliefs:
            return 0.0
        
        # Average belief confidence
        avg_belief_confidence = sum(b.confidence for b in beliefs) / len(beliefs)
        
        # Evidence quality
        if evidence:
            avg_evidence_confidence = sum(e.confidence for e in evidence) / len(evidence)
        else:
            avg_evidence_confidence = 0.5
        
        # Weighted average
        overall = avg_belief_confidence * 0.7 + avg_evidence_confidence * 0.3
        
        return round(overall, 3)
    
    def _calculate_model_completeness(self, beliefs: List[Belief]) -> float:
        """Calculate model completeness"""
        # Check for different belief types
        has_motivation = any(b.belief_type == BeliefType.MOTIVATION for b in beliefs)
        has_preference = any(b.belief_type == BeliefType.PREFERENCE for b in beliefs)
        has_pattern = any(b.belief_type == BeliefType.PATTERN for b in beliefs)
        
        completeness = 0.0
        if has_motivation:
            completeness += 0.4
        if has_preference:
            completeness += 0.3
        if has_pattern:
            completeness += 0.3
        
        return round(completeness, 3)


def get_self_model_engine() -> SelfModelEngine:
    """Get singleton self model engine instance"""
    if not hasattr(get_self_model_engine, "_instance"):
        get_self_model_engine._instance = SelfModelEngine()
    return get_self_model_engine._instance
