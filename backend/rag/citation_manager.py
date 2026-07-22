"""
Citation Manager — Provenance Tracking

Every retrieved fact carries origin, confidence, timestamp, and supporting IDs.
Nothing becomes detached from provenance.
Architecture V3 — FROZEN. No redesign.
"""
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Set
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Citation(BaseModel):
    citation_id: str = Field(default_factory=lambda: f"cit_{uuid.uuid4().hex[:8]}")
    source_type: str = Field(..., description="behavior_object|evidence|identity|self_model|goal|reflection|inference|memory")
    source_id: str = Field(..., description="ID of the original source object")
    content_summary: str = Field(..., description="Summary of the cited content")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence of the cited source")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the source was created/recorded")
    supporting_evidence_ids: List[str] = Field(default_factory=list, description="Supporting evidence IDs")
    supporting_inference_ids: List[str] = Field(default_factory=list, description="Supporting inference IDs")
    supporting_behavior_ids: List[str] = Field(default_factory=list, description="Supporting behavior object IDs")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CitationGroup(BaseModel):
    group_id: str = Field(default_factory=lambda: f"citgrp_{uuid.uuid4().hex[:8]}")
    claim: str = Field(..., description="The claim being cited")
    citations: List[Citation] = Field(default_factory=list)
    aggregate_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    has_counter_evidence: bool = False
    best_supporting_citation: Optional[str] = None


class CitationManager:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self._citations: Dict[str, Citation] = {}
        self._groups: Dict[str, CitationGroup] = {}

    def create_citation(
        self,
        source_type: str,
        source_id: str,
        content_summary: str,
        confidence: float,
        timestamp: Optional[datetime] = None,
        supporting_evidence_ids: Optional[List[str]] = None,
        supporting_inference_ids: Optional[List[str]] = None,
        supporting_behavior_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Citation:
        citation = Citation(
            source_type=source_type,
            source_id=source_id,
            content_summary=content_summary,
            confidence=confidence,
            timestamp=timestamp or datetime.utcnow(),
            supporting_evidence_ids=supporting_evidence_ids or [],
            supporting_inference_ids=supporting_inference_ids or [],
            supporting_behavior_ids=supporting_behavior_ids or [],
            metadata=metadata or {},
        )
        self._citations[citation.citation_id] = citation
        return citation

    def get_citation(self, citation_id: str) -> Optional[Citation]:
        return self._citations.get(citation_id)

    def get_citations_for_source(self, source_id: str) -> List[Citation]:
        return [c for c in self._citations.values() if c.source_id == source_id]

    def create_group(self, claim: str, citations: List[Citation]) -> CitationGroup:
        if not citations:
            return CitationGroup(claim=claim)
        confidences = [c.confidence for c in citations]
        agg_conf = sum(confidences) / len(confidences)
        best = max(citations, key=lambda c: c.confidence)
        group = CitationGroup(
            claim=claim,
            citations=citations,
            aggregate_confidence=agg_conf,
            has_counter_evidence=False,
            best_supporting_citation=best.citation_id,
        )
        self._groups[group.group_id] = group
        return group

    def get_group(self, group_id: str) -> Optional[CitationGroup]:
        return self._groups.get(group_id)

    def merge_citations(self, citations: List[Citation]) -> Citation:
        if not citations:
            raise ValueError("Cannot merge empty citation list")
        if len(citations) == 1:
            return citations[0]
        avg_conf = sum(c.confidence for c in citations) / len(citations)
        all_evidence: Set[str] = set()
        all_inferences: Set[str] = set()
        all_behaviors: Set[str] = set()
        for c in citations:
            all_evidence.update(c.supporting_evidence_ids)
            all_inferences.update(c.supporting_inference_ids)
            all_behaviors.update(c.supporting_behavior_ids)
        merged = Citation(
            source_type="merged",
            source_id=",".join(c.source_id for c in citations),
            content_summary=citations[0].content_summary,
            confidence=avg_conf,
            timestamp=min(c.timestamp for c in citations),
            supporting_evidence_ids=list(all_evidence),
            supporting_inference_ids=list(all_inferences),
            supporting_behavior_ids=list(all_behaviors),
        )
        self._citations[merged.citation_id] = merged
        return merged

    def all_citations(self) -> List[Citation]:
        return list(self._citations.values())

    def clear(self) -> None:
        self._citations.clear()
        self._groups.clear()

    @property
    def citation_count(self) -> int:
        return len(self._citations)


_citation_manager_instance: Optional[CitationManager] = None


def get_citation_manager() -> CitationManager:
    global _citation_manager_instance
    if _citation_manager_instance is None:
        _citation_manager_instance = CitationManager()
    return _citation_manager_instance
