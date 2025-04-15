from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional

from shared.database.session import get_db_session
from shared.models.marketplace import Alert
from shared.repositories.alert_repository import alert_repository
from shared.utils.logging_config import get_logger
from src.schemas.alert import AlertResponse, AlertCreate, AlertUpdate, PaginatedAlertResponse

router = APIRouter()
logger = get_logger(__name__)

@router.get("/", response_model=PaginatedAlertResponse, summary="Get all alerts")
async def get_alerts(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    active_only: bool = Query(True, description="Only return active alerts"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
) -> PaginatedAlertResponse:
    """
    Get all alerts with pagination.
    """
    try:
        # If user_id is provided, get alerts for that user
        if user_id is not None:
            items = alert_repository.get_by_user_id(user_id, active_only)
            total = len(items)
            # Manual pagination
            paginated_items = items[skip:skip+limit]
        else:
            # Otherwise, get all alerts
            items = alert_repository.get_all(skip=skip, limit=limit)
            total = alert_repository.count()
        
        # Convert to response models
        alert_responses = [AlertResponse.from_orm(alert) for alert in items]
        
        return PaginatedAlertResponse(
            items=alert_responses,
            total=total,
            page=skip // limit + 1 if limit > 0 else 1,
            pages=(total + limit - 1) // limit if limit > 0 else 1,
            size=len(alert_responses)
        )
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{alert_id}", response_model=AlertResponse, summary="Get alert by ID")
async def get_alert(
    alert_id: int = Path(..., description="ID of the alert to retrieve")
) -> AlertResponse:
    """
    Get a specific alert by its ID.
    """
    try:
        alert = alert_repository.get_by_id(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert with ID {alert_id} not found")
        return AlertResponse.from_orm(alert)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert {alert_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/", response_model=AlertResponse, status_code=201, summary="Create a new alert")
async def create_alert(
    alert_data: AlertCreate
) -> AlertResponse:
    """
    Create a new alert.
    """
    try:
        # Create alert
        alert_dict = alert_data.dict()
        alert = alert_repository.create(alert_dict)
        return AlertResponse.from_orm(alert)
    except Exception as e:
        logger.error(f"Error creating alert: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/{alert_id}", response_model=AlertResponse, summary="Update an alert")
async def update_alert(
    alert_id: int,
    alert_data: AlertUpdate
) -> AlertResponse:
    """
    Update an existing alert.
    """
    try:
        # Check if alert exists
        existing_alert = alert_repository.get_by_id(alert_id)
        if not existing_alert:
            raise HTTPException(status_code=404, detail=f"Alert with ID {alert_id} not found")
        
        # Update alert
        alert_dict = alert_data.dict(exclude_unset=True)
        updated_alert = alert_repository.update(alert_id, alert_dict)
        return AlertResponse.from_orm(updated_alert)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert {alert_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/{alert_id}", status_code=204, summary="Delete an alert")
async def delete_alert(
    alert_id: int
) -> None:
    """
    Delete an alert by its ID.
    """
    try:
        # Check if alert exists
        existing_alert = alert_repository.get_by_id(alert_id)
        if not existing_alert:
            raise HTTPException(status_code=404, detail=f"Alert with ID {alert_id} not found")
        
        # Delete alert
        alert_repository.delete(alert_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert {alert_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/{alert_id}/activate", response_model=AlertResponse, summary="Activate an alert")
async def activate_alert(
    alert_id: int
) -> AlertResponse:
    """
    Activate an alert.
    """
    try:
        # Check if alert exists
        existing_alert = alert_repository.get_by_id(alert_id)
        if not existing_alert:
            raise HTTPException(status_code=404, detail=f"Alert with ID {alert_id} not found")
        
        # Update alert
        updated_alert = alert_repository.update(alert_id, {"is_active": True})
        return AlertResponse.from_orm(updated_alert)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating alert {alert_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/{alert_id}/deactivate", response_model=AlertResponse, summary="Deactivate an alert")
async def deactivate_alert(
    alert_id: int
) -> AlertResponse:
    """
    Deactivate an alert.
    """
    try:
        # Check if alert exists
        existing_alert = alert_repository.get_by_id(alert_id)
        if not existing_alert:
            raise HTTPException(status_code=404, detail=f"Alert with ID {alert_id} not found")
        
        # Update alert
        updated_alert = alert_repository.update(alert_id, {"is_active": False})
        return AlertResponse.from_orm(updated_alert)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating alert {alert_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 