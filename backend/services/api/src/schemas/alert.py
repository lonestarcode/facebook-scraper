from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator

class AlertBase(BaseModel):
    """Base model for alerts with common fields."""
    user_id: int = Field(..., description="User ID")
    name: str = Field(..., description="Name of the alert")
    search_query: str = Field(..., description="Search query for matching listings")
    min_price: Optional[float] = Field(None, description="Minimum price filter")
    max_price: Optional[float] = Field(None, description="Maximum price filter")
    location: Optional[str] = Field(None, description="Location filter")
    radius_miles: Optional[int] = Field(None, description="Search radius in miles")
    categories: Optional[List[str]] = Field(None, description="List of categories")
    keywords: Optional[List[str]] = Field(None, description="List of keywords to match")
    notification_email: Optional[str] = Field(None, description="Email for notifications")
    notification_sms: Optional[str] = Field(None, description="Phone number for SMS notifications")
    notify_immediately: bool = Field(True, description="Whether to notify immediately")

class AlertCreate(AlertBase):
    """Model for creating a new alert."""
    is_active: bool = Field(True, description="Whether the alert is active")
    
    @validator('name')
    def validate_name(cls, v):
        """Validate alert name."""
        if len(v) < 3:
            raise ValueError("Alert name must be at least 3 characters")
        return v
    
    @validator('search_query')
    def validate_search_query(cls, v):
        """Validate search query."""
        if len(v) < 2:
            raise ValueError("Search query must be at least 2 characters")
        return v
    
    @validator('notification_email')
    def validate_email(cls, v):
        """Validate email format."""
        if v is not None and "@" not in v:
            raise ValueError("Invalid email format")
        return v

class AlertUpdate(BaseModel):
    """Model for updating an existing alert."""
    name: Optional[str] = None
    search_query: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    location: Optional[str] = None
    radius_miles: Optional[int] = None
    categories: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    notification_email: Optional[str] = None
    notification_sms: Optional[str] = None
    notify_immediately: Optional[bool] = None
    is_active: Optional[bool] = None
    
    class Config:
        extra = "ignore"

class AlertResponse(AlertBase):
    """Response model for alerts."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_matched_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class PaginatedAlertResponse(BaseModel):
    """Paginated response for alerts."""
    items: List[AlertResponse]
    total: int
    page: int
    pages: int
    size: int 