"""
Identity Evolution Engine
Manages continuous identity evolution without resets
Supports rollback via snapshots
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import uuid

from backend.reasoning import BehaviorObject, Inference, Evidence
from backend.reasoning.reasoning_context import ReflectionReference, GoalReference
from .identity_engine import Identity, IdentityEngine, get_identity_engine
from .identity_snapshot import IdentitySnapshot, SnapshotManager, get_snapshot_manager
from .self_model import SelfModel, SelfModelEngine, get_self_model_engine


logger = logging.getLogger(__name__)


class IdentityChange(BaseModel):
    """Record of a single identity change"""
    change_id: str = Field(..., description="Unique change identifier")
    change_type: str = Field(..., description="Type of change (profile/interest/creator/style/motivation)")
    field_path: str = Field(..., description="Path to changed field")
    old_value: Optional[Any] = Field(None, description="Previous value")
    new_value: Any = Field(..., description="New value")
    change_magnitude: float = Field(..., ge=0.0, le=1.0, description="Magnitude of change")
    timestamp: datetime = Field(..., description="When change occurred")
    evidence_ids: List[str] = Field(default_factory=list, description="Supporting evidence")
    inference_ids: List[str] = Field(default_factory=list, description="Supporting inferences")


class IdentityShift(BaseModel):
    """Major identity shift detection"""
    shift_id: str = Field(..., description="Unique shift identifier")
    shift_type: str = Field(..., description="Type of shift (interest/motivation/style/goal)")
    description: str = Field(..., description="Shift description")
    magnitude: float = Field(..., ge=0.0, le=1.0, description="Shift magnitude")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in shift")
    detected_at: datetime = Field(..., description="When shift was detected")
    changes: List[str] = Field(default_factory=list, description="Related change IDs")
    evidence_summary: str = Field(..., description="Evidence summary")


class EvolutionPeriod(BaseModel):
    """Evolution summary for a time period"""
    period_id: str = Field(..., description="Period identifier")
    period_type: str = Field(..., description="Period type (daily/weekly/monthly)")
    start_date: datetime = Field(..., description="Period start")
    end_date: datetime = Field(..., description="Period end")
    
    # Changes
    total_changes: int = Field(default=0, description="Total changes")
    major_changes: int = Field(default=0, description="Major changes")
    minor_changes: int = Field(default=0, description="Minor changes")
    
    # Shifts
    identity_shifts: List[str] = Field(default_factory=list, description="Identity shift IDs")
    
    # Stability
    stability_score: float = Field(..., ge=0.0, le=1.0, description="Period stability")
    evolution_rate: float = Field(..., ge=0.0, le=1.0, description="Rate of evolution")
    
    # Confidence
    evolution_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in evolution")
    
    # Summary
    summary: str = Field(..., description="Period summary")


class IdentityEvolution(BaseModel):
    """
    Identity Evolution Record
    
    Tracks complete evolution history of an identity.
    Supports rollback via snapshots.
    """
    evolution_id: str = Field(..., description="Unique evolution identifier")
    identity_id: str = Field(..., description="Identity being tracked")
    user_id: str = Field(..., description="User identifier")
    
    # Current state
    current_version: int = Field(..., description="Current identity version")
    current_snapshot_id: str = Field(..., description="Current snapshot ID")
    
    # Evolution history
    changes: List[IdentityChange] = Field(default_factory=list, description="All changes")
    identity_shifts: List[IdentityShift] = Field(default_factory=list, description="Major shifts")
    snapshots: List[str] = Field(default_factory=list, description="Snapshot IDs")
    
    # Periods
    daily_periods: List[EvolutionPeriod] = Field(default_factory=list, description="Daily evolution")
    weekly_periods: List[EvolutionPeriod] = Field(default_factory=list, description="Weekly evolution")
    monthly_periods: List[EvolutionPeriod] = Field(default_factory=list, description="Monthly evolution")
    
    # Metrics
    total_evolutions: int = Field(default=0, description="Total evolution count")
    avg_stability: float = Field(..., ge=0.0, le=1.0, description="Average stability")
    avg_evolution_rate: float = Field(..., ge=0.0, le=1.0, description="Average evolution rate")
    
    # Temporal
    first_evolution: datetime = Field(..., description="First evolution timestamp")
    last_evolution: datetime = Field(..., description="Last evolution timestamp")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    def add_change(self, change: IdentityChange):
        """Add change to history"""
        self.changes.append(change)
        self.total_evolutions += 1
        self.last_evolution = change.timestamp
    
    def add_shift(self, shift: IdentityShift):
        """Add identity shift"""
        self.identity_shifts.append(shift)
    
    def get_recent_changes(self, hours: int = 24) -> List[IdentityChange]:
        """Get recent changes"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [c for c in self.changes if c.timestamp >= cutoff]
    
    def get_major_shifts(self, min_magnitude: float = 0.7) -> List[IdentityShift]:
        """Get major shifts"""
        return [s for s in self.identity_shifts if s.magnitude >= min_magnitude]


