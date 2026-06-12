"""
Character Runtime Layer
Computational representation and runtime orchestration
"""

from .core import (
    CharacterCore,
    get_character_core
)
from .character_state import (
    CharacterState,
    PersistentState,
    EphemeralState
)
from .runtime_builder import (
    RuntimeBuilder,
    get_runtime_builder
)
from .virtual_character import (
    VirtualCharacter,
    get_virtual_character
)
from .runtime_cache import (
    RuntimeCache,
    get_runtime_cache
)
from .runtime_validation import (
    RuntimeValidation,
    ValidationReport,
    get_runtime_validation
)
from .runtime_metrics import (
    RuntimeMetrics,
    MetricsSnapshot,
    get_runtime_metrics
)

__all__ = [
    # Core
    "CharacterCore",
    "get_character_core",
    # State
    "CharacterState",
    "PersistentState",
    "EphemeralState",
    # Builder
    "RuntimeBuilder",
    "get_runtime_builder",
    # Character
    "VirtualCharacter",
    "get_virtual_character",
    # Cache
    "RuntimeCache",
    "get_runtime_cache",
    # Validation
    "RuntimeValidation",
    "ValidationReport",
    "get_runtime_validation",
    # Metrics
    "RuntimeMetrics",
    "MetricsSnapshot",
    "get_runtime_metrics"
]
