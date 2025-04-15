"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import List, Optional, Dict, Any, Generic, TypeVar
from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import validator

# Generic type for paginated responses
T = TypeVar('T')

class NotificationType(str, Enum):
    """Types of notifications that can be sent."""
    
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"
    PUSH = "push"

class ImageSchema(BaseModel):
    """Schema for an image."""
    
    url: HttpUrl
    alt: Optional[str] = None

class ListingAnalysisSchema(BaseModel):
    """Schema for listing analysis."""
    
    quality_score: float
    keywords: List[str]
    category_confidence: float
    sentiment_score: Optional[float] = None
    price_analysis: Optional[Dict[str, Any]] = None

class ListingSchema(BaseModel):
    """Schema for a marketplace listing."""
    
    id: UUID
    external_id: str
    title: str
    description: Optional[str] = None
    price: Optional[float] = None
    currency: str = "USD"
    location: Optional[str] = None
    seller_name: Optional[str] = None
    category: Optional[str] = None
    image_urls: Optional[List[str]] = None
    listing_url: str
    listed_date: Optional[datetime] = None
    scraped_date: datetime
    last_updated: datetime
    is_sold: bool = False
    is_deleted: bool = False
    metadata: Optional[Dict[str, Any]] = None
    source: str = "facebook"

class ListingCreateSchema(BaseModel):
    """Schema for creating a listing."""
    
    external_id: str
    title: str
    description: Optional[str] = None
    price: Optional[float] = None
    currency: str = "USD"
    location: Optional[str] = None
    seller_name: Optional[str] = None
    category: Optional[str] = None
    image_urls: Optional[List[str]] = None
    listing_url: str
    listed_date: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    source: str = "facebook"

    @validator('price')
    def price_must_be_positive(cls, v):
        """Validate that price is positive if provided."""
        if v is not None and v < 0:
            raise ValueError('Price must be positive')
        return v

class PriceAlertSchema(BaseModel):
    """Schema for a price alert."""
    
    search_term: Optional[str] = None
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    location: Optional[str] = None
    notification_method: str = "email"
    notification_target: str

    @validator('search_term', 'category')
    def validate_search_criteria(cls, v, values):
        """Validate that either search_term or category is provided."""
        if 'search_term' in values and not values['search_term'] and 'category' in values and not values['category'] and not v:
            raise ValueError('Either search_term or category must be provided')
        return v
    
    @validator('min_price', 'max_price')
    def validate_price(cls, v):
        """Validate that price is positive if provided."""
        if v is not None and v < 0:
            raise ValueError('Price must be positive')
        return v
    
    @validator('max_price')
    def validate_price_range(cls, v, values):
        """Validate that max_price is greater than min_price if both are provided."""
        if 'min_price' in values and values['min_price'] is not None and v is not None and v < values['min_price']:
            raise ValueError('max_price must be greater than min_price')
        return v
    
    @validator('notification_method')
    def validate_notification_method(cls, v):
        """Validate that notification_method is valid."""
        valid_methods = ["email", "sms", "push"]
        if v not in valid_methods:
            raise ValueError(f'notification_method must be one of {valid_methods}')
        return v

class AlertResponseSchema(PriceAlertSchema):
    """Alert response schema with additional fields."""
    
    id: int
    user_id: UUID
    is_active: bool = True
    created_at: datetime
    last_triggered: Optional[datetime] = None

class AlertHistorySchema(BaseModel):
    """Alert history schema."""
    
    id: int
    alert_id: int
    listing_id: UUID
    triggered_at: datetime
    notification_sent: bool
    notification_time: Optional[datetime] = None

class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response model.
    
    Contains:
    - List of items of type T
    - Total count of items
    - Current page number
    - Items per page (limit)
    """
    
    items: List[T]
    total: int
    page: int
    limit: int
    
    @property
    def pages(self) -> int:
        """Calculate total number of pages."""
        return (self.total + self.limit - 1) // self.limit if self.limit > 0 else 0
    
    class Config:
        """Pydantic model configuration."""
        
        from_attributes = True

class UserSchema(BaseModel):
    """User information schema."""
    
    id: UUID
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        """Pydantic model configuration."""
        
        from_attributes = True

class UserCreateSchema(BaseModel):
    """Schema for creating a new user."""
    
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class PriceAlertCreateSchema(BaseModel):
    """Schema for creating a price alert."""
    
    user_id: str
    category: Optional[str] = None
    max_price: float
    keywords: List[str] = Field(default_factory=list)
    notify_email: Optional[EmailStr] = None
    notify_webhook: Optional[HttpUrl] = None
    is_active: bool = True

class PriceAlertUpdateSchema(BaseModel):
    """Schema for updating a price alert."""
    
    category: Optional[str] = None
    max_price: Optional[float] = None
    keywords: Optional[List[str]] = None
    notify_email: Optional[EmailStr] = None
    notify_webhook: Optional[HttpUrl] = None
    is_active: Optional[bool] = None

class AlertNotificationSchema(BaseModel):
    """Schema for an alert notification."""
    
    id: int
    alert_id: int
    listing_id: int
    notification_type: NotificationType
    status: str
    delivery_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime 