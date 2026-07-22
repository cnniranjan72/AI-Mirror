"""
Character RAG Package

Retrieval, Ranking, Fusion, Context Building, Citation Management.
Architecture V3 — FROZEN. No redesign.
No renaming. No simplification. No shortcuts.
"""
from .citation_manager import Citation, CitationGroup, CitationManager, get_citation_manager
from .retriever import RetrievedObject, RetrievalResult, Retriever, get_retriever
from .memory_ranker import RankedObject, MemoryRanker, get_memory_ranker
from .fusion import FusedFact, FusedEvidence, FusionEngine, get_fusion_engine
from .context_builder import CharacterContext, ContextBuilder, get_context_builder

__all__ = [
    "Citation",
    "CitationGroup",
    "CitationManager",
    "get_citation_manager",
    "RetrievedObject",
    "RetrievalResult",
    "Retriever",
    "get_retriever",
    "RankedObject",
    "MemoryRanker",
    "get_memory_ranker",
    "FusedFact",
    "FusedEvidence",
    "FusionEngine",
    "get_fusion_engine",
    "CharacterContext",
    "ContextBuilder",
    "get_context_builder",
]
