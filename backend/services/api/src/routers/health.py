from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import time
from typing import Dict, Any

from shared.database.session import get_db_session
from shared.utils.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.get("/health", summary="Health check endpoint")
async def health_check() -> Dict[str, Any]:
    """
    Check the health of the API service and its dependencies.
    
    Returns:
        Health check information
    """
    start_time = time.time()
    health_info = {
        "status": "ok",
        "timestamp": time.time(),
        "uptime": time.time() - start_time,
        "dependencies": {
            "database": {"status": "unknown"},
        }
    }
    
    # Check database health
    try:
        with get_db_session() as session:
            # Execute a simple query
            session.execute("SELECT 1")
            health_info["dependencies"]["database"] = {
                "status": "ok", 
                "response_time": time.time() - start_time
            }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}", exc_info=True)
        health_info["dependencies"]["database"] = {
            "status": "error",
            "error": str(e)
        }
        health_info["status"] = "degraded"
    
    return health_info

@router.get("/readiness", summary="Readiness check endpoint")
async def readiness_check() -> Dict[str, str]:
    """
    Check if the service is ready to handle requests.
    
    Returns:
        Readiness status
    """
    return {"status": "ready"}

@router.get("/liveness", summary="Liveness check endpoint")
async def liveness_check() -> Dict[str, str]:
    """
    Check if the service is alive.
    
    Returns:
        Liveness status
    """
    return {"status": "alive"} 