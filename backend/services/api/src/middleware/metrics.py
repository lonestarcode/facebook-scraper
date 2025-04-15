"""
Middleware for collecting and exposing API metrics using Prometheus.
"""
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from shared.config.logging_config import get_logger

logger = get_logger("api.middleware.metrics")

# Define Prometheus metrics
REQUEST_COUNT = Counter(
    "api_request_count",
    "Count of requests received",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "api_request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint", "status"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting request metrics.
    Tracks request counts and latency by method, endpoint, and status code.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics collection for /metrics endpoint to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Start timer
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        duration = time.time() - start_time
        
        # Get a normalized path (replace path params with {param})
        endpoint = request.url.path
        for route in request.app.routes:
            if hasattr(route, "path") and route.path != endpoint:
                path_format = route.path
                if path_format.endswith("/{path:path}"):
                    # Handle catch-all routes
                    prefix = path_format.replace("/{path:path}", "")
                    if endpoint.startswith(prefix + "/"):
                        endpoint = path_format
                        break
                if route.path_regex.match(endpoint):
                    endpoint = route.path
                    break
        
        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()
        
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code
        ).observe(duration)
        
        return response


async def metrics_endpoint():
    """
    Endpoint that returns Prometheus metrics.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


def setup_metrics(app: FastAPI) -> None:
    """
    Set up metrics collection and endpoint for a FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Add middleware for metrics collection
    app.add_middleware(MetricsMiddleware)
    
    # Add /metrics endpoint
    app.add_route("/metrics", metrics_endpoint) 