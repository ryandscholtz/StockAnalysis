"""
CloudWatch Custom Metrics Service
Implements comprehensive metrics emission for monitoring and observability
"""
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging
import os
import json

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from app.core.logging import LoggerMixin


class MetricUnit(str, Enum):
    """CloudWatch metric units"""
    SECONDS = "Seconds"
    MICROSECONDS = "Microseconds"
    MILLISECONDS = "Milliseconds"
    BYTES = "Bytes"
    KILOBYTES = "Kilobytes"
    MEGABYTES = "Megabytes"
    GIGABYTES = "Gigabytes"
    TERABYTES = "Terabytes"
    BITS = "Bits"
    KILOBITS = "Kilobits"
    MEGABITS = "Megabits"
    GIGABITS = "Gigabits"
    TERABITS = "Terabits"
    PERCENT = "Percent"
    COUNT = "Count"
    COUNT_PER_SECOND = "Count/Second"
    NONE = "None"


class MetricType(str, Enum):
    """Types of metrics for categorization"""
    API_PERFORMANCE = "api_performance"
    BUSINESS = "business"
    SYSTEM = "system"
    ERROR = "error"
    CACHE = "cache"
    DATABASE = "database"
    AI_ML = "ai_ml"


@dataclass
class MetricData:
    """Represents a single metric data point"""
    name: str
    value: Union[int, float]
    unit: MetricUnit
    timestamp: Optional[datetime] = None
    dimensions: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.SYSTEM
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class MetricBatch:
    """Batch of metrics for efficient CloudWatch submission"""
    namespace: str
    metrics: List[MetricData] = field(default_factory=list)
    
    def add_metric(self, metric: MetricData):
        """Add a metric to the batch"""
        self.metrics.append(metric)
    
    def size(self) -> int:
        """Get the number of metrics in the batch"""
        return len(self.metrics)
    
    def clear(self):
        """Clear all metrics from the batch"""
        self.metrics.clear()


class MetricsCollector(LoggerMixin):
    """Collects and aggregates metrics before emission"""
    
    def __init__(self):
        self.metrics_buffer: Dict[str, List[MetricData]] = defaultdict(list)
        self.response_times: deque = deque(maxlen=1000)  # Keep last 1000 response times
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'total_requests': 0
        }
        self.analysis_stats = {
            'completed': 0,
            'failed': 0,
            'in_progress': 0
        }
        self._lock = asyncio.Lock()
    
    async def record_api_response_time(self, endpoint: str, method: str, duration_ms: float, status_code: int):
        """Record API response time metrics"""
        async with self._lock:
            self.response_times.append(duration_ms)
            
            metric = MetricData(
                name="APIResponseTime",
                value=duration_ms,
                unit=MetricUnit.MILLISECONDS,
                dimensions={
                    "Endpoint": endpoint,
                    "Method": method,
                    "StatusCode": str(status_code)
                },
                metric_type=MetricType.API_PERFORMANCE
            )
            self.metrics_buffer["api_performance"].append(metric)
    
    async def record_error(self, error_category: str, endpoint: str = None):
        """Record error occurrence"""
        async with self._lock:
            self.error_counts[error_category] += 1
            
            dimensions = {"ErrorCategory": error_category}
            if endpoint:
                dimensions["Endpoint"] = endpoint
            
            metric = MetricData(
                name="ErrorCount",
                value=1,
                unit=MetricUnit.COUNT,
                dimensions=dimensions,
                metric_type=MetricType.ERROR
            )
            self.metrics_buffer["errors"].append(metric)
    
    async def record_cache_hit(self, cache_type: str = "redis"):
        """Record cache hit"""
        async with self._lock:
            self.cache_stats['hits'] += 1
            self.cache_stats['total_requests'] += 1
            
            metric = MetricData(
                name="CacheHit",
                value=1,
                unit=MetricUnit.COUNT,
                dimensions={"CacheType": cache_type},
                metric_type=MetricType.CACHE
            )
            self.metrics_buffer["cache"].append(metric)
    
    async def record_cache_miss(self, cache_type: str = "redis"):
        """Record cache miss"""
        async with self._lock:
            self.cache_stats['misses'] += 1
            self.cache_stats['total_requests'] += 1
            
            metric = MetricData(
                name="CacheMiss",
                value=1,
                unit=MetricUnit.COUNT,
                dimensions={"CacheType": cache_type},
                metric_type=MetricType.CACHE
            )
            self.metrics_buffer["cache"].append(metric)
    
    async def record_analysis_completion(self, ticker: str, analysis_type: str, duration_seconds: float, success: bool):
        """Record stock analysis completion"""
        async with self._lock:
            if success:
                self.analysis_stats['completed'] += 1
                metric_name = "AnalysisCompleted"
            else:
                self.analysis_stats['failed'] += 1
                metric_name = "AnalysisFailed"
            
            # Record completion/failure count
            metric = MetricData(
                name=metric_name,
                value=1,
                unit=MetricUnit.COUNT,
                dimensions={
                    "Ticker": ticker,
                    "AnalysisType": analysis_type
                },
                metric_type=MetricType.BUSINESS
            )
            self.metrics_buffer["business"].append(metric)
            
            # Record analysis duration if successful
            if success:
                duration_metric = MetricData(
                    name="AnalysisDuration",
                    value=duration_seconds,
                    unit=MetricUnit.SECONDS,
                    dimensions={
                        "Ticker": ticker,
                        "AnalysisType": analysis_type
                    },
                    metric_type=MetricType.BUSINESS
                )
                self.metrics_buffer["business"].append(duration_metric)
    
    async def get_cache_hit_ratio(self) -> float:
        """Calculate current cache hit ratio"""
        async with self._lock:
            total = self.cache_stats['total_requests']
            if total == 0:
                return 0.0
            return self.cache_stats['hits'] / total
    
    async def get_average_response_time(self) -> float:
        """Calculate average response time from recent requests"""
        async with self._lock:
            if not self.response_times:
                return 0.0
            return sum(self.response_times) / len(self.response_times)
    
    async def get_error_rate(self, time_window_minutes: int = 5) -> float:
        """Calculate error rate over time window"""
        # This is a simplified implementation
        # In production, you'd want to track errors with timestamps
        async with self._lock:
            total_errors = sum(self.error_counts.values())
            # Simplified calculation - in reality you'd need time-based tracking
            return total_errors / max(1, len(self.response_times))
    
    async def get_buffered_metrics(self, metric_type: str = None) -> List[MetricData]:
        """Get buffered metrics, optionally filtered by type"""
        async with self._lock:
            if metric_type:
                return self.metrics_buffer.get(metric_type, []).copy()
            
            all_metrics = []
            for metrics_list in self.metrics_buffer.values():
                all_metrics.extend(metrics_list)
            return all_metrics
    
    async def clear_buffer(self, metric_type: str = None):
        """Clear metrics buffer"""
        async with self._lock:
            if metric_type:
                self.metrics_buffer[metric_type].clear()
            else:
                self.metrics_buffer.clear()


