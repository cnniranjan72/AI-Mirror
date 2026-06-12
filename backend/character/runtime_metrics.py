"""
Runtime Metrics
Tracks runtime performance and statistics
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from collections import deque
import threading
import logging


logger = logging.getLogger(__name__)


class MetricsSnapshot(BaseModel):
    """Snapshot of runtime metrics"""
    snapshot_timestamp: datetime = Field(..., description="Snapshot timestamp")
    
    # Build metrics
    total_builds: int = Field(default=0, description="Total runtime builds")
    successful_builds: int = Field(default=0, description="Successful builds")
    failed_builds: int = Field(default=0, description="Failed builds")
    avg_build_latency_ms: float = Field(default=0.0, description="Average build latency")
    max_build_latency_ms: float = Field(default=0.0, description="Max build latency")
    min_build_latency_ms: float = Field(default=0.0, description="Min build latency")
    
    # Snapshot metrics
    avg_snapshot_age_seconds: float = Field(default=0.0, description="Average snapshot age")
    avg_snapshot_load_ms: float = Field(default=0.0, description="Average snapshot load time")
    
    # Memory metrics
    avg_memory_load_ms: float = Field(default=0.0, description="Average memory load time")
    avg_behavior_count: float = Field(default=0.0, description="Average behavior count")
    avg_reflection_count: float = Field(default=0.0, description="Average reflection count")
    avg_inference_count: float = Field(default=0.0, description="Average inference count")
    
    # Cache metrics
    cache_hit_rate: float = Field(default=0.0, description="Cache hit rate")
    cache_size: int = Field(default=0, description="Current cache size")
    
    # Validation metrics
    validation_success_rate: float = Field(default=0.0, description="Validation success rate")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RuntimeMetrics:
    """
    Runtime Metrics
    
    Tracks:
    - Runtime build latency
    - Snapshot age
    - Memory load latency
    - Inference count
    - Behavior count
    - Reflection count
    - Cache hit rate
    - Validation success
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Runtime Metrics
        
        Args:
            config: Metrics configuration
        """
        self.config = config or {}
        
        # Configuration
        self.max_history_size = self.config.get("max_history_size", 1000)
        
        # Metrics storage
        self._build_latencies = deque(maxlen=self.max_history_size)
        self._snapshot_ages = deque(maxlen=self.max_history_size)
        self._snapshot_load_times = deque(maxlen=self.max_history_size)
        self._memory_load_times = deque(maxlen=self.max_history_size)
        self._model_load_times = deque(maxlen=self.max_history_size)
        self._behavior_counts = deque(maxlen=self.max_history_size)
        self._reflection_counts = deque(maxlen=self.max_history_size)
        self._inference_counts = deque(maxlen=self.max_history_size)
        
        # Counters
        self._total_builds = 0
        self._successful_builds = 0
        self._failed_builds = 0
        self._total_validations = 0
        self._successful_validations = 0
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("RuntimeMetrics initialized")
    
    def record_build_latency(self, latency_ms: float):
        """Record build latency"""
        with self._lock:
            self._build_latencies.append(latency_ms)
            self._total_builds += 1
    
    def record_build_success(self):
        """Record successful build"""
        with self._lock:
            self._successful_builds += 1
    
    def record_build_failure(self):
        """Record failed build"""
        with self._lock:
            self._failed_builds += 1
    
    def record_snapshot_age(self, age_seconds: float):
        """Record snapshot age"""
        with self._lock:
            self._snapshot_ages.append(age_seconds)
    
    def record_snapshot_load(self, load_time_ms: float):
        """Record snapshot load time"""
        with self._lock:
            self._snapshot_load_times.append(load_time_ms)
    
    def record_memory_load(self, load_time_ms: float):
        """Record memory load time"""
        with self._lock:
            self._memory_load_times.append(load_time_ms)
    
    def record_model_load(self, load_time_ms: float):
        """Record model load time"""
        with self._lock:
            self._model_load_times.append(load_time_ms)
    
    def record_behavior_count(self, count: int):
        """Record behavior count"""
        with self._lock:
            self._behavior_counts.append(count)
    
    def record_reflection_count(self, count: int):
        """Record reflection count"""
        with self._lock:
            self._reflection_counts.append(count)
    
    def record_inference_count(self, count: int):
        """Record inference count"""
        with self._lock:
            self._inference_counts.append(count)
    
    def record_validation(self, success: bool):
        """Record validation result"""
        with self._lock:
            self._total_validations += 1
            if success:
                self._successful_validations += 1
    
    def get_snapshot(self) -> MetricsSnapshot:
        """
        Get metrics snapshot
        
        Returns:
            MetricsSnapshot
        """
        try:
            with self._lock:
                # Calculate averages
                avg_build_latency = self._calculate_avg(self._build_latencies)
                max_build_latency = max(self._build_latencies) if self._build_latencies else 0.0
                min_build_latency = min(self._build_latencies) if self._build_latencies else 0.0
                
                avg_snapshot_age = self._calculate_avg(self._snapshot_ages)
                avg_snapshot_load = self._calculate_avg(self._snapshot_load_times)
                avg_memory_load = self._calculate_avg(self._memory_load_times)
                
                avg_behavior_count = self._calculate_avg(self._behavior_counts)
                avg_reflection_count = self._calculate_avg(self._reflection_counts)
                avg_inference_count = self._calculate_avg(self._inference_counts)
                
                # Calculate rates
                validation_success_rate = (
                    self._successful_validations / self._total_validations
                    if self._total_validations > 0 else 0.0
                )
                
                snapshot = MetricsSnapshot(
                    snapshot_timestamp=datetime.utcnow(),
                    total_builds=self._total_builds,
                    successful_builds=self._successful_builds,
                    failed_builds=self._failed_builds,
                    avg_build_latency_ms=avg_build_latency,
                    max_build_latency_ms=max_build_latency,
                    min_build_latency_ms=min_build_latency,
                    avg_snapshot_age_seconds=avg_snapshot_age,
                    avg_snapshot_load_ms=avg_snapshot_load,
                    avg_memory_load_ms=avg_memory_load,
                    avg_behavior_count=avg_behavior_count,
                    avg_reflection_count=avg_reflection_count,
                    avg_inference_count=avg_inference_count,
                    cache_hit_rate=0.0,  # Would be populated from cache
                    cache_size=0,  # Would be populated from cache
                    validation_success_rate=validation_success_rate,
                    metadata={
                        "history_size": len(self._build_latencies),
                        "max_history_size": self.max_history_size
                    }
                )
                
                return snapshot
                
        except Exception as e:
            logger.error(f"Error getting metrics snapshot: {str(e)}", exc_info=True)
            return MetricsSnapshot(snapshot_timestamp=datetime.utcnow())
    
    def get_metrics_dict(self) -> Dict[str, Any]:
        """
        Get metrics as dictionary
        
        Returns:
            Metrics dictionary
        """
        snapshot = self.get_snapshot()
        return snapshot.dict()
    
    def reset_metrics(self):
        """Reset all metrics"""
        with self._lock:
            self._build_latencies.clear()
            self._snapshot_ages.clear()
            self._snapshot_load_times.clear()
            self._memory_load_times.clear()
            self._model_load_times.clear()
            self._behavior_counts.clear()
            self._reflection_counts.clear()
            self._inference_counts.clear()
            
            self._total_builds = 0
            self._successful_builds = 0
            self._failed_builds = 0
            self._total_validations = 0
            self._successful_validations = 0
            
            logger.info("Metrics reset")
    
    def _calculate_avg(self, values: deque) -> float:
        """Calculate average of values"""
        if not values:
            return 0.0
        return sum(values) / len(values)


def get_runtime_metrics() -> RuntimeMetrics:
    """Get singleton runtime metrics instance"""
    if not hasattr(get_runtime_metrics, "_instance"):
        get_runtime_metrics._instance = RuntimeMetrics()
    return get_runtime_metrics._instance
