from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.session import get_db_session
from src.database.models import MarketplaceListing, ListingAnalysis
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import or_

router = APIRouter()

@router.get("/listings/")
async def get_listings(
    category: Optional[str] = None,
    hours: Optional[int] = 24,
    session: AsyncSession = Depends(get_db_session)
):
    """Get marketplace listings with optional filtering"""
    try:
        query = session.query(MarketplaceListing)
        
        if category:
            query = query.filter(MarketplaceListing.category == category)
            
        if hours:
            time_threshold = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(MarketplaceListing.created_at >= time_threshold)
            
        return await query.all()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/listings/{listing_id}/analysis")
async def get_listing_analysis(
    listing_id: int,
    session: AsyncSession = Depends(get_db_session)
):
    """Get analysis for a specific listing"""
    try:
        analysis = await session.query(ListingAnalysis)\
            .filter(ListingAnalysis.listing_id == listing_id)\
            .first()
            
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
            
        return analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/listings/newest")
async def get_newest_listings(
    category: Optional[str] = None,
    max_age_hours: Optional[int] = 24,
    limit: int = 50,
    session: AsyncSession = Depends(get_db_session)
):
    """Get newest listings with age information"""
    try:
        query = session.query(MarketplaceListing)\
            .order_by(MarketplaceListing.created_at.desc())
        
        if category:
            query = query.filter(MarketplaceListing.category == category)
            
        if max_age_hours:
            time_threshold = datetime.utcnow() - timedelta(hours=max_age_hours)
            query = query.filter(MarketplaceListing.created_at >= time_threshold)
            
        listings = await query.limit(limit).all()
        
        # Add age information
        now = datetime.utcnow()
        result = []
        for listing in listings:
            age_hours = (now - listing.created_at).total_seconds() / 3600
            result.append({
                "id": listing.id,
                "title": listing.title,
                "price": listing.price,
                "location": listing.location,
                "url": listing.listing_url,
                "created_at": listing.created_at.isoformat(),
                "age_hours": round(age_hours, 1),
                "age_display": _format_age(age_hours)
            })
            
        return result
        
    except Exception as e:
        logger.error(f"Error fetching newest listings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/listings/by-age")
async def get_listings_by_age(
    category: Optional[str] = None,
    max_age_hours: Optional[int] = None,
    min_age_hours: Optional[int] = None,
    sort_order: str = "newest",  # "newest" or "oldest"
    limit: int = 50,
    session: AsyncSession = Depends(get_db_session)
):
    """Get listings sorted by age with flexible filtering"""
    try:
        query = session.query(MarketplaceListing)
        
        # Apply category filter
        if category:
            query = query.filter(MarketplaceListing.category == category)
        
        # Apply age filters
        now = datetime.utcnow()
        if max_age_hours:
            max_age = now - timedelta(hours=max_age_hours)
            query = query.filter(MarketplaceListing.created_at >= max_age)
            
        if min_age_hours:
            min_age = now - timedelta(hours=min_age_hours)
            query = query.filter(MarketplaceListing.created_at <= min_age)
        
        # Apply sorting
        if sort_order == "newest":
            query = query.order_by(MarketplaceListing.created_at.desc())
        else:
            query = query.order_by(MarketplaceListing.created_at.asc())
        
        listings = await query.limit(limit).all()
        
        # Add age information to response
        result = []
        for listing in listings:
            age_hours = (now - listing.created_at).total_seconds() / 3600
            result.append({
                "id": listing.id,
                "title": listing.title,
                "price": listing.price,
                "location": listing.location,
                "url": listing.listing_url,
                "created_at": listing.created_at.isoformat(),
                "age_hours": round(age_hours, 1),
                "age_display": self._format_age(age_hours)
            })
            
        return result
        
    except Exception as e:
        logger.error(f"Error fetching age-sorted listings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
    def _format_age(self, age_hours: float) -> str:
        """Format age in a human-readable way"""
        if age_hours < 1:
            minutes = int(age_hours * 60)
            return f"{minutes} minutes old"
        elif age_hours < 24:
            hours = int(age_hours)
            return f"{hours} hours old"
        else:
            days = int(age_hours / 24)
            return f"{days} days old"

@router.get("/listings/search")
async def search_listings(
    keywords: Optional[str] = None,
    category: Optional[str] = None,
    max_price: Optional[float] = None,
    min_price: Optional[float] = None,
    location: Optional[str] = None,
    hours: Optional[int] = 24,
    limit: int = 50,
    session: AsyncSession = Depends(get_db_session)
):
    """Search listings with flexible filtering"""
    try:
        query = session.query(MarketplaceListing)
        
        # Apply keyword search if provided
        if keywords:
            search_terms = [term.strip().lower() for term in keywords.split(',')]
            keyword_filters = [
                or_(
                    MarketplaceListing.title.ilike(f"%{term}%"),
                    MarketplaceListing.description.ilike(f"%{term}%")
                )
                for term in search_terms
            ]
            query = query.filter(or_(*keyword_filters))
        
        # Apply optional filters
        if category:
            query = query.filter(MarketplaceListing.category == category)
        if max_price:
            query = query.filter(MarketplaceListing.price <= max_price)
        if min_price:
            query = query.filter(MarketplaceListing.price >= min_price)
        if location:
            query = query.filter(MarketplaceListing.location.ilike(f"%{location}%"))
        if hours:
            time_threshold = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(MarketplaceListing.created_at >= time_threshold)
            
        query = query.order_by(MarketplaceListing.created_at.desc())
        listings = await query.limit(limit).all()
        
        return listings
        
    except Exception as e:
        logger.error(f"Error searching listings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
