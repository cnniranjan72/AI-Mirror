"""
Identity Layer for AIMirror
Computational Identity Construction and Evolution
"""

from .identity_engine import (
    Identity,
    BehaviorProfile,
    InterestGraph,
    CreatorGraph,
    LearningStyle,
    AttentionProfile,
    ExplorationProfile,
    ConsistencyProfile,
    HabitProfile,
    MotivationSignals,
    IdentityEngine,
    get_identity_engine
)
from .self_model import (
    SelfModel,
    Belief,
    BeliefType,
    SelfModelEngine,
    get_self_model_engine
)
from .identity_evolution import (
    IdentitySnapshot,
    IdentityEvolution,
    IdentityEvolutionEngine,
    get_identity_evolution_engine
)

__all__ = [
    # Identity
    "Identity",
    "BehaviorProfile",
    "InterestGraph",
    "CreatorGraph",
    "LearningStyle",
    "AttentionProfile",
    "ExplorationProfile",
    "ConsistencyProfile",
    "HabitProfile",
    "MotivationSignals",
    "IdentityEngine",
    "get_identity_engine",
    # Self Model
    "SelfModel",
    "Belief",
    "BeliefType",
    "SelfModelEngine",
    "get_self_model_engine",
    # Evolution
    "IdentitySnapshot",
    "IdentityEvolution",
    "IdentityEvolutionEngine",
    "get_identity_evolution_engine"
]
