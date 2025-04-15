"""Main FastAPI application instance"""

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging
from typing import Callable

from backend.shared.config.settings import get_settings
from backend.shared.config.logging_config import configure_logging, get_logger
from backend.services.api.src.middleware.logging import LoggingMiddleware
from backend.services.api.src.middleware.metrics import MetricsMiddleware
from backend.services.api.src.middleware.rate_limit import RateLimitMiddleware
from backend.services.api.src.middleware.auth import AuthMiddleware
from backend.services.api.src.health_setup import setup_health_checks

from backend.services.api.src.routers import listings, alerts, health, users
from backend.services.api.src.routes import auth_routes, websocket_routes
from backend.services.api.src.websocket import websocket_manager

# Configure logging
configure_logging(service_name="api-service")
logger = get_logger("api")

# Get settings
settings = get_settings("api")

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application
    
    Returns:
        FastAPI: Configured application instance
    """
    # Create FastAPI app
    app = FastAPI(
        title="Facebook Marketplace Scraper API",
        description="API for the Facebook Marketplace Scraper",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthMiddleware)
    
    # Register exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler for unhandled exceptions"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred"
            }
        )
    
    # Register startup event handler
    @app.on_event("startup")
    async def startup_event():
        """Startup event handler"""
        logger.info("API service starting")
        
        # Any startup initialization can go here
        # e.g., database connections, warm up caches, etc.
    
    # Register shutdown event handler
    @app.on_event("shutdown")
    async def shutdown_event():
        """Shutdown event handler"""
        logger.info("API service shutting down")
        
        # Close WebSocket connections
        try:
            await websocket_manager.close_all()
            logger.info("Closed all WebSocket connections")
        except Exception as e:
            logger.error(f"Error closing WebSocket connections: {str(e)}")
    
    # Setup API routes
    
    # Health check endpoints
    setup_health_checks(app)
    
    # API routers
    app.include_router(health.router)
    app.include_router(auth_routes.router)
    app.include_router(users.router)
    app.include_router(listings.router)
    app.include_router(alerts.router)
    
    # WebSocket routes
    app.include_router(websocket_routes.router)
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "Facebook Marketplace Scraper API",
            "version": "2.0.0",
            "docs": "/docs",
        }
    
    return app

# Create the FastAPI application instance
app = create_app() 