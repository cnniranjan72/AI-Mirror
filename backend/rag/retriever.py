"""
Retriever — Multi-Source Data Retrieval

Retrieves BehaviorObjects, Evidence, Identity, SelfModel, Goals, Reflections, Snapshots, Journal, Inferences.
Architecture V3 — FROZEN. No redesign.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set, Callable
from pydantic import BaseModel, Field

from backend.cognitive_planning.planner_models import RetrievalPlan, RetrievalDirective, RetrievalTarget

logger = logging.getLogger(__name__)


class RetrievedObject(BaseModel):
    object_id: str = Field(..., description="Unique identifier")
    source_type: str = Field(..., description="Source type matching RetrievalTarget values")
    content: Dict[str, Any] = Field(default_factory=dict, description="The retrieved content")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: Optional[datetime] = None
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    topic: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    objects: List[RetrievedObject] = Field(default_factory=list)
    total_retrieved: int = 0
    retrieval_time_ms: float = 0.0
    directives_fulfilled: int = 0
    directives_total: int = 0
    errors: List[str] = Field(default_factory=list)


class Retriever:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self._data_sources: Dict[str, Callable] = {}

    def register_source(self, target: RetrievalTarget, loader: Callable) -> None:
        self._data_sources[target.value] = loader

    def retrieve(self, plan: RetrievalPlan, context: Optional[Dict[str, Any]] = None) -> RetrievalResult:
        start = time.perf_counter()
        context = context or {}
        all_objects: List[RetrievedObject] = []
        errors: List[str] = []
        fulfilled = 0

        for directive in plan.directives:
            try:
                objects = self._execute_directive(directive, context)
                all_objects.extend(objects)
                if objects or not directive.required:
                    fulfilled += 1
            except Exception as e:
                err = f"Retrieval failed for {directive.target.value}: {e}"
                logger.warning(err)
                errors.append(err)
                if directive.required:
                    errors.append(f"Required directive {directive.target.value} failed")

        if plan.deduplicate:
            all_objects = self._deduplicate(all_objects)

        all_objects.sort(key=lambda o: o.relevance_score, reverse=True)
        if len(all_objects) > plan.total_max_results:
            all_objects = all_objects[:plan.total_max_results]

        elapsed = (time.perf_counter() - start) * 1000
        return RetrievalResult(
            objects=all_objects,
            total_retrieved=len(all_objects),
            retrieval_time_ms=elapsed,
            directives_fulfilled=fulfilled,
            directives_total=len(plan.directives),
            errors=errors,
        )

    def _execute_directive(
        self,
        directive: RetrievalDirective,
        context: Dict[str, Any],
    ) -> List[RetrievedObject]:
        loader = self._data_sources.get(directive.target.value)
        if loader is None:
            logger.debug(f"No loader registered for {directive.target.value}")
            return self._extract_from_context(directive, context)

        raw_data = loader(
            target=directive.target,
            max_results=directive.max_results,
            filter_topics=directive.filter_topics,
            filter_days=directive.filter_timerange_days,
        )
        return self._convert_to_retrieved(raw_data, directive.target.value)

    def _extract_from_context(
        self,
        directive: RetrievalDirective,
        context: Dict[str, Any],
    ) -> List[RetrievedObject]:
        objects: List[RetrievedObject] = []
        target_key = directive.target.value
        if target_key in context:
            data = context[target_key]
            if isinstance(data, list):
                objects.extend(self._convert_to_retrieved(data, target_key))
            elif isinstance(data, dict):
                objects.append(RetrievedObject(
                    object_id=data.get("id", data.get("object_id", target_key)),
                    source_type=target_key,
                    content=data,
                    confidence=data.get("confidence", 0.5),
                    timestamp=data.get("timestamp") or data.get("created_at"),
                ))
        return objects

    def _convert_to_retrieved(
        self,
        data: Any,
        source_type: str,
    ) -> List[RetrievedObject]:
        if isinstance(data, list):
            result = []
            for item in data:
                if isinstance(item, dict):
                    obj = RetrievedObject(
                        object_id=item.get("id") or item.get("object_id") or item.get("unique_id", ""),
                        source_type=source_type,
                        content=item,
                        confidence=float(item.get("confidence", item.get("confidence_score", 0.5))),
                        timestamp=item.get("timestamp") or item.get("created_at") or item.get("updated_at"),
                        topic=item.get("topic"),
                    )
                    result.append(obj)
                elif hasattr(item, "dict"):
                    d = item.dict()
                    obj = RetrievedObject(
                        object_id=getattr(item, "unique_id", None) or getattr(item, "id", None) or d.get("unique_id", d.get("id", "")),
                        source_type=source_type,
                        content=d,
                        confidence=float(getattr(item, "confidence", getattr(item, "confidence_score", 0.5))),
                        timestamp=getattr(item, "timestamp", getattr(item, "created_at", None)),
                        topic=getattr(item, "topic", None),
                    )
                    result.append(obj)
            return result
        if isinstance(data, dict):
            return [RetrievedObject(
                object_id=data.get("id") or data.get("object_id", ""),
                source_type=source_type,
                content=data,
                confidence=float(data.get("confidence", 0.5)),
                timestamp=data.get("timestamp") or data.get("created_at"),
            )]
        if hasattr(data, "dict"):
            d = data.dict()
            return [RetrievedObject(
                object_id=getattr(data, "unique_id", None) or getattr(data, "id", None) or d.get("unique_id", d.get("id", "")),
                source_type=source_type,
                content=d,
                confidence=float(getattr(data, "confidence", getattr(data, "confidence_score", 0.5))),
                timestamp=getattr(data, "timestamp", getattr(data, "created_at", None)),
                topic=getattr(data, "topic", None),
            )]
        return []

    def _deduplicate(self, objects: List[RetrievedObject]) -> List[RetrievedObject]:
        seen: Set[str] = set()
        result: List[RetrievedObject] = []
        for obj in objects:
            key = f"{obj.source_type}:{obj.object_id}"
            if key not in seen:
                seen.add(key)
                result.append(obj)
        return result


_retriever_instance: Optional[Retriever] = None


def get_retriever() -> Retriever:
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = Retriever()
    return _retriever_instance
