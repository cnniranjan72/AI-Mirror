"""
Shared contracts and models for AIMirror platform
This package contains all strongly-typed models that serve as the language of the platform
"""

from .contracts import (
    BehaviorEvent,
    NormalizedContent,
    BehaviorCluster,
    Persona,
    Character,
    MemoryRecord,
    GoalState,
    Reflection
)

__all__ = [
    "BehaviorEvent",
    "NormalizedContent",
    "BehaviorCluster",
    "Persona",
    "Character",
    "MemoryRecord",
    "GoalState",
    "Reflection"
]
