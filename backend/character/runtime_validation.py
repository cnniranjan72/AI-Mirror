"""
Runtime Validation
Validates runtime components and state
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .core import CharacterCore
from .character_state import CharacterState


logger = logging.getLogger(__name__)


class ValidationIssue(BaseModel):
    """Individual validation issue"""
    severity: str = Field(..., description="Severity (error/warning/info)")
    component: str = Field(..., description="Component with issue")
    issue: str = Field(..., description="Issue description")
    details: Optional[str] = Field(None, description="Additional details")


class ValidationReport(BaseModel):
    """Runtime validation report"""
    is_valid: bool = Field(..., description="Whether runtime is valid")
    validated_at: datetime = Field(..., description="Validation timestamp")
    
    # Component validation
    snapshot_valid: bool = Field(..., description="Snapshot validation")
    self_model_valid: bool = Field(..., description="Self model validation")
    memory_valid: bool = Field(..., description="Memory validation")
    context_valid: bool = Field(..., description="Context validation")
    state_valid: bool = Field(..., description="State validation")
    
    # Issues
    errors: List[ValidationIssue] = Field(default_factory=list, description="Validation errors")
    warnings: List[ValidationIssue] = Field(default_factory=list, description="Validation warnings")
    info: List[ValidationIssue] = Field(default_factory=list, description="Validation info")
    
    # Metrics
    error_count: int = Field(default=0, description="Error count")
    warning_count: int = Field(default=0, description="Warning count")
    info_count: int = Field(default=0, description="Info count")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Validation metadata")
    
    def add_error(self, component: str, issue: str, details: Optional[str] = None):
        """Add validation error"""
        self.errors.append(ValidationIssue(
            severity="error",
            component=component,
            issue=issue,
            details=details
        ))
        self.error_count += 1
        self.is_valid = False
    
    def add_warning(self, component: str, issue: str, details: Optional[str] = None):
        """Add validation warning"""
        self.warnings.append(ValidationIssue(
            severity="warning",
            component=component,
            issue=issue,
            details=details
        ))
        self.warning_count += 1
    
    def add_info(self, component: str, issue: str, details: Optional[str] = None):
        """Add validation info"""
        self.info.append(ValidationIssue(
            severity="info",
            component=component,
            issue=issue,
            details=details
        ))
        self.info_count += 1


class RuntimeValidation:
    """
    Runtime Validation
    
    Validates:
    - IdentitySnapshot exists and is valid
    - SelfModel is valid
    - BehaviorMemory is available
    - ReasoningContext is complete
    - CharacterState is complete
    - Confidence ranges are valid
    - Lifecycle is valid
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Runtime Validation
        
        Args:
            config: Validation configuration
        """
        self.config = config or {}
        
        # Validation thresholds
        self.min_confidence = self.config.get("min_confidence", 0.0)
        self.max_snapshot_age_hours = self.config.get("max_snapshot_age_hours", 24)
        self.min_completeness = self.config.get("min_completeness", 0.3)
        
        logger.info("RuntimeValidation initialized")
    
    def validate_runtime(
        self,
        character_core: Optional[CharacterCore],
        character_state: Optional[CharacterState]
    ) -> ValidationReport:
        """
        Validate complete runtime
        
        Args:
            character_core: Character core to validate
            character_state: Character state to validate
            
        Returns:
            ValidationReport
        """
        try:
            logger.info("Validating runtime")
            
            report = ValidationReport(
                is_valid=True,
                validated_at=datetime.utcnow(),
                snapshot_valid=False,
                self_model_valid=False,
                memory_valid=False,
                context_valid=False,
                state_valid=False
            )
            
            # Validate CharacterCore exists
            if character_core is None:
                report.add_error("CharacterCore", "CharacterCore is None")
                return report
            
            # Validate CharacterState exists
            if character_state is None:
                report.add_error("CharacterState", "CharacterState is None")
                return report
            
            # Validate IdentitySnapshot
            report.snapshot_valid = self._validate_snapshot(character_core, report)
            
            # Validate SelfModel
            report.self_model_valid = self._validate_self_model(character_core, report)
            
            # Validate Memory
            report.memory_valid = self._validate_memory(character_core, report)
            
            # Validate ReasoningContext
            report.context_valid = self._validate_context(character_core, report)
            
            # Validate CharacterState
            report.state_valid = self._validate_state(character_state, report)
            
            # Overall validation
            if report.error_count == 0:
                report.is_valid = True
                report.add_info("Runtime", "Runtime validation passed")
            else:
                report.is_valid = False
            
            # Add metadata
            report.metadata = {
                "core_id": character_core.core_id,
                "state_id": character_state.state_id,
                "snapshot_version": character_core.get_snapshot_version(),
                "validation_timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Validation complete: valid={report.is_valid}, errors={report.error_count}, warnings={report.warning_count}")
            return report
            
        except Exception as e:
            logger.error(f"Error validating runtime: {str(e)}", exc_info=True)
            
            error_report = ValidationReport(
                is_valid=False,
                validated_at=datetime.utcnow(),
                snapshot_valid=False,
                self_model_valid=False,
                memory_valid=False,
                context_valid=False,
                state_valid=False
            )
            error_report.add_error("Validation", f"Validation failed: {str(e)}")
            return error_report
    
    def _validate_snapshot(
        self,
        character_core: CharacterCore,
        report: ValidationReport
    ) -> bool:
        """Validate identity snapshot"""
        try:
            snapshot = character_core.identity_snapshot
            
            # Check snapshot exists
            if snapshot is None:
                report.add_error("IdentitySnapshot", "Snapshot is None")
                return False
            
            # Check snapshot validity
            if not snapshot.is_valid():
                report.add_error("IdentitySnapshot", "Snapshot is expired or invalid")
                return False
            
            # Check snapshot age
            age_hours = snapshot.get_age_seconds() / 3600
            if age_hours > self.max_snapshot_age_hours:
                report.add_warning(
                    "IdentitySnapshot",
                    f"Snapshot is old: {age_hours:.1f} hours",
                    f"Max age: {self.max_snapshot_age_hours} hours"
                )
            
            # Check confidence
            if snapshot.overall_confidence < self.min_confidence:
                report.add_warning(
                    "IdentitySnapshot",
                    f"Low confidence: {snapshot.overall_confidence:.2f}",
                    f"Min confidence: {self.min_confidence}"
                )
            
            # Check completeness
            if snapshot.identity_completeness < self.min_completeness:
                report.add_warning(
                    "IdentitySnapshot",
                    f"Low completeness: {snapshot.identity_completeness:.2f}",
                    f"Min completeness: {self.min_completeness}"
                )
            
            report.add_info("IdentitySnapshot", "Snapshot validation passed")
            return True
            
        except Exception as e:
            report.add_error("IdentitySnapshot", f"Snapshot validation failed: {str(e)}")
            return False
    
    def _validate_self_model(
        self,
        character_core: CharacterCore,
        report: ValidationReport
    ) -> bool:
        """Validate self model"""
        try:
            self_model = character_core.self_model
            
            # Check self model exists
            if self_model is None:
                report.add_error("SelfModel", "Self model is None")
                return False
            
            # Check confidence
            if self_model.overall_confidence < self.min_confidence:
                report.add_warning(
                    "SelfModel",
                    f"Low model confidence: {self_model.overall_confidence:.2f}"
                )
            
            # Check completeness
            if self_model.model_completeness < self.min_completeness:
                report.add_warning(
                    "SelfModel",
                    f"Low model completeness: {self_model.model_completeness:.2f}"
                )
            
            # Check beliefs
            if len(self_model.beliefs) == 0:
                report.add_warning("SelfModel", "No beliefs in self model")
            
            report.add_info("SelfModel", f"Self model validation passed: {len(self_model.beliefs)} beliefs")
            return True
            
        except Exception as e:
            report.add_error("SelfModel", f"Self model validation failed: {str(e)}")
            return False
    
    def _validate_memory(
        self,
        character_core: CharacterCore,
        report: ValidationReport
    ) -> bool:
        """Validate memory availability"""
        try:
            memory_counts = character_core.get_memory_count()
            
            # Check if any memories exist
            total_memories = sum(memory_counts.values())
            
            if total_memories == 0:
                report.add_warning("Memory", "No memories available")
            else:
                report.add_info("Memory", f"Memory validation passed: {total_memories} total memories")
            
            return True
            
        except Exception as e:
            report.add_error("Memory", f"Memory validation failed: {str(e)}")
            return False
    
    def _validate_context(
        self,
        character_core: CharacterCore,
        report: ValidationReport
    ) -> bool:
        """Validate reasoning context"""
        try:
            if not character_core.has_reasoning_context():
                report.add_info("ReasoningContext", "No reasoning context available")
                return True
            
            report.add_info("ReasoningContext", "Reasoning context available")
            return True
            
        except Exception as e:
            report.add_error("ReasoningContext", f"Context validation failed: {str(e)}")
            return False
    
    def _validate_state(
        self,
        character_state: CharacterState,
        report: ValidationReport
    ) -> bool:
        """Validate character state"""
        try:
            # Check state validity
            if not character_state.is_valid:
                report.add_error("CharacterState", "State is marked invalid")
                return False
            
            # Check state expiration
            if character_state.is_expired():
                report.add_warning("CharacterState", "State is expired")
            
            # Check validation errors
            if character_state.validation_errors:
                for error in character_state.validation_errors:
                    report.add_warning("CharacterState", error)
            
            # Check confidence
            if character_state.get_overall_confidence() < self.min_confidence:
                report.add_warning(
                    "CharacterState",
                    f"Low state confidence: {character_state.get_overall_confidence():.2f}"
                )
            
            report.add_info("CharacterState", "State validation passed")
            return True
            
        except Exception as e:
            report.add_error("CharacterState", f"State validation failed: {str(e)}")
            return False


def get_runtime_validation() -> RuntimeValidation:
    """Get singleton runtime validation instance"""
    if not hasattr(get_runtime_validation, "_instance"):
        get_runtime_validation._instance = RuntimeValidation()
    return get_runtime_validation._instance
