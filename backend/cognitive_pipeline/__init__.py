"""
Cognitive Pipeline — Integrated Query Processing
Architecture V3 — FROZEN. No redesign.
"""
from .pipeline import CognitivePipeline, CognitivePipelineResult, get_cognitive_pipeline
from .data_sources import register_data_sources

__all__ = [
    "CognitivePipeline",
    "CognitivePipelineResult",
    "get_cognitive_pipeline",
    "register_data_sources",
]
