from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator, root_validator

class ListingBase(BaseModel):
    """Base model for listings with common fields."""
    listing_id: str = Field(..., description="External marketplace listing ID")
    title: str = Field(..., description="Title of the listing")
    description: Optional[str] = Field(None, description="Description of the listing")
    price: Optional[float] = Field(None, description="Price of the listing")
    price_text: Optional[str] = Field(None, description="Original price text")
    location: Optional[str] = Field(None, description="Location of the listing")
    category: Optional[str] = Field(None, description="Category of the listing")
    url: Optional[str] = Field(None, description="URL to the original listing")

class ListingCreate(ListingBase):
    """Model for creating a new listing."""
    scraped_at: Optional[datetime] = Field(None, description="When the listing was scraped")
    images: List[str] = Field(default_factory=list, description="List of image URLs")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    search_term: Optional[str] = Field(None, description="Search term used to find this listing")
    
    @validator('images')
    def validate_images(cls, v):
        """Validate image URLs."""
        if len(v) > 20:
            raise ValueError("Maximum of 20 images allowed")
        return v

class ListingUpdate(BaseModel):
    """Model for updating an existing listing."""
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    price_text: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "ignore"

class ListingImageResponse(BaseModel):
    """Response model for listing images."""
    id: int
    url: str
    position: int
    downloaded: bool
    local_path: Optional[str] = None
    created_at: datetime
    
    class Config:
        orm_mode = True

class ListingResponse(ListingBase):
    """Response model for listings."""
    id: int
    created_at: datetime
    updated_at: datetime
    scraped_at: datetime
    status: str
    processed_at: Optional[datetime] = None
    search_term: Optional[str] = None
    keywords: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    images: List[ListingImageResponse] = Field(default_factory=list)
    
    class Config:
        orm_mode = True

class ListingSearchParams(BaseModel):
    """Search parameters for listings."""
    search: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    location: Optional[str] = None
    category: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    skip: int = 0
    limit: int = 100

class PaginatedListingResponse(BaseModel):
    """Paginated response for listings."""
    items: List[ListingResponse]
    total: int
    page: int
    pages: int
    size: int 