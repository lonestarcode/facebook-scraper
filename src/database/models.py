from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class MarketplaceListing(Base):
    __tablename__ = 'marketplace_listings'
    
    id = Column(Integer, primary_key=True)
    listing_id = Column(String(100), unique=True)
    title = Column(String(500))
    price = Column(Float)
    description = Column(Text)
    location = Column(String(200))
    category = Column(String(100))
    seller_id = Column(String(100))
    listing_url = Column(String(1000))
    images = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class ListingAnalysis(Base):
    __tablename__ = 'listing_analyses'
    
    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey('marketplace_listings.id'))
    quality_score = Column(Float)
    keywords = Column(JSON)
    category_confidence = Column(Float)
    analyzed_at = Column(DateTime, default=datetime.utcnow)

class PriceAlert(Base):
    __tablename__ = 'price_alerts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100))  # For future user management
    category = Column(String(100))
    max_price = Column(Float)
    keywords = Column(JSON)
    notify_email = Column(String(255))
    notify_webhook = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class AlertNotification(Base):
    __tablename__ = 'alert_notifications'
    
    id = Column(Integer, primary_key=True)
    alert_id = Column(Integer, ForeignKey('price_alerts.id'))
    listing_id = Column(Integer, ForeignKey('marketplace_listings.id'))
    sent_at = Column(DateTime, default=datetime.utcnow)
    notification_type = Column(String(50))  # email, webhook, etc.