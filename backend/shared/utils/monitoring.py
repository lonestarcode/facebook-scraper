"""Monitoring utilities using Prometheus for metrics collection."""

import time
import logging
import functools
from typing import Optional, Dict, Any, Callable, List, Union
from contextlib import contextmanager
from enum import Enum

from prometheus_client import Counter, Histogram, Gauge, Summary
from prometheus_client import CollectorRegistry, push_to_gateway
from prometheus_client import start_http_server

logger = logging.getLogger(__name__)

# Global registry for metrics
registry = CollectorRegistry()

# Application metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total count of HTTP requests',
    ['service', 'endpoint', 'method', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['service', 'endpoint', 'method'],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

DB_OPERATION_COUNT = Counter(
    'db_operations_total',
    'Total count of database operations',
    ['service', 'operation', 'table', 'status']
)

DB_OPERATION_LATENCY = Histogram(
    'db_operation_duration_seconds',
    'Database operation latency in seconds',
    ['service', 'operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

SCRAPER_LISTINGS_COUNT = Counter(
    'scraper_listings_total', 
    'Total number of listings scraped',
    ['marketplace', 'category'],
    registry=registry
)

ERRORS_COUNT = Counter(
    'errors_total', 
    'Total number of errors',
    ['service', 'type'],
    registry=registry
)

ACTIVE_USERS = Gauge(
    'active_users', 
    'Number of active users',
    registry=registry
)

ACTIVE_LISTINGS = Gauge(
    'active_listings', 
    'Number of active listings',
    registry=registry
)

# Service health status
SERVICE_HEALTH = Gauge(
    'service_health', 
    'Health status of service (1=healthy, 0=unhealthy)',
    ['service'],
    registry=registry
)

# Kafka metrics
KAFKA_MESSAGE_COUNT = Counter(
    'kafka_messages_total',
    'Total count of Kafka messages',
    ['service', 'topic', 'operation']
)

KAFKA_MESSAGE_LATENCY = Histogram(
    'kafka_message_processing_seconds',
    'Kafka message processing time in seconds',
    ['service', 'topic'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

# Scraper-specific metrics
SCRAPE_COUNTER = Counter(
    'scrapes_total',
    'Total count of scraping operations',
    ['scraper', 'status', 'reason']
)

SCRAPE_DURATION = Histogram(
    'scrape_duration_seconds',
    'Duration of scraping operations',
    ['scraper'],
    buckets=(1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)
)

PROCESSING_ERRORS = Counter(
    'processing_errors_total',
    'Total count of processing errors',
    ['service', 'processor', 'error_type']
)

# WebSocket metrics
WEBSOCKET_CONNECTIONS = Gauge(
    'websocket_connections_current',
    'Current number of active WebSocket connections',
)

WEBSOCKET_MESSAGES_SENT = Counter(
    'websocket_messages_sent_total',
    'Total count of messages sent through WebSockets',
)

WEBSOCKET_ERRORS = Counter(
    'websocket_errors_total',
    'Total count of WebSocket errors',
    ['type']
)

# Resource metrics
MEMORY_USAGE = Gauge(
    'process_memory_bytes',
    'Memory usage in bytes',
    ['service']
)

CPU_USAGE = Gauge(
    'process_cpu_percent',
    'CPU usage percentage',
    ['service']
)

# Component health status
COMPONENT_HEALTH = Gauge(
    'component_health_status',
    'Health status of system components (1 = healthy, 0 = unhealthy)',
    ['service', 'component']
)

class TimerContextManager:
    """Context manager for timing operations and recording in a Histogram."""
    
    def __init__(self, metric, **labels):
        self.metric = metric
        self.labels = labels
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.metric.labels(**self.labels).observe(duration)
        
def time_operation(metric, **labels):
    """Create a context manager for timing an operation.
    
    Args:
        metric: The Prometheus Histogram metric to record to
        **labels: Labels to apply to the metric
        
    Returns:
        A context manager that times the operation
    """
    return TimerContextManager(metric, **labels)

def update_component_health(service: str, component: str, is_healthy: bool):
    """Update the health status of a component.
    
    Args:
        service: The service name
        component: The component name
        is_healthy: Whether the component is healthy
    """
    COMPONENT_HEALTH.labels(service=service, component=component).set(1 if is_healthy else 0)

def track_error(service: str, error_type: str, processor: str = "general"):
    """Track a processing error.
    
    Args:
        service: The service name
        error_type: The type of error
        processor: The processor that encountered the error
    """
    PROCESSING_ERRORS.labels(
        service=service,
        processor=processor,
        error_type=error_type
    ).inc()

def setup_monitoring(
    service_name: str,
    push_gateway_url: Optional[str] = None,
    metrics_port: Optional[int] = None
) -> None:
    """
    Set up monitoring for a service.
    
    Args:
        service_name: Name of the service
        push_gateway_url: Optional URL for Prometheus push gateway
        metrics_port: Port to expose metrics HTTP server, if None, server is not started
    """
    # Initialize service health as healthy
    SERVICE_HEALTH.labels(service=service_name).set(1)
    
    # Start metrics server if port is provided
    if metrics_port:
        try:
            start_http_server(metrics_port)
            logger.info(f"Started metrics server on port {metrics_port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
    
    # Push initial metrics to gateway if URL is provided
    if push_gateway_url:
        try:
            push_to_gateway(push_gateway_url, job=service_name, registry=registry)
            logger.info(f"Connected to Prometheus push gateway at {push_gateway_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Prometheus push gateway: {e}")


@contextmanager
def track_db_operation(operation: str, table: str):
    """
    Context manager to track database operation latency.
    
    Args:
        operation: Type of operation (insert, update, select, delete)
        table: Database table name
    """
    start_time = time.time()
    try:
        yield
    finally:
        latency = time.time() - start_time
        DB_OPERATION_LATENCY.labels(operation=operation, table=table).observe(latency)


def record_error(service: str, error_type: str):
    """
    Record an error occurrence.
    
    Args:
        service: Name of the service
        error_type: Type of error
    """
    ERRORS_COUNT.labels(service=service, error_type=error_type).inc()


def update_health_status(service: str, is_healthy: bool):
    """
    Update service health status.
    
    Args:
        service: Name of the service
        is_healthy: True if healthy, False otherwise
    """
    SERVICE_HEALTH.labels(service=service).set(1 if is_healthy else 0)


def update_user_count(count: int):
    """
    Update the active user count.
    
    Args:
        count: Number of active users
    """
    ACTIVE_USERS.set(count)


def update_listing_count(count: int):
    """
    Update the active listing count.
    
    Args:
        count: Number of active listings
    """
    ACTIVE_LISTINGS.set(count)


def monitor_endpoint(method: str, endpoint: str):
    """
    Decorator to monitor HTTP endpoint performance.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                response = await func(*args, **kwargs)
                status_code = response.status_code
            except Exception as e:
                # Record error and re-raise
                record_error("api", type(e).__name__)
                status_code = 500
                raise
            finally:
                # Record request count and latency
                latency = time.time() - start_time
                REQUEST_COUNT.labels(
                    service="api",
                    endpoint=endpoint,
                    method=method,
                    status_code=status_code
                ).inc()
                REQUEST_LATENCY.labels(
                    service="api",
                    endpoint=endpoint,
                    method=method
                ).observe(latency)
            
            return response
        
        return wrapper
    
    return decorator 