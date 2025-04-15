"""API endpoints for marketplace listings."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from shared.models.schema import ListingSchema, PaginatedResponse
from shared.models.marketplace import Listing
from src.validation.listings import ListingFilterParams
from src.database.session import get_db

router = APIRouter()

@router.get("/", response_model=PaginatedResponse[ListingSchema])
async def get_listings(
    filters: ListingFilterParams = Depends(),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get marketplace listings with optional filters.
    
    Supports filtering by:
    - Category
    - Price range
    - Location
    - Keyword search
    - Date posted
    """
    # Calculate offset for pagination
    offset = (page - 1) * limit
    
    # Build query with filters
    query = db.query(Listing)
    
    # Apply filters if provided
    if filters.category:
        query = query.filter(Listing.category == filters.category)
    
    if filters.min_price is not None:
        query = query.filter(Listing.price >= filters.min_price)
    
    if filters.max_price is not None:
        query = query.filter(Listing.price <= filters.max_price)
        
    if filters.location:
        query = query.filter(Listing.location.ilike(f"%{filters.location}%"))
    
    if filters.search:
        query = query.filter(Listing.title.ilike(f"%{filters.search}%") | 
                             Listing.description.ilike(f"%{filters.search}%"))
    
    if filters.days_old is not None:
        from datetime import datetime, timedelta
        date_threshold = datetime.utcnow() - timedelta(days=filters.days_old)
        query = query.filter(Listing.listed_date >= date_threshold)
    
    # Execute count query
    total = query.count()
    
    # Apply pagination
    items = query.order_by(Listing.listed_date.desc()).offset(offset).limit(limit).all()
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        limit=limit
    )

@router.get("/{listing_id}", response_model=ListingSchema)
async def get_listing(
    listing_id: str = Path(..., description="The ID of the listing to retrieve"),
    db: Session = Depends(get_db)
):
    """Get a specific marketplace listing by ID."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    return listing

@router.get("/categories", response_model=List[str])
async def get_categories(db: Session = Depends(get_db)):
    """Get all available marketplace listing categories."""
    categories = db.query(Listing.category).distinct().all()
    return [category[0] for category in categories if category[0]] 