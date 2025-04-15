from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.orm import Session, joinedload

from shared.database.session import get_db_session
from shared.models.marketplace import Alert, Listing, listing_alerts
from shared.repositories.base import BaseRepository
from shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class AlertRepository(BaseRepository[Alert]):
    """Repository for marketplace alerts."""

    def __init__(self):
        """Initialize the repository with the Alert model."""
        super().__init__(Alert)
    
    def get_by_user_id(
        self,
        user_id: Union[int, str],
        active_only: bool = True,
        db_session: Optional[Session] = None
    ) -> List[Alert]:
        """
        Get all alerts for a specific user.
        
        Args:
            user_id: User ID
            active_only: Only return active alerts
            db_session: Optional database session
            
        Returns:
            List of alerts
        """
        with db_session or get_db_session() as session:
            query = select(Alert).where(Alert.user_id == user_id)
            
            if active_only:
                query = query.where(Alert.is_active == True)
                
            return list(session.execute(query).scalars().all())
    
    def match_listing_to_alerts(
        self,
        listing: Listing,
        db_session: Optional[Session] = None
    ) -> List[Alert]:
        """
        Find alerts that match a specific listing.
        
        Args:
            listing: Listing to match against alerts
            db_session: Optional database session
            
        Returns:
            List of matching alerts
        """
        with db_session or get_db_session() as session:
            # Build filters for matching alerts
            filters = [Alert.is_active == True]
            
            # Price filters
            if listing.price is not None:
                # Either min_price is null or listing price is above min_price
                min_price_filter = or_(
                    Alert.min_price.is_(None),
                    listing.price >= Alert.min_price
                )
                filters.append(min_price_filter)
                
                # Either max_price is null or listing price is below max_price
                max_price_filter = or_(
                    Alert.max_price.is_(None),
                    listing.price <= Alert.max_price
                )
                filters.append(max_price_filter)
            
            # Location filter
            if listing.location:
                # Either alert location is null or listing location contains alert location
                location_filter = or_(
                    Alert.location.is_(None),
                    Alert.location == '',
                    listing.location.ilike(f'%{Alert.location}%')
                )
                filters.append(location_filter)
            
            # Category filter
            if listing.category:
                # If alert has categories JSON array with listing category
                # This is a simplistic approach - in production, you'd use proper JSON queries
                category_filter = or_(
                    Alert.categories.is_(None),
                    Alert.categories == '[]',
                    Alert.categories.cast(str).like(f'%"{listing.category}"%')
                )
                filters.append(category_filter)
            
            # Search query filter
            # This is a very basic implementation - in production you'd likely use full-text search
            title = listing.title.lower() if listing.title else ''
            description = listing.description.lower() if listing.description else ''
            
            query_filter = Alert.search_query.in_([
                # Exact matches
                title, 
                description, 
                # Check if alert query is contained in title or description
                *[q for q in session.query(Alert.search_query).distinct() 
                  if q and (q.lower() in title or q.lower() in description)]
            ])
            filters.append(query_filter)
            
            # Build and execute query
            query = select(Alert).where(and_(*filters))
            matching_alerts = list(session.execute(query).scalars().all())
            
            # Update matched alerts and the listing-alert association
            if matching_alerts:
                # Update the listing status
                listing.status = "MATCHED"
                
                # Create associations
                now = datetime.utcnow()
                for alert in matching_alerts:
                    # Check if this listing is already associated with this alert
                    assoc_exists = session.query(listing_alerts).filter_by(
                        listing_id=listing.id,
                        alert_id=alert.id
                    ).first() is not None
                    
                    if not assoc_exists:
                        # Create the association
                        stmt = listing_alerts.insert().values(
                            listing_id=listing.id,
                            alert_id=alert.id,
                            matched_at=now,
                            notified=False
                        )
                        session.execute(stmt)
                        
                        # Update the alert's last_matched_at
                        alert.last_matched_at = now
                
                session.commit()
            
            return matching_alerts
    
    def get_pending_notifications(
        self,
        limit: int = 100,
        db_session: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Get alerts with listings that need notifications.
        
        Args:
            limit: Maximum number of notifications to retrieve
            db_session: Optional database session
            
        Returns:
            List of notification data dictionaries
        """
        with db_session or get_db_session() as session:
            # Query for alerts with listings that haven't been notified
            query = (
                select(Alert, Listing)
                .join(listing_alerts, Alert.id == listing_alerts.c.alert_id)
                .join(Listing, Listing.id == listing_alerts.c.listing_id)
                .where(listing_alerts.c.notified == False)
                .where(Alert.is_active == True)
                .limit(limit)
            )
            
            results = session.execute(query).all()
            
            notifications = []
            for alert, listing in results:
                # Get the association record
                assoc = session.query(listing_alerts).filter_by(
                    alert_id=alert.id,
                    listing_id=listing.id
                ).first()
                
                if assoc and not assoc.notified:
                    notifications.append({
                        "alert_id": alert.id,
                        "alert": alert,
                        "listing_id": listing.id,
                        "listing": listing,
                        "matched_at": assoc.matched_at,
                        "user_id": alert.user_id,
                        "notification_email": alert.notification_email,
                        "notification_sms": alert.notification_sms
                    })
            
            return notifications
    
    def mark_notified(
        self,
        alert_id: int,
        listing_id: int,
        db_session: Optional[Session] = None
    ) -> bool:
        """
        Mark a listing-alert pair as notified.
        
        Args:
            alert_id: Alert ID
            listing_id: Listing ID
            db_session: Optional database session
            
        Returns:
            True if successful, False otherwise
        """
        with db_session or get_db_session() as session:
            stmt = (
                update(listing_alerts)
                .where(listing_alerts.c.alert_id == alert_id)
                .where(listing_alerts.c.listing_id == listing_id)
                .values(
                    notified=True,
                    notification_sent_at=datetime.utcnow()
                )
            )
            result = session.execute(stmt)
            session.commit()
            
            return result.rowcount > 0


# Singleton instance
alert_repository = AlertRepository() 