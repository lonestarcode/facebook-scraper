"""Database models for marketplace listings and alerts."""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, Boolean,
    ForeignKey, Enum, JSON, func, Table
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
import enum
import json

from shared.models.base import Base
from shared.database.session import Base as DatabaseBase
from shared.utils.logging_config import get_logger

logger = get_logger(__name__)

class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    preferences = Column(JSON, nullable=True)
    
    # Relationships
    alerts = relationship("PriceAlert", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        """String representation of the user."""
        return f"<User {self.username}>"


class ListingStatus(enum.Enum):
    """Status of a marketplace listing."""
    NEW = "new"               # Newly scraped, not processed
    PROCESSED = "processed"   # Processed but not matched
    MATCHED = "matched"       # Matched with at least one alert
    ARCHIVED = "archived"     # No longer active on marketplace
    ERROR = "error"           # Error processing the listing


class Listing(Base):
    """Model for a marketplace listing."""
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(String(255), unique=True, nullable=False, index=True)  # Original ID from marketplace
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=True)
    price_text = Column(String(128), nullable=True)  # Original price text (might include currency)
    location = Column(String(255), nullable=True)
    category = Column(String(255), nullable=True)
    url = Column(String(1024), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    scraped_at = Column(DateTime, nullable=False)  # When it was scraped from marketplace
    
    # Processing info
    search_term = Column(String(255), nullable=True)  # Search term used to find this listing
    status = Column(Enum(ListingStatus), default=ListingStatus.NEW, nullable=False)
    processed_at = Column(DateTime, nullable=True)  # When it was processed
    
    # Extracted and enriched data
    keywords = Column(JSON, nullable=True)  # Extracted keywords
    metadata = Column(JSON, nullable=True)  # Additional metadata
    
    # Relationships
    images = relationship("ListingImage", back_populates="listing", cascade="all, delete-orphan")
    alerts = relationship("Alert", secondary="listing_alerts", back_populates="listings")
    
    @hybrid_property
    def image_count(self) -> int:
        """Get the number of images for this listing."""
        return len(self.images) if self.images else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "listing_id": self.listing_id,
            "title": self.title,
            "description": self.description,
            "price": self.price,
            "price_text": self.price_text,
            "location": self.location,
            "category": self.category,
            "url": self.url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "search_term": self.search_term,
            "status": self.status.value if self.status else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "keywords": self.keywords,
            "metadata": self.metadata,
            "images": [img.url for img in self.images] if self.images else [],
            "image_count": self.image_count
        }
    
    @classmethod
    def from_raw_data(cls, data: Dict[str, Any]) -> "Listing":
        """
        Create a Listing model from raw scraped data.
        
        Args:
            data: Raw listing data from scraper
            
        Returns:
            Listing model instance
        """
        try:
            # Parse scraped_at timestamp
            if "scraped_at" in data and isinstance(data["scraped_at"], str):
                scraped_at = datetime.fromisoformat(data["scraped_at"])
            else:
                scraped_at = datetime.utcnow()
            
            # Extract basic fields
            listing = cls(
                listing_id=data.get("listing_id", f"unknown_{int(datetime.utcnow().timestamp())}"),
                title=data.get("title", "Unknown Title"),
                description=data.get("description", ""),
                price=data.get("price"),
                price_text=data.get("price_text"),
                location=data.get("location"),
                category=data.get("category"),
                url=data.get("url"),
                scraped_at=scraped_at,
                search_term=data.get("search_term"),
                status=ListingStatus.NEW
            )
            
            # Store any additional data as metadata
            metadata = {k: v for k, v in data.items() if k not in listing.to_dict()}
            if metadata:
                listing.metadata = metadata
            
            return listing
            
        except Exception as e:
            logger.error(f"Error creating listing from raw data: {str(e)}", 
                         extra={"data": str(data)[:200]}, 
                         exc_info=True)
            raise


class ListingImage(Base):
    """Model for a marketplace listing image."""
    __tablename__ = "listing_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(1024), nullable=False)
    position = Column(Integer, default=0, nullable=False)  # Order of images
    downloaded = Column(Boolean, default=False, nullable=False)  # Whether image has been downloaded
    local_path = Column(String(1024), nullable=True)  # Path to local copy if downloaded
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    listing = relationship("Listing", back_populates="images")


class SearchTerm(Base):
    """Model for search terms used to find listings."""
    __tablename__ = "search_terms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    term = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    total_listings_found = Column(Integer, default=0, nullable=False)


class Alert(Base):
    """Model for user alerts (notifications for specific types of listings)."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)  # Reference to user in auth system
    name = Column(String(255), nullable=False)
    search_query = Column(String(512), nullable=False)  # Search query for matching listings
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    location = Column(String(255), nullable=True)
    radius_miles = Column(Integer, nullable=True)
    categories = Column(JSON, nullable=True)  # List of categories
    keywords = Column(JSON, nullable=True)  # List of keywords to match
    
    # Notification settings
    notification_email = Column(String(255), nullable=True)
    notification_sms = Column(String(50), nullable=True)
    notify_immediately = Column(Boolean, default=True, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_matched_at = Column(DateTime, nullable=True)
    
    # Relationships
    listings = relationship("Listing", secondary="listing_alerts", back_populates="alerts")


# Association table for many-to-many relationship between listings and alerts
listing_alerts = Table(
    "listing_alerts",
    Base.metadata,
    Column("listing_id", Integer, ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True),
    Column("alert_id", Integer, ForeignKey("alerts.id", ondelete="CASCADE"), primary_key=True),
    Column("matched_at", DateTime, default=datetime.utcnow, nullable=False),
    Column("notified", Boolean, default=False, nullable=False),
    Column("notification_sent_at", DateTime, nullable=True)
)


class PriceAlert(Base):
    """Price alert model for marketplace listings."""
    
    __tablename__ = "price_alerts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    search_term = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    location = Column(String(255), nullable=True)
    notification_method = Column(Enum("email", "sms", "push", name="notification_methods"), default="email")
    notification_target = Column(String(255), nullable=False)  # Email address, phone number, etc.
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_triggered = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="alerts")
    
    def __repr__(self):
        """String representation of the alert."""
        price_range = ""
        if self.min_price is not None and self.max_price is not None:
            price_range = f"${self.min_price} - ${self.max_price}"
        elif self.min_price is not None:
            price_range = f">${self.min_price}"
        elif self.max_price is not None:
            price_range = f"<${self.max_price}"
            
        return f"<PriceAlert '{self.search_term or self.category}' {price_range}>"


class AlertHistory(Base):
    """History of triggered alerts."""
    
    __tablename__ = "alert_history"
    
    id = Column(Integer, primary_key=True)
    alert_id = Column(Integer, ForeignKey("price_alerts.id"), nullable=False)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    notification_sent = Column(Boolean, default=False)
    notification_time = Column(DateTime, nullable=True)
    
    # Relationships
    alert = relationship("PriceAlert")
    listing = relationship("Listing")
    
    def __repr__(self):
        """String representation of the alert history entry."""
        return f"<AlertHistory alert_id={self.alert_id} listing_id={self.listing_id}>" 