class CloudWatchMetricsService(LoggerMixin):
    """Service for emitting custom metrics to CloudWatch"""
    
    def __init__(self, namespace: str = "StockAnalysis/API"):
        self.namespace = namespace
        self.enabled = BOTO3_AVAILABLE and os.getenv("CLOUDWATCH_METRICS_ENABLED", "true").lower() == "true"
        self.collector = MetricsCollector()
        self.batch_size = int(os.getenv("METRICS_BATCH_SIZE", "20"))  # CloudWatch limit is 20
        self.flush_interval = int(os.getenv("METRICS_FLUSH_INTERVAL", "60"))  # seconds
        
        if self.enabled and BOTO3_AVAILABLE:
            try:
                self.cloudwatch = boto3.client('cloudwatch')
                self.log_info("CloudWatch metrics service initialized")
            except (NoCredentialsError, Exception) as e:
                self.log_warning(f"Failed to initialize CloudWatch client: {e}")
                self.enabled = False
        else:
            self.cloudwatch = None
            if not BOTO3_AVAILABLE:
                self.log_warning("boto3 not available, CloudWatch metrics disabled")
            else:
                self.log_info("CloudWatch metrics disabled by configuration")
    
    async def emit_metric(self, metric: MetricData) -> bool:
        """Emit a single metric to CloudWatch"""
        if not self.enabled:
            self.log_debug(f"Metrics disabled, skipping metric: {metric.name}")
            return False
        
        try:
            metric_data = {
                'MetricName': metric.name,
                'Value': metric.value,
                'Unit': metric.unit.value,
                'Timestamp': metric.timestamp
            }
            
            if metric.dimensions:
                metric_data['Dimensions'] = [
                    {'Name': key, 'Value': value}
                    for key, value in metric.dimensions.items()
                ]
            
            response = self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
            
            self.log_debug(f"Emitted metric: {metric.name} = {metric.value}")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to emit metric {metric.name}: {e}")
            return False
    
    async def emit_metrics_batch(self, metrics: List[MetricData]) -> int:
        """Emit a batch of metrics to CloudWatch"""
        if not self.enabled or not metrics:
            return 0
        
        success_count = 0
        
        # Process metrics in batches of 20 (CloudWatch limit)
        for i in range(0, len(metrics), self.batch_size):
            batch = metrics[i:i + self.batch_size]
            
            try:
                metric_data = []
                for metric in batch:
                    data = {
                        'MetricName': metric.name,
                        'Value': metric.value,
                        'Unit': metric.unit.value,
                        'Timestamp': metric.timestamp
                    }
                    
                    if metric.dimensions:
                        data['Dimensions'] = [
                            {'Name': key, 'Value': value}
                            for key, value in metric.dimensions.items()
                        ]
                    
                    metric_data.append(data)
                
                response = self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=metric_data
                )
                
                success_count += len(batch)
                self.log_debug(f"Emitted batch of {len(batch)} metrics")
                
            except Exception as e:
                self.log_error(f"Failed to emit metrics batch: {e}")
        
        return success_count
    
    async def flush_buffered_metrics(self) -> int:
        """Flush all buffered metrics to CloudWatch"""
        metrics = await self.collector.get_buffered_metrics()
        if not metrics:
            return 0
        
        success_count = await self.emit_metrics_batch(metrics)
        
        if success_count > 0:
            await self.collector.clear_buffer()
            self.log_info(f"Flushed {success_count} metrics to CloudWatch")
        
        return success_count
    
    async def emit_system_metrics(self):
        """Emit current system metrics"""
        try:
            # Cache hit ratio
            hit_ratio = await self.collector.get_cache_hit_ratio()
            await self.collector.metrics_buffer["system"].append(
                MetricData(
                    name="CacheHitRatio",
                    value=hit_ratio * 100,  # Convert to percentage
                    unit=MetricUnit.PERCENT,
                    metric_type=MetricType.CACHE
                )
            )
            
            # Average response time
            avg_response_time = await self.collector.get_average_response_time()
            await self.collector.metrics_buffer["system"].append(
                MetricData(
                    name="AverageResponseTime",
                    value=avg_response_time,
                    unit=MetricUnit.MILLISECONDS,
                    metric_type=MetricType.API_PERFORMANCE
                )
            )
            
            # Error rate
            error_rate = await self.collector.get_error_rate()
            await self.collector.metrics_buffer["system"].append(
                MetricData(
                    name="ErrorRate",
                    value=error_rate * 100,  # Convert to percentage
                    unit=MetricUnit.PERCENT,
                    metric_type=MetricType.ERROR
                )
            )
            
            # Analysis completion rate
            completed = self.collector.analysis_stats['completed']
            failed = self.collector.analysis_stats['failed']
            total = completed + failed
            
            if total > 0:
                completion_rate = (completed / total) * 100
                await self.collector.metrics_buffer["business"].append(
                    MetricData(
                        name="AnalysisCompletionRate",
                        value=completion_rate,
                        unit=MetricUnit.PERCENT,
                        metric_type=MetricType.BUSINESS
                    )
                )
            
        except Exception as e:
            self.log_error(f"Failed to emit system metrics: {e}")
    
    async def start_background_flush(self):
        """Start background task to periodically flush metrics"""
        async def flush_loop():
            while True:
                try:
                    await asyncio.sleep(self.flush_interval)
                    await self.emit_system_metrics()
                    await self.flush_buffered_metrics()
                except Exception as e:
                    self.log_error(f"Error in metrics flush loop: {e}")
        
        asyncio.create_task(flush_loop())
        self.log_info(f"Started background metrics flush (interval: {self.flush_interval}s)")
    
    def get_collector(self) -> MetricsCollector:
        """Get the metrics collector instance"""
        return self.collector


