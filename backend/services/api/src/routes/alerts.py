"""API endpoints for price and availability alerts."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, Body
from sqlalchemy.orm import Session

from shared.models.schema import PriceAlertSchema, AlertResponseSchema
from shared.models.marketplace import PriceAlert, User
from src.database.session import get_db
from src.middleware.auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[AlertResponseSchema])
async def get_user_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all alerts for the current user."""
    alerts = db.query(PriceAlert).filter(PriceAlert.user_id == current_user.id).all()
    return alerts

@router.post("/", response_model=AlertResponseSchema, status_code=201)
async def create_alert(
    alert_data: PriceAlertSchema = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new price alert for the current user."""
    # Create new alert
    new_alert = PriceAlert(
        user_id=current_user.id,
        search_term=alert_data.search_term,
        category=alert_data.category,
        min_price=alert_data.min_price,
        max_price=alert_data.max_price,
        location=alert_data.location,
        notification_method=alert_data.notification_method,
        notification_target=alert_data.notification_target,
        is_active=True
    )
    
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)
    
    # Publish event to Kafka
    from shared.utils.kafka import get_kafka_client
    kafka_client = get_kafka_client("api")
    kafka_client.publish_event(
        topic="marketplace.alert.created",
        key=str(new_alert.id),
        value={
            "alert_id": new_alert.id,
            "user_id": current_user.id,
            "search_term": new_alert.search_term,
            "category": new_alert.category,
            "min_price": new_alert.min_price,
            "max_price": new_alert.max_price
        }
    )
    
    return new_alert

@router.put("/{alert_id}", response_model=AlertResponseSchema)
async def update_alert(
    alert_id: int = Path(..., description="The ID of the alert to update"),
    alert_data: PriceAlertSchema = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing price alert."""
    alert = db.query(PriceAlert).filter(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Update alert fields
    for field, value in alert_data.dict(exclude_unset=True).items():
        setattr(alert, field, value)
    
    db.commit()
    db.refresh(alert)
    
    # Publish update event
    from shared.utils.kafka import get_kafka_client
    kafka_client = get_kafka_client("api")
    kafka_client.publish_event(
        topic="marketplace.alert.updated",
        key=str(alert.id),
        value={
            "alert_id": alert.id,
            "user_id": current_user.id,
            "search_term": alert.search_term,
            "category": alert.category,
            "min_price": alert.min_price,
            "max_price": alert.max_price
        }
    )
    
    return alert

@router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: int = Path(..., description="The ID of the alert to delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a price alert."""
    alert = db.query(PriceAlert).filter(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Delete from database
    db.delete(alert)
    db.commit()
    
    # Publish delete event
    from shared.utils.kafka import get_kafka_client
    kafka_client = get_kafka_client("api")
    kafka_client.publish_event(
        topic="marketplace.alert.deleted",
        key=str(alert_id),
        value={
            "alert_id": alert_id,
            "user_id": current_user.id
        }
    )
    
    return None 