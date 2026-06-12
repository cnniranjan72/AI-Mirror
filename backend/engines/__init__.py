"""
Intelligence Engines for AIMirror platform
Core engines for knowledge processing, consolidation, and intelligence
"""

from .knowledge_consolidation import KnowledgeConsolidationEngine
from .persona_engine import PersonaEngineV2

__all__ = [
    "KnowledgeConsolidationEngine",
    "PersonaEngineV2"
]
