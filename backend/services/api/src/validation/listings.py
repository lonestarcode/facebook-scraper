"""Validation models for marketplace listing API endpoints."""

from typing import Optional
from pydantic import BaseModel, Field, validator
from fastapi import Query


class ListingFilterParams(BaseModel):
    """
    Validation model for filtering marketplace listings.
    
    Used as a dependency in the listings router to validate and parse query parameters.
    """
    
    category: Optional[str] = Field(
        None, description="Filter listings by category"
    )
    
    min_price: Optional[float] = Field(
        None, description="Minimum price filter", ge=0
    )
    
    max_price: Optional[float] = Field(
        None, description="Maximum price filter", ge=0
    )
    
    location: Optional[str] = Field(
        None, description="Filter listings by location (partial match)"
    )
    
    search: Optional[str] = Field(
        None, description="Search term to match in title or description"
    )
    
    days_old: Optional[int] = Field(
        None, description="Only show listings newer than this many days", ge=0
    )

    @validator("max_price")
    def validate_price_range(cls, max_price, values):
        """Validate that max_price is greater than min_price if both are provided."""
        min_price = values.get("min_price")
        if min_price is not None and max_price is not None and max_price < min_price:
            raise ValueError("max_price must be greater than or equal to min_price")
        return max_price
    
    @validator("search")
    def validate_search_term(cls, search):
        """Validate search terms are reasonable length."""
        if search and len(search) < 2:
            raise ValueError("search term must be at least 2 characters")
        return search
    
    class Config:
        """Pydantic model configuration."""
        
        # Allow conversion from query parameters
        from_attributes = True


def get_listing_filters(
    category: Optional[str] = Query(None, description="Filter listings by category"),
    min_price: Optional[float] = Query(None, description="Minimum price filter", ge=0),
    max_price: Optional[float] = Query(None, description="Maximum price filter", ge=0),
    location: Optional[str] = Query(None, description="Filter listings by location"),
    search: Optional[str] = Query(None, description="Search term to match in title or description"),
    days_old: Optional[int] = Query(None, description="Only show listings newer than this many days", ge=0)
) -> ListingFilterParams:
    """
    Create a ListingFilterParams object from query parameters.
    
    This function can be used as a dependency in FastAPI routes.
    """
    return ListingFilterParams(
        category=category,
        min_price=min_price,
        max_price=max_price,
        location=location,
        search=search,
        days_old=days_old
    ) 