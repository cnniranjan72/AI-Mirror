"""
Memory Ranker — Hybrid Ranking

Ranks retrieved objects using importance, recency, confidence, behavior stability,
identity relevance, goal relevance, semantic similarity, temporal relevance.
No vector-only ranking. Hybrid ranking.
Architecture V3 — FROZEN. No redesign.
"""
import logging
import math
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .retriever import RetrievedObject

logger = logging.getLogger(__name__)


class RankedObject(BaseModel):
    retrieved: RetrievedObject
    rank_score: float = Field(..., ge=0.0, le=1.0)
    sub_scores: Dict[str, float] = Field(default_factory=dict)

    def __lt__(self, other: "RankedObject") -> bool:
        return self.rank_score < other.rank_score


class MemoryRanker:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.recency_weight = self.config.get("recency_weight", 0.15)
        self.confidence_weight = self.config.get("confidence_weight", 0.20)
        self.stability_weight = self.config.get("stability_weight", 0.10)
        self.identity_relevance_weight = self.config.get("identity_relevance_weight", 0.20)
        self.goal_relevance_weight = self.config.get("goal_relevance_weight", 0.15)
        self.semantic_weight = self.config.get("semantic_weight", 0.10)
        self.temporal_weight = self.config.get("temporal_weight", 0.10)
        self.recency_decay_days = self.config.get("recency_decay_days", 30.0)

    def rank(
        self,
        objects: List[RetrievedObject],
        identity_topics: Optional[List[str]] = None,
        goal_ids: Optional[List[str]] = None,
        query_embedding: Optional[List[float]] = None,
        current_time: Optional[datetime] = None,
    ) -> List[RankedObject]:
        if not objects:
            return []

        now = current_time or datetime.utcnow()
        identity_topics = identity_topics or []
        goal_ids = goal_ids or []

        ranked: List[RankedObject] = []
        for obj in objects:
            sub_scores = self._compute_sub_scores(obj, identity_topics, goal_ids, query_embedding, now)
            total = self._aggregate(sub_scores)
            ranked.append(RankedObject(retrieved=obj, rank_score=total, sub_scores=sub_scores))

        ranked.sort(reverse=True)
        return ranked

    def _compute_sub_scores(
        self,
        obj: RetrievedObject,
        identity_topics: List[str],
        goal_ids: List[str],
        query_embedding: Optional[List[float]],
        now: datetime,
    ) -> Dict[str, float]:
        content = obj.content

        recency = self._score_recency(obj.timestamp, now)
        confidence = obj.confidence
        stability = self._score_stability(content)
        identity_relevance = self._score_identity_relevance(content, identity_topics)
        goal_relevance = self._score_goal_relevance(content, goal_ids)
        semantic = self._score_semantic(content, query_embedding)
        temporal = self._score_temporal_pattern(content)

        return {
            "recency": recency,
            "confidence": confidence,
            "stability": stability,
            "identity_relevance": identity_relevance,
            "goal_relevance": goal_relevance,
            "semantic_similarity": semantic,
            "temporal": temporal,
        }

    def _aggregate(self, scores: Dict[str, float]) -> float:
        weights = {
            "recency": self.recency_weight,
            "confidence": self.confidence_weight,
            "stability": self.stability_weight,
            "identity_relevance": self.identity_relevance_weight,
            "goal_relevance": self.goal_relevance_weight,
            "semantic_similarity": self.semantic_weight,
            "temporal": self.temporal_weight,
        }
        total = 0.0
        for key, weight in weights.items():
            total += scores.get(key, 0.0) * weight
        return min(1.0, max(0.0, total))

    def _score_recency(self, timestamp: Optional[datetime], now: datetime) -> float:
        if timestamp is None:
            return 0.3
        if timestamp.tzinfo is not None:
            timestamp = timestamp.replace(tzinfo=None)
        days_ago = (now - timestamp).total_seconds() / 86400.0
        if days_ago < 0:
            return 1.0
        return math.exp(-days_ago / self.recency_decay_days)

    def _score_stability(self, content: Dict[str, Any]) -> float:
        stability = content.get("stability_score") or content.get("behavior_stability")
        if stability is not None:
            return float(stability)
        consistency = content.get("consistency_score") or content.get("overall_consistency")
        if consistency is not None:
            return float(consistency)
        return 0.5

    def _score_identity_relevance(self, content: Dict[str, Any], identity_topics: List[str]) -> float:
        if not identity_topics:
            return 0.5
        content_topics = []
        for key in ("topic", "subtopics", "dominant_topics", "keywords"):
            val = content.get(key)
            if isinstance(val, str):
                content_topics.append(val.lower())
            elif isinstance(val, list):
                content_topics.extend(str(v).lower() for v in val)
        if not content_topics:
            return 0.3
        matches = sum(1 for t in content_topics if any(it.lower() in t for it in identity_topics))
        return min(1.0, matches / max(1, len(identity_topics)))

    def _score_goal_relevance(self, content: Dict[str, Any], goal_ids: List[str]) -> float:
        if not goal_ids:
            return 0.5
        content_str = str(content).lower()
        return 1.0 if any(gid.lower() in content_str for gid in goal_ids) else 0.3

    def _score_semantic(self, content: Dict[str, Any], query_embedding: Optional[List[float]]) -> float:
        if query_embedding is None:
            return 0.5
        content_emb = content.get("representative_embedding")
        if not content_emb or len(content_emb) != len(query_embedding):
            return 0.5
        dot = sum(a * b for a, b in zip(content_emb, query_embedding))
        norm_a = math.sqrt(sum(a * a for a in content_emb)) or 1.0
        norm_b = math.sqrt(sum(b * b for b in query_embedding)) or 1.0
        return max(0.0, min(1.0, dot / (norm_a * norm_b)))

    def _score_temporal_pattern(self, content: Dict[str, Any]) -> float:
        recency_score = content.get("recency_score")
        if recency_score is not None:
            return float(recency_score)
        consistency = content.get("consistency_score") or content.get("temporal_consistency")
        if consistency is not None:
            return float(consistency)
        return 0.5


_memory_ranker_instance: Optional[MemoryRanker] = None


def get_memory_ranker() -> MemoryRanker:
    global _memory_ranker_instance
    if _memory_ranker_instance is None:
        _memory_ranker_instance = MemoryRanker()
    return _memory_ranker_instance
