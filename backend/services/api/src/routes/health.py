"""Health check endpoints for the API service."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.database.session import get_db
from shared.utils.kafka import get_kafka_client
from shared.config.settings import get_settings

router = APIRouter()

@router.get("/ready")
async def readiness_check(
    db: Session = Depends(get_db),
    response: Response = None
):
    """
    Readiness check for the API service.
    
    Verifies:
    - Database connection
    - Kafka connection
    """
    settings = get_settings("api")
    health_status = {
        "status": "ok",
        "database": "ok",
        "kafka": "ok",
        "version": settings.version,
        "service": "api"
    }
    
    # Check database connection
    try:
        # Simple query to check DB connection
        db.execute(text("SELECT 1"))
    except Exception as e:
        health_status["database"] = "error"
        health_status["database_error"] = str(e)
        health_status["status"] = "error"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    # Check Kafka connection
    try:
        kafka_client = get_kafka_client("api")
        kafka_client.check_connection()
    except Exception as e:
        health_status["kafka"] = "error"
        health_status["kafka_error"] = str(e)
        health_status["status"] = "error"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return health_status

@router.get("/live")
async def liveness_check():
    """
    Liveness check for the API service.
    
    A simple check that returns 200 if the service is running.
    """
    return {"status": "alive", "service": "api"} 