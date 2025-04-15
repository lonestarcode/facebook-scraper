"""Health check setup for the Scraper service."""

import logging
import os
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, Response, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class HealthStatus(BaseModel):
    """Health status model for the service."""
    status: str = "ok"
    version: str = "2.0.0"
    service: str = "scraper-service"
    checks: Dict[str, bool] = {}
    details: Dict[str, Any] = {}

class HealthCheck:
    """Health check manager for the service."""
    
    def __init__(self, service_name: str = "scraper-service", version: str = "2.0.0"):
        """Initialize the health check manager."""
        self.status = HealthStatus(
            service=service_name,
            version=version
        )
        self.components = {
            "service": True,
            "database": False,
            "kafka-producer": False,
            "browser-engine": False,
            "rate-limiter": False
        }
        self._update_status()
    
    def set_status(self, component: str, status: bool) -> None:
        """Set the status of a component."""
        self.components[component] = status
        self._update_status()
        logger.info(f"Health check component {component} set to {status}")
    
    def get_status(self) -> HealthStatus:
        """Get the current health status."""
        self._update_status()
        return self.status
    
    def is_healthy(self) -> bool:
        """Check if the service is healthy."""
        return all(self.components.values())
    
    def is_ready(self) -> bool:
        """Check if the service is ready to handle requests."""
        # Service is ready if critical components are up
        critical_components = ["service", "database", "browser-engine"]
        return all(self.components.get(comp, False) for comp in critical_components)
    
    def is_alive(self) -> bool:
        """Check if the service is alive."""
        # Service is alive if the main service component is up
        return self.components.get("service", False)
    
    def _update_status(self) -> None:
        """Update the overall status based on components."""
        self.status.checks = self.components
        self.status.status = "ok" if self.is_healthy() else "degraded"
        
        # Add additional details
        self.status.details = {
            "environment": os.getenv("ENVIRONMENT", "development"),
            "healthy": self.is_healthy(),
            "ready": self.is_ready(),
            "alive": self.is_alive(),
        }

def create_health_check(service_name: str = "scraper-service", version: str = "2.0.0") -> HealthCheck:
    """Create a health check instance."""
    return HealthCheck(service_name=service_name, version=version)

def setup_health_checks(app: FastAPI) -> HealthCheck:
    """Set up health check endpoints for the FastAPI application."""
    health_check = create_health_check()
    
    @app.get("/health", response_model=HealthStatus, tags=["Health"])
    async def health():
        """Overall health check endpoint."""
        status_obj = health_check.get_status()
        return status_obj
    
    @app.get("/health/ready", response_model=None, tags=["Health"])
    async def ready(response: Response):
        """Readiness probe endpoint."""
        if health_check.is_ready():
            return {"status": "ready"}
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not ready"}
    
    @app.get("/health/live", response_model=None, tags=["Health"])
    async def live(response: Response):
        """Liveness probe endpoint."""
        if health_check.is_alive():
            return {"status": "alive"}
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not alive"}
    
    @app.get("/health/status", response_model=Dict[str, bool], tags=["Health"])
    async def component_status():
        """Component status endpoint."""
        return health_check.components
    
    logger.info("Health check endpoints configured")
    return health_check 