# Global metrics service instance
_metrics_service: Optional[CloudWatchMetricsService] = None


def get_metrics_service() -> CloudWatchMetricsService:
    """Get the global metrics service instance"""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = CloudWatchMetricsService()
    return _metrics_service


async def initialize_metrics_service():
    """Initialize the metrics service and start background tasks"""
    service = get_metrics_service()
    if service.enabled:
        await service.start_background_flush()


# Convenience functions for common metrics
async def record_api_response_time(endpoint: str, method: str, duration_ms: float, status_code: int):
    """Record API response time"""
    service = get_metrics_service()
    await service.collector.record_api_response_time(endpoint, method, duration_ms, status_code)


async def record_error(error_category: str, endpoint: str = None):
    """Record error occurrence"""
    service = get_metrics_service()
    await service.collector.record_error(error_category, endpoint)


async def record_cache_hit(cache_type: str = "redis"):
    """Record cache hit"""
    service = get_metrics_service()
    await service.collector.record_cache_hit(cache_type)


async def record_cache_miss(cache_type: str = "redis"):
    """Record cache miss"""
    service = get_metrics_service()
    await service.collector.record_cache_miss(cache_type)


async def record_analysis_completion(ticker: str, analysis_type: str, duration_seconds: float, success: bool):
    """Record stock analysis completion"""
    service = get_metrics_service()
    await service.collector.record_analysis_completion(ticker, analysis_type, duration_seconds, success)