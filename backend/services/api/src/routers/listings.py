from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from shared.database.session import get_db_session
from shared.models.marketplace import Listing, ListingStatus
from shared.repositories.listing_repository import listing_repository
from shared.utils.logging_config import get_logger
from src.schemas.listing import (
    ListingResponse, 
    ListingCreate, 
    ListingUpdate, 
    ListingSearchParams,
    PaginatedListingResponse
)

router = APIRouter()
logger = get_logger(__name__)

@router.get("/", response_model=PaginatedListingResponse, summary="Get all listings")
async def get_listings(
    search: Optional[str] = Query(None, description="Search term for title and description"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    location: Optional[str] = Query(None, description="Location filter"),
    category: Optional[str] = Query(None, description="Category filter"),
    start_date: Optional[datetime] = Query(None, description="Start date for scraped_at"),
    end_date: Optional[datetime] = Query(None, description="End date for scraped_at"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
) -> PaginatedListingResponse:
    """
    Get all listings with pagination and optional filters.
    """
    try:
        # Search listings with filters
        listings, total_count = listing_repository.search_listings(
            search_term=search,
            min_price=min_price,
            max_price=max_price,
            location=location,
            category=category,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )
        
        # Convert to response models
        listing_responses = [ListingResponse.from_orm(listing) for listing in listings]
        
        return PaginatedListingResponse(
            items=listing_responses,
            total=total_count,
            page=skip // limit + 1 if limit > 0 else 1,
            pages=(total_count + limit - 1) // limit if limit > 0 else 1,
            size=len(listing_responses)
        )
    except Exception as e:
        logger.error(f"Error getting listings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/recent", response_model=List[ListingResponse], summary="Get recent listings")
async def get_recent_listings(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
    limit: int = Query(50, ge=1, le=100, description="Number of listings to return")
) -> List[ListingResponse]:
    """
    Get recent listings from the last N hours.
    """
    try:
        listings = listing_repository.get_recent_listings(hours=hours, limit=limit)
        return [ListingResponse.from_orm(listing) for listing in listings]
    except Exception as e:
        logger.error(f"Error getting recent listings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/categories", response_model=List[str], summary="Get all unique categories")
async def get_categories() -> List[str]:
    """
    Get all unique listing categories.
    """
    try:
        return listing_repository.get_categories()
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{listing_id}", response_model=ListingResponse, summary="Get listing by ID")
async def get_listing(
    listing_id: int = Path(..., description="ID of the listing to retrieve")
) -> ListingResponse:
    """
    Get a specific listing by its ID.
    """
    try:
        listing = listing_repository.get_by_id(listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail=f"Listing with ID {listing_id} not found")
        return ListingResponse.from_orm(listing)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting listing {listing_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/external/{external_id}", response_model=ListingResponse, summary="Get listing by external ID")
async def get_listing_by_external_id(
    external_id: str = Path(..., description="External ID of the listing")
) -> ListingResponse:
    """
    Get a specific listing by its external marketplace ID.
    """
    try:
        listing = listing_repository.get_by_listing_id(external_id)
        if not listing:
            raise HTTPException(status_code=404, detail=f"Listing with external ID {external_id} not found")
        return ListingResponse.from_orm(listing)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting listing with external ID {external_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/", response_model=ListingResponse, status_code=201, summary="Create a new listing")
async def create_listing(
    listing_data: ListingCreate
) -> ListingResponse:
    """
    Create a new listing.
    """
    try:
        # Check if listing already exists
        existing_listing = listing_repository.get_by_listing_id(listing_data.listing_id)
        if existing_listing:
            raise HTTPException(
                status_code=409, 
                detail=f"Listing with external ID {listing_data.listing_id} already exists"
            )
        
        # Create listing
        listing_dict = listing_data.dict()
        
        # Extract images
        image_urls = listing_dict.pop("images", [])
        
        # Set default values
        listing_dict["status"] = ListingStatus.NEW
        listing_dict["scraped_at"] = listing_dict.get("scraped_at") or datetime.utcnow()
        
        # Create with images
        listing = listing_repository.create_with_images(listing_dict, image_urls)
        return ListingResponse.from_orm(listing)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating listing: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/{listing_id}", response_model=ListingResponse, summary="Update a listing")
async def update_listing(
    listing_id: int,
    listing_data: ListingUpdate
) -> ListingResponse:
    """
    Update an existing listing.
    """
    try:
        # Check if listing exists
        existing_listing = listing_repository.get_by_id(listing_id)
        if not existing_listing:
            raise HTTPException(status_code=404, detail=f"Listing with ID {listing_id} not found")
        
        # Update listing
        listing_dict = listing_data.dict(exclude_unset=True)
        updated_listing = listing_repository.update(listing_id, listing_dict)
        return ListingResponse.from_orm(updated_listing)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating listing {listing_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/{listing_id}", status_code=204, summary="Delete a listing")
async def delete_listing(
    listing_id: int
) -> None:
    """
    Delete a listing by its ID.
    """
    try:
        # Check if listing exists
        existing_listing = listing_repository.get_by_id(listing_id)
        if not existing_listing:
            raise HTTPException(status_code=404, detail=f"Listing with ID {listing_id} not found")
        
        # Delete listing
        listing_repository.delete(listing_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting listing {listing_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/{listing_id}/archive", response_model=ListingResponse, summary="Archive a listing")
async def archive_listing(
    listing_id: int
) -> ListingResponse:
    """
    Archive a listing (mark as no longer active).
    """
    try:
        # Check if listing exists
        existing_listing = listing_repository.get_by_id(listing_id)
        if not existing_listing:
            raise HTTPException(status_code=404, detail=f"Listing with ID {listing_id} not found")
        
        # Update listing status
        success = listing_repository.update_status(listing_id, ListingStatus.ARCHIVED)
        if not success:
            raise HTTPException(status_code=404, detail=f"Listing with ID {listing_id} not found")
            
        # Return updated listing
        updated_listing = listing_repository.get_by_id(listing_id)
        return ListingResponse.from_orm(updated_listing)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving listing {listing_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 