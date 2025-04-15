"""Health check configuration for the API service"""

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from fastapi import FastAPI, Depends, Response, status
from pydantic import BaseModel

# Import logging config
from shared.config.logging_config import get_logger

logger = get_logger(__name__)

class HealthStatus(BaseModel):
    """Model representing the health status of the service"""
    status: str = "ok"
    version: str = os.getenv("VERSION", "2.0.0")
    service: str = "api-service"
    checks: Dict[str, bool] = {}
    details: Dict[str, str] = {}

class HealthCheck:
    """Health check manager for the service"""
    
    def __init__(self, service_name: str):
        """Initialize the health check manager
        
        Args:
            service_name: The name of the service
        """
        self.service_name = service_name
        self.checks = {
            "service": True,
            "database": False,
            "auth-provider": False,
            "rate-limiter": False,
            "processor-service": False,
            "scraper-service": False
        }
        self.details = {
            "service": "Service starting up",
            "database": "Not connected",
            "auth-provider": "Not configured",
            "rate-limiter": "Not initialized",
            "processor-service": "Not connected",
            "scraper-service": "Not connected"
        }
        self.start_time = time.time()
        logger.info(f"Health check initialized for {service_name}")
    
    def set_component_status(self, component: str, status: bool, details: str) -> None:
        """Set the status of a component
        
        Args:
            component: The name of the component
            status: Whether the component is healthy
            details: Details about the component status
        """
        if component in self.checks:
            old_status = self.checks[component]
            self.checks[component] = status
            self.details[component] = details
            
            if old_status != status:
                log_level = logging.INFO if status else logging.ERROR
                logger.log(log_level, f"Component {component} health changed to {status}: {details}")
        else:
            self.checks[component] = status
            self.details[component] = details
            logger.info(f"Added new component {component} with health {status}: {details}")
    
    def get_health(self) -> HealthStatus:
        """Get the overall health status
        
        Returns:
            The health status object
        """
        status = "ok"
        
        # Check if any component is unhealthy
        if not all(self.checks.values()):
            status = "degraded"
            
        # If the core components are down, the service is in error state
        core_components = ["service", "database", "auth-provider"]
        if not all(self.checks.get(comp, False) for comp in core_components):
            status = "error"
            
        return HealthStatus(
            status=status,
            version=os.getenv("VERSION", "2.0.0"),
            service=self.service_name,
            checks=self.checks,
            details=self.details
        )
    
    def is_healthy(self) -> bool:
        """Check if the service is healthy
        
        Returns:
            True if all components are healthy, False otherwise
        """
        return all(self.checks.values())
    
    def is_ready(self) -> bool:
        """Check if the service is ready
        
        Returns:
            True if the service and core components are healthy, False otherwise
        """
        required_components = ["service", "database", "auth-provider"]
        return all(self.checks.get(component, False) for component in required_components)
    
    def is_alive(self) -> bool:
        """Check if the service is alive
        
        Returns:
            True if the service component is healthy, False otherwise
        """
        return self.checks.get("service", False)
    
    def uptime(self) -> float:
        """Get the uptime of the service in seconds
        
        Returns:
            The uptime in seconds
        """
        return time.time() - self.start_time
    
    def dependent_services_status(self) -> Dict[str, bool]:
        """Get the status of dependent services
        
        Returns:
            A dictionary mapping service names to their statuses
        """
        return {
            "processor": self.checks.get("processor-service", False),
            "scraper": self.checks.get("scraper-service", False)
        }

def create_health_check(service_name: str = "api-service") -> HealthCheck:
    """Create a health check manager
    
    Args:
        service_name: The name of the service
        
    Returns:
        A health check manager
    """
    return HealthCheck(service_name)

def setup_health_checks(app: FastAPI, health_check: HealthCheck) -> None:
    """Set up health check endpoints for the FastAPI app
    
    Args:
        app: The FastAPI application
        health_check: The health check manager
    """
    @app.get("/health", tags=["Health"])
    async def health():
        """Get the health status of the service"""
        health_status = health_check.get_health()
        return health_status
    
    @app.get("/health/ready", tags=["Health"])
    async def ready(response: Response):
        """Check if the service is ready to handle requests"""
        is_ready = health_check.is_ready()
        if not is_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        
        return {
            "ready": is_ready,
            "uptime": health_check.uptime()
        }
    
    @app.get("/health/live", tags=["Health"])
    async def live(response: Response):
        """Check if the service is alive"""
        is_alive = health_check.is_alive()
        if not is_alive:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            
        return {
            "alive": is_alive,
            "uptime": health_check.uptime()
        }
    
    @app.get("/health/component/{component}", tags=["Health"])
    async def component_status(component: str):
        """Get the status of a specific component"""
        if component in health_check.checks:
            return {
                "component": component,
                "healthy": health_check.checks[component],
                "details": health_check.details[component]
            }
        return {"error": f"Component {component} not found"}
    
    @app.get("/health/dependencies", tags=["Health"])
    async def dependencies():
        """Get the status of dependent services"""
        return {
            "dependencies": health_check.dependent_services_status(),
            "details": {
                k: health_check.details.get(f"{k}-service", "Unknown") 
                for k in ["processor", "scraper"]
            }
        }
    
    logger.info("Health check endpoints configured") 