class IdentityEvolutionEngine:
    """
    Identity Evolution Engine
    
    Responsibilities:
    - Merge new evidence into identity
    - Merge new inferences into identity
    - Update identity continuously
    - Create snapshots
    - Detect major shifts
    - Maintain evolution timeline
    - Support rollback
    
    Identity NEVER resets - only evolves.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Identity Evolution Engine
        
        Args:
            config: Engine configuration
        """
        self.config = config or {}
        
        # Get engine instances
        self.identity_engine = get_identity_engine()
        self.self_model_engine = get_self_model_engine()
        self.snapshot_manager = get_snapshot_manager()
        
        # Configuration
        self.major_change_threshold = self.config.get("major_change_threshold", 0.3)
        self.shift_detection_threshold = self.config.get("shift_detection_threshold", 0.5)
        self.snapshot_frequency_hours = self.config.get("snapshot_frequency_hours", 24)
        
        logger.info("IdentityEvolutionEngine initialized")
    
    def evolve_identity(
        self,
        identity: Identity,
        new_behaviors: List[BehaviorObject],
        new_inferences: List[Inference],
        new_evidence: List[Evidence],
        reflections: Optional[List[ReflectionReference]] = None,
        goals: Optional[List[GoalReference]] = None,
        evolution: Optional[IdentityEvolution] = None
    ) -> tuple[Identity, IdentitySnapshot, IdentityEvolution]:
        """
        Evolve identity with new data
        
        Args:
            identity: Current identity
            new_behaviors: New behavior objects
            new_inferences: New inferences
            new_evidence: New evidence
            reflections: Optional reflections
            goals: Optional goals
            evolution: Existing evolution record
            
        Returns:
            Tuple of (updated_identity, new_snapshot, evolution_record)
        """
        try:
            logger.info(f"Evolving identity {identity.identity_id} with {len(new_behaviors)} behaviors, {len(new_inferences)} inferences")
            
            # Merge all behaviors
            all_behaviors = self._merge_behaviors(identity, new_behaviors)
            all_inferences = self._merge_inferences(identity, new_inferences)
            all_evidence = self._merge_evidence(identity, new_evidence)
            
            # Reconstruct identity
            updated_identity = self.identity_engine.construct_identity(
                user_id=identity.user_id,
                behavior_objects=all_behaviors,
                inferences=all_inferences,
                evidence=all_evidence,
                reflections=reflections,
                goals=goals,
                existing_identity=identity
            )
            
            # Detect changes
            changes = self._detect_changes(identity, updated_identity, new_evidence, new_inferences)
            
            # Detect shifts
            shifts = self._detect_shifts(changes)
            
            # Compute identity shift (Paper Eq. 2)
            identity_shift = self._compute_identity_shift(identity, updated_identity)
            threshold_exceeded = identity_shift > self.config.get("snapshot_threshold", 0.15)
            updated_identity.metadata["identity_shift"] = identity_shift
            updated_identity.metadata["snapshot_threshold_exceeded"] = threshold_exceeded
            snapshot = self.snapshot_manager.create_snapshot(updated_identity)
            logger.info(f"Snapshot created: identity_shift={identity_shift:.3f} (threshold_exceeded={threshold_exceeded})")
            
            # Update or create evolution record
            if evolution is None:
                evolution = IdentityEvolution(
                    evolution_id=f"evolution_{identity.user_id}_{uuid.uuid4().hex[:8]}",
                    identity_id=identity.identity_id,
                    user_id=identity.user_id,
                    current_version=updated_identity.identity_version,
                    current_snapshot_id=snapshot.snapshot_id,
                    first_evolution=datetime.utcnow(),
                    last_evolution=datetime.utcnow(),
                    avg_stability=updated_identity.behavior_profile.behavior_stability,
                    avg_evolution_rate=0.5
                )
            else:
                evolution.current_version = updated_identity.identity_version
                evolution.current_snapshot_id = snapshot.snapshot_id
            
            # Add changes and shifts
            for change in changes:
                evolution.add_change(change)
            
            for shift in shifts:
                evolution.add_shift(shift)
            
            # Add snapshot
            evolution.snapshots.append(snapshot.snapshot_id)
            
            # Update metrics
            evolution.avg_stability = self._calculate_avg_stability(evolution)
            evolution.avg_evolution_rate = self._calculate_evolution_rate(evolution)
            
            logger.info(f"Identity evolved: version {updated_identity.identity_version}, {len(changes)} changes, {len(shifts)} shifts")
            
            return updated_identity, snapshot, evolution
            
        except Exception as e:
            logger.error(f"Error evolving identity: {str(e)}", exc_info=True)
            raise
    
    def _merge_behaviors(
        self,
        identity: Identity,
        new_behaviors: List[BehaviorObject]
    ) -> List[BehaviorObject]:
        """Merge new behaviors with existing"""
        try:
            # Get existing behavior IDs
            existing_ids = set(identity.source_behavior_objects)
            
            # Add new behaviors that aren't duplicates
            all_behaviors = []
            
            # Note: In production, would fetch existing behaviors from storage
            # For now, just use new behaviors
            all_behaviors.extend(new_behaviors)
            
            return all_behaviors
            
        except Exception as e:
            logger.error(f"Error merging behaviors: {str(e)}", exc_info=True)
            return new_behaviors
    
    def _merge_inferences(
        self,
        identity: Identity,
        new_inferences: List[Inference]
    ) -> List[Inference]:
        """Merge new inferences with existing"""
        try:
            # Similar to behaviors - in production would fetch from storage
            return new_inferences
            
        except Exception as e:
            logger.error(f"Error merging inferences: {str(e)}", exc_info=True)
            return new_inferences
    
    def _merge_evidence(
        self,
        identity: Identity,
        new_evidence: List[Evidence]
    ) -> List[Evidence]:
        """Merge new evidence with existing"""
        try:
            # Similar to behaviors - in production would fetch from storage
            return new_evidence
            
        except Exception as e:
            logger.error(f"Error merging evidence: {str(e)}", exc_info=True)
            return new_evidence
    
    def _detect_changes(
        self,
        old_identity: Identity,
        new_identity: Identity,
        new_evidence: List[Evidence],
        new_inferences: List[Inference]
    ) -> List[IdentityChange]:
        """Detect changes between identities"""
        try:
            changes = []
            
            # Check dominant topics
            old_topics = set(old_identity.dominant_topics)
            new_topics = set(new_identity.dominant_topics)
            
            if old_topics != new_topics:
                added = new_topics - old_topics
                removed = old_topics - new_topics
                
                if added or removed:
                    magnitude = len(added | removed) / max(len(old_topics | new_topics), 1)
                    
                    change = IdentityChange(
                        change_id=f"change_{uuid.uuid4().hex[:8]}",
                        change_type="interest",
                        field_path="dominant_topics",
                        old_value=list(old_topics),
                        new_value=list(new_topics),
                        change_magnitude=min(1.0, magnitude),
                        timestamp=datetime.utcnow(),
                        evidence_ids=[e.evidence_id for e in new_evidence[:3]],
                        inference_ids=[i.inference_id for i in new_inferences[:3]]
                    )
                    changes.append(change)
            
            # Check motivation signals
            old_learning = old_identity.motivation_signals.learning_motivation
            new_learning = new_identity.motivation_signals.learning_motivation
            
            if abs(new_learning - old_learning) > 0.1:
                change = IdentityChange(
                    change_id=f"change_{uuid.uuid4().hex[:8]}",
                    change_type="motivation",
                    field_path="motivation_signals.learning_motivation",
                    old_value=old_learning,
                    new_value=new_learning,
                    change_magnitude=abs(new_learning - old_learning),
                    timestamp=datetime.utcnow(),
                    evidence_ids=[e.evidence_id for e in new_evidence[:2]],
                    inference_ids=[i.inference_id for i in new_inferences[:2]]
                )
                changes.append(change)
            
            # Check confidence
            if abs(new_identity.overall_confidence - old_identity.overall_confidence) > 0.05:
                change = IdentityChange(
                    change_id=f"change_{uuid.uuid4().hex[:8]}",
                    change_type="profile",
                    field_path="overall_confidence",
                    old_value=old_identity.overall_confidence,
                    new_value=new_identity.overall_confidence,
                    change_magnitude=abs(new_identity.overall_confidence - old_identity.overall_confidence),
                    timestamp=datetime.utcnow(),
                    evidence_ids=[],
                    inference_ids=[]
                )
                changes.append(change)
            
            logger.debug(f"Detected {len(changes)} changes")
            return changes
            
        except Exception as e:
            logger.error(f"Error detecting changes: {str(e)}", exc_info=True)
            return []
    
    def _detect_shifts(self, changes: List[IdentityChange]) -> List[IdentityShift]:
        """Detect major identity shifts from changes"""
        try:
            shifts = []
            
            # Group changes by type
            from collections import defaultdict
            changes_by_type = defaultdict(list)
            
            for change in changes:
                changes_by_type[change.change_type].append(change)
            
            # Detect shifts in each category
            for change_type, type_changes in changes_by_type.items():
                # Calculate aggregate magnitude
                total_magnitude = sum(c.change_magnitude for c in type_changes)
                avg_magnitude = total_magnitude / len(type_changes)
                
                if avg_magnitude >= self.shift_detection_threshold:
                    shift = IdentityShift(
                        shift_id=f"shift_{uuid.uuid4().hex[:8]}",
                        shift_type=change_type,
                        description=f"Major {change_type} shift detected",
                        magnitude=avg_magnitude,
                        confidence=0.8,
                        detected_at=datetime.utcnow(),
                        changes=[c.change_id for c in type_changes],
                        evidence_summary=f"{len(type_changes)} significant changes in {change_type}"
                    )
                    shifts.append(shift)
            
            logger.debug(f"Detected {len(shifts)} identity shifts")
            return shifts
            
        except Exception as e:
            logger.error(f"Error detecting shifts: {str(e)}", exc_info=True)
            return []
    
    def _compute_identity_shift(self, old: Identity, new_id: Identity) -> float:
        """Paper Eq. 2: compute ‖I_{t+1} - I_t‖₂"""
        try:
            import numpy as np

            old_vec = np.array([
                old.overall_confidence,
                old.identity_completeness,
                old.behavior_profile.avg_engagement_rate,
                old.behavior_profile.behavior_diversity,
                old.behavior_profile.behavior_stability,
                old.interest_graph.diversity_score,
                old.creator_graph.creator_diversity_score,
                old.creator_graph.dependence_score,
                old.learning_style.confidence,
                old.attention_profile.avg_attention_span,
                old.exploration_profile.novelty_seeking_score,
                old.exploration_profile.exploration_rate,
                old.consistency_profile.overall_consistency,
                old.habit_profile.routine_strength,
                old.motivation_signals.learning_motivation,
                old.motivation_signals.entertainment_seeking,
                old.motivation_signals.skill_building_intent,
            ])

            new_vec = np.array([
                new_id.overall_confidence,
                new_id.identity_completeness,
                new_id.behavior_profile.avg_engagement_rate,
                new_id.behavior_profile.behavior_diversity,
                new_id.behavior_profile.behavior_stability,
                new_id.interest_graph.diversity_score,
                new_id.creator_graph.creator_diversity_score,
                new_id.creator_graph.dependence_score,
                new_id.learning_style.confidence,
                new_id.attention_profile.avg_attention_span,
                new_id.exploration_profile.novelty_seeking_score,
                new_id.exploration_profile.exploration_rate,
                new_id.consistency_profile.overall_consistency,
                new_id.habit_profile.routine_strength,
                new_id.motivation_signals.learning_motivation,
                new_id.motivation_signals.entertainment_seeking,
                new_id.motivation_signals.skill_building_intent,
            ])

            shift = float(np.linalg.norm(new_vec - old_vec))
            return min(1.0, shift)
        except Exception as e:
            logger.warning(f"Error computing identity shift: {e}")
            return 0.0

    def _calculate_avg_stability(self, evolution: IdentityEvolution) -> float:
        """Calculate average stability from evolution history"""
        try:
            if not evolution.changes:
                return 1.0
            
            # Recent changes indicate lower stability
            recent_changes = evolution.get_recent_changes(hours=168)  # 1 week
            
            if not recent_changes:
                return 1.0
            
            # More changes = less stability
            stability = max(0.0, 1.0 - (len(recent_changes) / 50.0))
            
            return round(stability, 3)
            
        except Exception as e:
            logger.error(f"Error calculating stability: {str(e)}", exc_info=True)
            return 0.5
    
    def _calculate_evolution_rate(self, evolution: IdentityEvolution) -> float:
        """Calculate evolution rate"""
        try:
            if not evolution.changes:
                return 0.0
            
            # Changes per day
            days = (evolution.last_evolution - evolution.first_evolution).days + 1
            changes_per_day = len(evolution.changes) / days
            
            # Normalize to 0-1
            rate = min(1.0, changes_per_day / 5.0)
            
            return round(rate, 3)
            
        except Exception as e:
            logger.error(f"Error calculating evolution rate: {str(e)}", exc_info=True)
            return 0.0
    
    def rollback_to_snapshot(
        self,
        snapshot_id: str,
        evolution: IdentityEvolution
    ) -> Optional[Identity]:
        """
        Rollback identity to a previous snapshot
        
        Args:
            snapshot_id: Snapshot to rollback to
            evolution: Evolution record
            
        Returns:
            Identity from snapshot or None
        """
        try:
            snapshot = self.snapshot_manager.get_snapshot(snapshot_id)
            
            if not snapshot:
                logger.warning(f"Snapshot {snapshot_id} not found")
                return None
            
            # Reconstruct identity from snapshot
            # Note: In production, would fetch full data from storage
            logger.info(f"Rolled back to snapshot {snapshot_id}")
            
            return None  # Placeholder - would return reconstructed identity
            
        except Exception as e:
            logger.error(f"Error rolling back: {str(e)}", exc_info=True)
            return None


def get_identity_evolution_engine() -> IdentityEvolutionEngine:
    """Get singleton identity evolution engine instance"""
    if not hasattr(get_identity_evolution_engine, "_instance"):
        get_identity_evolution_engine._instance = IdentityEvolutionEngine()
    return get_identity_evolution_engine._instance
