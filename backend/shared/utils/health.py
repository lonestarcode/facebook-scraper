"""
Shared health check utilities for all services.

This module provides base functionality for health checks that can be
used across all microservices, ensuring consistent implementations.
"""

import logging
import os
from enum import Enum
from typing import Dict, Optional, List, Callable, Any, Union

from fastapi import FastAPI, APIRouter, Response, status, HTTPException, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ComponentStatus(str, Enum):
    """Status enum for health check components."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class HealthCheckComponent(BaseModel):
    """Component health check model."""
    status: ComponentStatus = ComponentStatus.UNKNOWN
    message: Optional[str] = None
    last_checked: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    service: str
    version: str
    status: ComponentStatus = ComponentStatus.UNKNOWN
    components: Dict[str, HealthCheckComponent] = {}
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    timestamp: str = Field(default_factory=lambda: import_datetime().utcnow().isoformat())


def import_datetime():
    """Import datetime lazily to avoid circular imports."""
    from datetime import datetime
    return datetime


class HealthCheck:
    """Health check manager for services."""
    
    def __init__(self, service_name: str, version: str = "1.0.0"):
        """
        Initialize the health check manager.
        
        Args:
            service_name: Name of the service
            version: Service version
        """
        self.service_name = service_name
        self.version = version
        self.components: Dict[str, HealthCheckComponent] = {}
        self.critical_components: List[str] = []
        
    def register_component(
        self, 
        name: str, 
        initial_status: ComponentStatus = ComponentStatus.UNKNOWN,
        message: Optional[str] = None,
        is_critical: bool = False
    ) -> None:
        """
        Register a component to be health checked.
        
        Args:
            name: Component name
            initial_status: Initial status
            message: Status message
            is_critical: Whether this component is critical for readiness
        """
        self.components[name] = HealthCheckComponent(
            status=initial_status,
            message=message,
            last_checked=import_datetime().utcnow().isoformat()
        )
        
        if is_critical:
            self.critical_components.append(name)
        
        logger.info(f"Registered health check component: {name} (critical: {is_critical})")
    
    def update_status(
        self, 
        component: str, 
        status: ComponentStatus,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update the status of a component.
        
        Args:
            component: Component name
            status: New status
            message: Status message
            details: Additional details
        """
        if component not in self.components:
            self.register_component(component, status, message)
        
        self.components[component].status = status
        self.components[component].message = message
        self.components[component].last_checked = import_datetime().utcnow().isoformat()
        
        if details:
            self.components[component].details = details
        
        logger.info(f"Updated component {component} status to {status}: {message}")
    
    def get_health(self) -> HealthCheckResponse:
        """
        Get the current health status.
        
        Returns:
            Health check response
        """
        # Get overall status
        status = ComponentStatus.HEALTHY
        
        # If any critical component is unhealthy, overall status is unhealthy
        for name, component in self.components.items():
            if name in self.critical_components and component.status != ComponentStatus.HEALTHY:
                status = ComponentStatus.UNHEALTHY
                break
        
        # If any component is unhealthy but not critical, status is degraded
        if status == ComponentStatus.HEALTHY:
            for component in self.components.values():
                if component.status != ComponentStatus.HEALTHY:
                    status = ComponentStatus.DEGRADED
                    break
        
        return HealthCheckResponse(
            service=self.service_name,
            version=self.version,
            status=status,
            components=self.components
        )
    
    def is_ready(self) -> bool:
        """
        Check if the service is ready to handle requests.
        
        Returns:
            True if all critical components are healthy
        """
        for name in self.critical_components:
            component = self.components.get(name)
            if not component or component.status != ComponentStatus.HEALTHY:
                return False
        
        return True
    
    def is_alive(self) -> bool:
        """
        Check if the service is alive.
        
        Returns:
            True if at least one component is not in UNHEALTHY state
        """
        # A service is alive if not all components are unhealthy
        # or if there are no components registered
        if not self.components:
            return True
            
        for component in self.components.values():
            if component.status != ComponentStatus.UNHEALTHY:
                return True
                
        return False


def setup_health_endpoints(
    app: FastAPI,
    health_check: HealthCheck,
    endpoint_path: str = "/health",
    readiness_path: str = "/ready",
    liveness_path: str = "/live",
    require_auth: bool = False,
    router: Optional[APIRouter] = None
) -> None:
    """
    Set up health check endpoints.
    
    Args:
        app: FastAPI application
        health_check: HealthCheck instance
        endpoint_path: Path for the health endpoint
        readiness_path: Path for the readiness endpoint
        liveness_path: Path for the liveness endpoint
        require_auth: Whether authentication is required
        router: Optional router to add the endpoints to
    """
    target = router or app
    
    @target.get(endpoint_path, response_model=HealthCheckResponse, tags=["Health"])
    async def health():
        """Health check endpoint."""
        return health_check.get_health()
    
    @target.get(readiness_path, response_model=None, tags=["Health"])
    async def ready(response: Response):
        """Readiness probe endpoint."""
        if health_check.is_ready():
            return {"status": "ready"}
        
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not ready"}
    
    @target.get(liveness_path, response_model=None, tags=["Health"])
    async def live(response: Response):
        """Liveness probe endpoint."""
        if health_check.is_alive():
            return {"status": "alive"}
        
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not alive"}
    
    logger.info(f"Health check endpoints configured: {endpoint_path}, {readiness_path}, {liveness_path}")


def check_dependency(
    health_check: HealthCheck,
    component_name: str,
    check_function: Callable[[], bool]
) -> Callable:
    """
    Create a FastAPI dependency for checking component health.
    
    Args:
        health_check: HealthCheck instance
        component_name: Component name
        check_function: Function that returns True if component is healthy
        
    Returns:
        Decorator for FastAPI routes
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if not check_function():
                health_check.update_status(
                    component_name,
                    ComponentStatus.UNHEALTHY,
                    f"{component_name} check failed"
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"{component_name} is unhealthy"
                )
                
            # Update health status to healthy
            health_check.update_status(
                component_name,
                ComponentStatus.HEALTHY,
                f"{component_name} is healthy"
            )
                
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator 