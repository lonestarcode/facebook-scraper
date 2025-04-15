"""
Shared utilities for collecting and exposing metrics using Prometheus.
"""
import time
import threading
from functools import wraps
from typing import Callable, Dict, Optional, Union, List

from prometheus_client import Counter, Gauge, Histogram, Summary, start_http_server
from shared.config.logging_config import get_logger

logger = get_logger("shared.utils.metrics")

# Global registry of metrics
_metrics: Dict[str, Union[Counter, Gauge, Histogram, Summary]] = {}

# Default buckets for histograms
DEFAULT_BUCKETS = [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]


class MetricsCollector:
    """
    Class for collecting and exposing Prometheus metrics.
    """
    
    def __init__(self, service_name: str, expose_endpoint: bool = True, port: int = 8000):
        """
        Initialize a metrics collector for a specific service.
        
        Args:
            service_name: Name of the service (used as prefix for metrics)
            expose_endpoint: Whether to expose metrics via HTTP endpoint
            port: Port to expose metrics on if expose_endpoint is True
        """
        self.service_name = service_name
        self.prefix = f"{service_name}_"
        
        # Start metrics server in background thread if needed
        if expose_endpoint:
            threading.Thread(
                target=start_http_server,
                args=(port,),
                daemon=True,
            ).start()
            logger.info(f"Started metrics server for {service_name} on port {port}")
    
    def counter(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
    ) -> Counter:
        """
        Create or get a Counter metric.
        
        Args:
            name: Metric name
            description: Metric description
            labels: Optional list of label names
            
        Returns:
            Counter metric
        """
        full_name = f"{self.prefix}{name}"
        if full_name not in _metrics:
            _metrics[full_name] = Counter(
                full_name,
                description,
                labels or [],
            )
        return _metrics[full_name]
    
    def gauge(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
    ) -> Gauge:
        """
        Create or get a Gauge metric.
        
        Args:
            name: Metric name
            description: Metric description
            labels: Optional list of label names
            
        Returns:
            Gauge metric
        """
        full_name = f"{self.prefix}{name}"
        if full_name not in _metrics:
            _metrics[full_name] = Gauge(
                full_name,
                description,
                labels or [],
            )
        return _metrics[full_name]
    
    def histogram(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
        buckets: Optional[List[float]] = None,
    ) -> Histogram:
        """
        Create or get a Histogram metric.
        
        Args:
            name: Metric name
            description: Metric description
            labels: Optional list of label names
            buckets: Optional list of bucket boundaries
            
        Returns:
            Histogram metric
        """
        full_name = f"{self.prefix}{name}"
        if full_name not in _metrics:
            _metrics[full_name] = Histogram(
                full_name,
                description,
                labels or [],
                buckets=buckets or DEFAULT_BUCKETS,
            )
        return _metrics[full_name]
    
    def summary(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
    ) -> Summary:
        """
        Create or get a Summary metric.
        
        Args:
            name: Metric name
            description: Metric description
            labels: Optional list of label names
            
        Returns:
            Summary metric
        """
        full_name = f"{self.prefix}{name}"
        if full_name not in _metrics:
            _metrics[full_name] = Summary(
                full_name,
                description,
                labels or [],
            )
        return _metrics[full_name]
    
    def time_this(
        self,
        metric_name: str,
        description: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Callable:
        """
        Decorator to time a function and record the duration.
        
        Args:
            metric_name: Name of the metric to use
            description: Description of the metric
            labels: Optional dictionary of label values
            
        Returns:
            Decorator function
        """
        histogram = self.histogram(
            f"{metric_name}_seconds",
            description,
            labels=list(labels.keys()) if labels else None,
        )
        
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start
                    if labels:
                        histogram.labels(**labels).observe(duration)
                    else:
                        histogram.observe(duration)
                    return result
                except Exception as e:
                    duration = time.time() - start
                    if labels:
                        histogram.labels(**labels).observe(duration)
                    else:
                        histogram.observe(duration)
                    raise e
            return wrapper
        return decorator 