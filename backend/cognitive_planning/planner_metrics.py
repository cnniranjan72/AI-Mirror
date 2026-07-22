"""
Planner Metrics — Performance Tracking for Cognitive Planning

Tracks timing, counts, and error rates for all planner modules.
Architecture V3 — FROZEN. No redesign.
"""
import time
import logging
import threading
from collections import deque
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PlannerMetricsSnapshot(BaseModel):
    snapshot_timestamp: float = Field(default_factory=time.time)
    total_plans: int = 0
    avg_intent_time_ms: float = 0.0
    avg_retrieval_time_ms: float = 0.0
    avg_reasoning_time_ms: float = 0.0
    avg_response_time_ms: float = 0.0
    avg_orchestration_time_ms: float = 0.0
    max_orchestration_time_ms: float = 0.0
    intent_counts: Dict[str, int] = Field(default_factory=dict)
    reasoning_mode_counts: Dict[str, int] = Field(default_factory=dict)
    response_structure_counts: Dict[str, int] = Field(default_factory=dict)
    error_count: int = 0
    avg_confidence: float = 0.0


class PlannerMetrics:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self._lock = threading.RLock()
        self._reset()

    def _reset(self) -> None:
        self.total_plans = 0
        self._intent_times: deque = deque(maxlen=1000)
        self._retrieval_times: deque = deque(maxlen=1000)
        self._reasoning_times: deque = deque(maxlen=1000)
        self._response_times: deque = deque(maxlen=1000)
        self._orchestration_times: deque = deque(maxlen=1000)
        self._max_orchestration = 0.0
        self.intent_counts: Dict[str, int] = {}
        self.reasoning_mode_counts: Dict[str, int] = {}
        self.response_structure_counts: Dict[str, int] = {}
        self.error_count = 0
        self._confidences: deque = deque(maxlen=1000)

    def record_intent_time(self, ms: float) -> None:
        with self._lock:
            self._intent_times.append(ms)

    def record_retrieval_time(self, ms: float) -> None:
        with self._lock:
            self._retrieval_times.append(ms)

    def record_reasoning_time(self, ms: float) -> None:
        with self._lock:
            self._reasoning_times.append(ms)

    def record_response_time(self, ms: float) -> None:
        with self._lock:
            self._response_times.append(ms)

    def record_orchestration_time(self, ms: float) -> None:
        with self._lock:
            self._orchestration_times.append(ms)
            if ms > self._max_orchestration:
                self._max_orchestration = ms

    def record_intent_type(self, intent_type: str) -> None:
        with self._lock:
            self.intent_counts[intent_type] = self.intent_counts.get(intent_type, 0) + 1

    def record_reasoning_mode(self, mode: str) -> None:
        with self._lock:
            self.reasoning_mode_counts[mode] = self.reasoning_mode_counts.get(mode, 0) + 1

    def record_response_structure(self, structure: str) -> None:
        with self._lock:
            self.response_structure_counts[structure] = (
                self.response_structure_counts.get(structure, 0) + 1)

    def record_confidence(self, confidence: float) -> None:
        with self._lock:
            self._confidences.append(confidence)

    def record_error(self) -> None:
        with self._lock:
            self.error_count += 1

    def record_plan(self) -> None:
        with self._lock:
            self.total_plans += 1

    def get_snapshot(self) -> PlannerMetricsSnapshot:
        with self._lock:
            def _avg(d: deque) -> float:
                return sum(d) / len(d) if d else 0.0
            avg_confidence = sum(self._confidences) / len(self._confidences) if self._confidences else 0.0
            return PlannerMetricsSnapshot(
                total_plans=self.total_plans,
                avg_intent_time_ms=_avg(self._intent_times),
                avg_retrieval_time_ms=_avg(self._retrieval_times),
                avg_reasoning_time_ms=_avg(self._reasoning_times),
                avg_response_time_ms=_avg(self._response_times),
                avg_orchestration_time_ms=_avg(self._orchestration_times),
                max_orchestration_time_ms=self._max_orchestration,
                intent_counts=dict(self.intent_counts),
                reasoning_mode_counts=dict(self.reasoning_mode_counts),
                response_structure_counts=dict(self.response_structure_counts),
                error_count=self.error_count,
                avg_confidence=avg_confidence,
            )

    def reset_metrics(self) -> None:
        with self._lock:
            self._reset()


_metrics_instance: Optional[PlannerMetrics] = None


def get_planner_metrics() -> PlannerMetrics:
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = PlannerMetrics()
    return _metrics_instance
