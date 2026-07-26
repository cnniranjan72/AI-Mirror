"""
Runtime Builder
SINGLE entry point for building character runtime
NO duplicated loading logic
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import time

from backend.identity.identity_snapshot import IdentitySnapshot, get_snapshot_manager
from backend.identity.self_model import SelfModel
from backend.identity.identity_engine import Identity
from backend.reasoning import Inference
from backend.reasoning.reasoning_context import (
    ReasoningContext,
    MemoryReference,
    GoalReference,
    ReflectionReference
)

from .core import CharacterCore, get_character_core
from .character_state import CharacterState, get_character_state_builder
from .runtime_metrics import RuntimeMetrics, get_runtime_metrics


logger = logging.getLogger(__name__)


class RuntimeBuildResult(BaseModel):
    """Result of runtime build operation"""
    success: bool = Field(..., description="Whether build succeeded")
    character_core: Optional[CharacterCore] = Field(None, description="Character core")
    character_state: Optional[CharacterState] = Field(None, description="Character state")
    build_time_ms: float = Field(..., description="Build time in milliseconds")
    errors: List[str] = Field(default_factory=list, description="Build errors")
    warnings: List[str] = Field(default_factory=list, description="Build warnings")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Build metadata")


class RuntimeBuilder:
    """
    Runtime Builder - SINGLE Entry Point
    
    Responsibilities:
    - Load latest IdentitySnapshot
    - Load latest SelfModel
    - Load memories (behavior, reflection, goal)
    - Load ReasoningContext
    - Load recent Inferences
    - Assemble CharacterCore
    - Generate CharacterState
    
    This is the ONLY place that orchestrates runtime loading.
    No duplicated logic anywhere else.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Runtime Builder
        
        Args:
            config: Builder configuration
        """
        self.config = config or {}
        
        # Get dependencies
        self.snapshot_manager = get_snapshot_manager()
        self.core_factory = get_character_core()
        self.state_builder = get_character_state_builder()
        self.metrics = get_runtime_metrics()
        
        # Configuration
        self.max_inferences = self.config.get("max_inferences", 20)
        self.max_reflections = self.config.get("max_reflections", 5)
        self.max_retrievals = self.config.get("max_retrievals", 10)
        
        logger.info("RuntimeBuilder initialized")
    
    def build_runtime(
        self,
        user_id: str,
        identity: Optional[Identity] = None,
        identity_snapshot: Optional[IdentitySnapshot] = None,
        self_model: Optional[SelfModel] = None,
        current_query: Optional[str] = None,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        recent_inferences: Optional[List[Inference]] = None,
    ) -> RuntimeBuildResult:
        """
        Build complete character runtime
        
        This is the SINGLE entry point for runtime construction.
        
        Args:
            user_id: User identifier
            identity: Optional identity (will create snapshot if provided)
            identity_snapshot: Optional existing snapshot
            self_model: Optional self model
            current_query: Current user query
            conversation_id: Conversation ID
            session_id: Session ID
            request_id: Request ID
            
        Returns:
            RuntimeBuildResult
        """
        start_time = time.time()
        errors = []
        warnings = []
        
        try:
            logger.info(f"Building runtime for user {user_id}")
            
            # Step 1: Load or create IdentitySnapshot
            snapshot_start = time.time()
            if identity_snapshot is None:
                if identity is not None:
                    identity_snapshot = self._create_snapshot(identity)
                else:
                    identity_snapshot = self._load_latest_snapshot(user_id)
                    if identity_snapshot is None:
                        errors.append("No identity snapshot available")
                        return self._build_error_result(errors, warnings, start_time)
            
            snapshot_time = (time.time() - snapshot_start) * 1000
            self.metrics.record_snapshot_load(snapshot_time)
            
            # Step 2: Load SelfModel
            model_start = time.time()
            if self_model is None:
                self_model = self._load_self_model(user_id, identity_snapshot)
                if self_model is None:
                    warnings.append("No self model available - using empty model")
                    self_model = self._create_empty_self_model(user_id, identity_snapshot)
            
            model_time = (time.time() - model_start) * 1000
            self.metrics.record_model_load(model_time)
            
            # Step 3: Load Memories
            memory_start = time.time()
            memory_ids = self._load_memory_ids(user_id)
            memory_time = (time.time() - memory_start) * 1000
            self.metrics.record_memory_load(memory_time)
            
            # Step 4: Load ReasoningContext
            context_start = time.time()
            reasoning_context = self._load_reasoning_context(user_id)
            context_time = (time.time() - context_start) * 1000
            
            # Step 5: Load recent Inferences. Prefer a pre-loaded list (passed
            # by an async caller) — the fallback sync loader below calls
            # asyncio.get_running_loop() internally, which raises when
            # build_runtime is (as it usually is) executed inside a plain
            # threadpool worker with no event loop of its own, so it silently
            # returns [] in that case. Passing inferences in avoids that.
            inference_start = time.time()
            if recent_inferences is None:
                recent_inferences = self._load_recent_inferences(user_id)
            inference_time = (time.time() - inference_start) * 1000
            self.metrics.record_inference_count(len(recent_inferences))
            
            # Step 6: Load Goals
            goals_start = time.time()
            active_goals = self._load_active_goals(user_id)
            goals_time = (time.time() - goals_start) * 1000
            
            # Step 7: Load Reflections
            reflections_start = time.time()
            recent_reflections = self._load_recent_reflections(user_id)
            reflections_time = (time.time() - reflections_start) * 1000
            self.metrics.record_reflection_count(len(recent_reflections))
            
            # Step 8: Load Recent Retrievals (placeholder)
            recent_retrievals = []  # Would be populated from retrieval history
            
            # Step 9: Assemble CharacterCore
            core_start = time.time()
            character_core = self.core_factory.create_core(
                user_id=user_id,
                identity_snapshot=identity_snapshot,
                self_model=self_model,
                behavior_memory_ids=memory_ids.get("behavior", []),
                reflection_memory_ids=memory_ids.get("reflection", []),
                goal_memory_ids=memory_ids.get("goal", []),
                episodic_memory_ids=memory_ids.get("episodic", []),
                semantic_memory_ids=memory_ids.get("semantic", []),
                reasoning_context=reasoning_context,
                inference_history=recent_inferences
            )
            core_time = (time.time() - core_start) * 1000
            
            # Step 10: Generate CharacterState
            state_start = time.time()
            character_state = self.state_builder.build_state(
                user_id=user_id,
                identity_snapshot=identity_snapshot,
                self_model=self_model,
                behavior_memory_ids=memory_ids.get("behavior", []),
                reflection_memory_ids=memory_ids.get("reflection", []),
                goal_memory_ids=memory_ids.get("goal", []),
                active_goals=active_goals,
                current_query=current_query,
                conversation_id=conversation_id,
                recent_reflections=recent_reflections,
                recent_retrievals=recent_retrievals,
                active_inferences=recent_inferences,
                reasoning_context=reasoning_context,
                session_id=session_id,
                request_id=request_id
            )
            state_time = (time.time() - state_start) * 1000
            
            # Calculate total build time
            build_time = (time.time() - start_time) * 1000
            self.metrics.record_build_latency(build_time)
            
            # Build metadata
            metadata = {
                "snapshot_load_ms": snapshot_time,
                "model_load_ms": model_time,
                "memory_load_ms": memory_time,
                "context_load_ms": context_time,
                "inference_load_ms": inference_time,
                "goals_load_ms": goals_time,
                "reflections_load_ms": reflections_time,
                "core_build_ms": core_time,
                "state_build_ms": state_time,
                "total_build_ms": build_time,
                "snapshot_version": identity_snapshot.identity_version,
                "inference_count": len(recent_inferences),
                "reflection_count": len(recent_reflections),
                "goal_count": len(active_goals),
                "memory_counts": memory_ids
            }
            
            logger.info(f"Runtime built successfully in {build_time:.2f}ms")
            
            return RuntimeBuildResult(
                success=True,
                character_core=character_core,
                character_state=character_state,
                build_time_ms=build_time,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error building runtime: {str(e)}", exc_info=True)
            errors.append(f"Runtime build failed: {str(e)}")
            return self._build_error_result(errors, warnings, start_time)
    
    def _create_snapshot(self, identity: Identity) -> IdentitySnapshot:
        """Create snapshot from identity"""
        try:
            snapshot = self.snapshot_manager.create_snapshot(identity)
            logger.debug(f"Created snapshot {snapshot.snapshot_id}")
            return snapshot
        except Exception as e:
            logger.error(f"Error creating snapshot: {str(e)}", exc_info=True)
            raise
    
    def _load_latest_snapshot(self, user_id: str) -> Optional[IdentitySnapshot]:
        """Load latest snapshot for user"""
        try:
            snapshot = self.snapshot_manager.get_latest_snapshot_for_user(user_id)
            if snapshot:
                logger.debug(f"Loaded snapshot {snapshot.snapshot_id} for user {user_id}")
                self.metrics.record_snapshot_age(snapshot.get_age_seconds())
            return snapshot
        except Exception as e:
            logger.error(f"Error loading snapshot: {str(e)}", exc_info=True)
            return None
    
    def _load_self_model(
        self,
        user_id: str,
        identity_snapshot: IdentitySnapshot
    ) -> Optional[SelfModel]:
        """Load self model for user from database"""
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    from app.db.postgres import fetchrow
                    import json
                    import uuid
                    
                    row = asyncio.run_coroutine_threadsafe(
                        fetchrow(
                            "SELECT * FROM self_models WHERE user_id = $1 ORDER BY updated_at DESC LIMIT 1",
                            user_id
                        ),
                        loop
                    ).result(timeout=5)
                    
                    if row:
                        from backend.identity.self_model import SelfModel, Belief, UncertaintyMap
                        
                        beliefs_data = json.loads(row["beliefs"]) if isinstance(row["beliefs"], str) else (row["beliefs"] or [])
                        beliefs = [Belief(**b) for b in beliefs_data]
                        
                        uncertainty_data = json.loads(row["uncertainty_map"]) if isinstance(row["uncertainty_map"], str) else (row["uncertainty_map"] or {})
                        uncertainty_map = UncertaintyMap(**uncertainty_data)
                        
                        strong_beliefs = json.loads(row["strong_beliefs"]) if isinstance(row["strong_beliefs"], str) else (row["strong_beliefs"] or [])
                        uncertain_beliefs = json.loads(row["uncertain_beliefs"]) if isinstance(row["uncertain_beliefs"], str) else (row["uncertain_beliefs"] or [])
                        
                        model = SelfModel(
                            self_model_id=row["self_model_id"],
                            user_id=row["user_id"],
                            identity_snapshot_id=row["identity_snapshot_id"],
                            beliefs=beliefs,
                            strong_beliefs=strong_beliefs,
                            uncertain_beliefs=uncertain_beliefs,
                            uncertainty_map=uncertainty_map,
                            overall_confidence=float(row.get("overall_confidence", 0.5) or 0.5),
                            model_completeness=float(row.get("model_completeness", 0.0) or 0.0),
                            created_at=row["created_at"],
                            updated_at=row["updated_at"],
                            metadata=json.loads(row["metadata"]) if isinstance(row.get("metadata"), str) else (row.get("metadata") or {})
                        )
                        logger.debug(f"Loaded self model for user {user_id}")
                        return model
            except Exception as inner:
                logger.debug(f"Could not load self model from DB: {inner}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading self model: {str(e)}", exc_info=True)
            return None
    
    def _create_empty_self_model(
        self,
        user_id: str,
        identity_snapshot: IdentitySnapshot
    ) -> SelfModel:
        """Create empty self model"""
        from backend.identity.self_model import UncertaintyMap
        import uuid
        
        return SelfModel(
            self_model_id=f"selfmodel_{user_id}_empty",
            user_id=user_id,
            identity_snapshot_id=identity_snapshot.snapshot_id,
            uncertainty_map=UncertaintyMap(
                overall_uncertainty=0.5,
                last_updated=datetime.utcnow()
            ),
            overall_confidence=0.5,
            model_completeness=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def _load_memory_ids(self, user_id: str) -> Dict[str, List[str]]:
        """Load memory IDs for user from V3 memories table"""
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    from app.db.postgres import fetch
                    
                    rows = asyncio.run_coroutine_threadsafe(
                        fetch(
                            "SELECT memory_id, memory_type FROM memories WHERE user_id = $1 ORDER BY created_at DESC LIMIT 100",
                            user_id
                        ),
                        loop
                    ).result(timeout=5)
                    
                    result = {
                        "behavior": [],
                        "reflection": [],
                        "goal": [],
                        "episodic": [],
                        "semantic": []
                    }
                    for row in rows:
                        mtype = row["memory_type"]
                        mid = row["memory_id"]
                        if mtype in result:
                            result[mtype].append(mid)
                        else:
                            result.setdefault(mtype, []).append(mid)
                    
                    logger.debug(f"Loaded {sum(len(v) for v in result.values())} memory IDs for user {user_id}")
                    return result
            except Exception as inner:
                logger.debug(f"Could not load memory IDs from DB: {inner}")
            
            return {
                "behavior": [],
                "reflection": [],
                "goal": [],
                "episodic": [],
                "semantic": []
            }
        except Exception as e:
            logger.error(f"Error loading memory IDs: {str(e)}", exc_info=True)
            return {}
    
    def _load_reasoning_context(self, user_id: str) -> Optional[ReasoningContext]:
        """Load reasoning context for user from V3 tables"""
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    from app.db.postgres import fetch
                    import json
                    
                    # Load recent inferences as context bases
                    inference_rows = asyncio.run_coroutine_threadsafe(
                        fetch(
                            "SELECT inference_id, inference_text, inference_type, confidence, source, created_at "
                            "FROM inferences WHERE user_id = $1 ORDER BY created_at DESC LIMIT 5",
                            user_id
                        ),
                        loop
                    ).result(timeout=5)
                    
                    # Load recent reflections as context
                    reflection_rows = asyncio.run_coroutine_threadsafe(
                        fetch(
                            "SELECT reflection_id, reflection_text, reflection_type, significance, created_at "
                            "FROM reflections WHERE user_id = $1 ORDER BY created_at DESC LIMIT 3",
                            user_id
                        ),
                        loop
                    ).result(timeout=5)
                    
                    # Load recent goals as context
                    goal_rows = asyncio.run_coroutine_threadsafe(
                        fetch(
                            "SELECT goal_id, goal_description, goal_status, priority, created_at "
                            "FROM goals WHERE user_id = $1 AND goal_status = 'active' ORDER BY priority ASC, created_at DESC LIMIT 5",
                            user_id
                        ),
                        loop
                    ).result(timeout=5)
                    
                    # Build memory references
                    memory_refs = []
                    for row in inference_rows[:3]:
                        memory_refs.append(MemoryReference(
                            memory_id=row["inference_id"],
                            memory_type="inference",
                            content=row["inference_text"],
                            metadata={"inference_type": row["inference_type"], "confidence": float(row["confidence"] or 0.0) if row["confidence"] else 0.0},
                            created_at=row["created_at"]
                        ))
                    
                    goal_refs = []
                    for row in goal_rows:
                        goal_refs.append(GoalReference(
                            goal_id=row["goal_id"],
                            description=row["goal_description"],
                            status=row["goal_status"],
                            priority=int(row["priority"]) if row["priority"] else 0,
                            created_at=row["created_at"]
                        ))
                    
                    reflection_refs = []
                    for row in reflection_rows:
                        reflection_refs.append(ReflectionReference(
                            reflection_id=row["reflection_id"],
                            content=row["reflection_text"],
                            reflection_type=row["reflection_type"],
                            significance=float(row["significance"] or 0.0) if row["significance"] else 0.0,
                            created_at=row["created_at"]
                        ))
                    
                    context = ReasoningContext(
                        context_id=f"ctx_{user_id}",
                        user_id=user_id,
                        memories=memory_refs,
                        active_goals=goal_refs,
                        recent_reflections=reflection_refs,
                        context_metadata={"source": "v3_database"}
                    )
                    logger.debug(f"Loaded reasoning context for user {user_id}")
                    return context
            except Exception as inner:
                logger.debug(f"Could not load reasoning context from DB: {inner}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading reasoning context: {str(e)}", exc_info=True)
            return None
    
    def _load_recent_inferences(self, user_id: str) -> List[Inference]:
        """Load recent inferences for user from V3 inferences table"""
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    from app.db.postgres import fetch
                    import json
                    
                    rows = asyncio.run_coroutine_threadsafe(
                        fetch(
                            "SELECT * FROM inferences WHERE user_id = $1 "
                            "ORDER BY created_at DESC LIMIT $2",
                            user_id, self.max_inferences
                        ),
                        loop
                    ).result(timeout=5)

                    def _j(v, default):
                        if isinstance(v, str):
                            try:
                                return json.loads(v)
                            except Exception:
                                return default
                        return v if v is not None else default

                    inferences = []
                    for row in rows:
                        inferences.append(Inference(
                            inference_id=row["inference_id"],
                            inference_type=row["inference_type"],
                            label=row["label"],
                            description=row["description"],
                            confidence=float(row["confidence"] or 0.0),
                            importance=float(row["importance"] or 0.0),
                            strength=float(row["strength"] or 0.0),
                            supporting_evidence=_j(row.get("supporting_evidence"), []),
                            evidence_summary=row.get("evidence_summary") or "",
                            affected_topics=_j(row.get("affected_topics"), []),
                            affected_creators=_j(row.get("affected_creators"), []),
                            affected_behaviors=_j(row.get("affected_behaviors"), []),
                            recommendation_seed=row.get("recommendation_seed"),
                            suggested_actions=_j(row.get("suggested_actions"), []),
                            inferred_at=row.get("inferred_at") or row["created_at"],
                            valid_from=row.get("valid_from") or row["created_at"],
                            valid_until=row.get("valid_until"),
                            rule_name=row.get("rule_name"),
                            context_id=row.get("context_id"),
                            metadata=_j(row.get("metadata"), {}),
                        ))
                    
                    logger.debug(f"Loaded {len(inferences)} inferences for user {user_id}")
                    return inferences
            except Exception as inner:
                logger.debug(f"Could not load inferences from DB: {inner}")
            
            return []
            
        except Exception as e:
            logger.error(f"Error loading inferences: {str(e)}", exc_info=True)
            return []
    
    def _load_active_goals(self, user_id: str) -> List[GoalReference]:
        """Load active goals for user from V3 goals table"""
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    from app.db.postgres import fetch
                    
                    rows = asyncio.run_coroutine_threadsafe(
                        fetch(
                            "SELECT goal_id, goal_description, goal_status, priority, "
                            "goal_type, milestones, progress, metadata, created_at "
                            "FROM goals WHERE user_id = $1 AND goal_status = 'active' "
                            "ORDER BY priority ASC, created_at DESC LIMIT 10",
                            user_id
                        ),
                        loop
                    ).result(timeout=5)
                    
                    import json
                    goals = []
                    for row in rows:
                        goals.append(GoalReference(
                            goal_id=row["goal_id"],
                            description=row["goal_description"],
                            status=row["goal_status"],
                            priority=int(row["priority"]) if row["priority"] else 0,
                            goal_type=row.get("goal_type", "general"),
                            milestones=json.loads(row["milestones"]) if isinstance(row.get("milestones"), str) else (row.get("milestones") or []),
                            progress=float(row["progress"] or 0.0) if row.get("progress") else 0.0,
                            metadata=json.loads(row["metadata"]) if isinstance(row.get("metadata"), str) else (row.get("metadata") or {}),
                            created_at=row["created_at"]
                        ))
                    
                    logger.debug(f"Loaded {len(goals)} active goals for user {user_id}")
                    return goals
            except Exception as inner:
                logger.debug(f"Could not load goals from DB: {inner}")
            
            return []
            
        except Exception as e:
            logger.error(f"Error loading goals: {str(e)}", exc_info=True)
            return []
    
    def _load_recent_reflections(self, user_id: str) -> List[ReflectionReference]:
        """Load recent reflections for user from V3 reflections table"""
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    from app.db.postgres import fetch
                    import json
                    
                    rows = asyncio.run_coroutine_threadsafe(
                        fetch(
                            "SELECT reflection_id, reflection_text, reflection_type, significance, "
                            "source_evidence_ids, source_inference_ids, metadata, created_at "
                            "FROM reflections WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
                            user_id, self.max_reflections
                        ),
                        loop
                    ).result(timeout=5)
                    
                    reflections = []
                    for row in rows:
                        reflections.append(ReflectionReference(
                            reflection_id=row["reflection_id"],
                            content=row["reflection_text"],
                            reflection_type=row["reflection_type"],
                            significance=float(row["significance"] or 0.0) if row["significance"] else 0.0,
                            source_evidence_ids=json.loads(row["source_evidence_ids"]) if isinstance(row["source_evidence_ids"], str) else (row["source_evidence_ids"] or []),
                            source_inference_ids=json.loads(row["source_inference_ids"]) if isinstance(row["source_inference_ids"], str) else (row["source_inference_ids"] or []),
                            metadata=json.loads(row["metadata"]) if isinstance(row.get("metadata"), str) else (row.get("metadata") or {}),
                            created_at=row["created_at"]
                        ))
                    
                    logger.debug(f"Loaded {len(reflections)} reflections for user {user_id}")
                    return reflections
            except Exception as inner:
                logger.debug(f"Could not load reflections from DB: {inner}")
            
            return []
            
        except Exception as e:
            logger.error(f"Error loading reflections: {str(e)}", exc_info=True)
            return []
    
    def _build_error_result(
        self,
        errors: List[str],
        warnings: List[str],
        start_time: float
    ) -> RuntimeBuildResult:
        """Build error result"""
        build_time = (time.time() - start_time) * 1000
        
        return RuntimeBuildResult(
            success=False,
            build_time_ms=build_time,
            errors=errors,
            warnings=warnings,
            metadata={"error": True}
        )


def get_runtime_builder() -> RuntimeBuilder:
    """Get singleton runtime builder instance"""
    if not hasattr(get_runtime_builder, "_instance"):
        get_runtime_builder._instance = RuntimeBuilder()
    return get_runtime_builder._instance
