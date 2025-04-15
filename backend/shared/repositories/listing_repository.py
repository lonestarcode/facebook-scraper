from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta

from sqlalchemy import select, update, delete, func, and_, or_, desc
from sqlalchemy.orm import Session, joinedload

from shared.database.session import get_db_session
from shared.models.marketplace import Listing, ListingStatus, ListingImage
from shared.repositories.base import BaseRepository
from shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class ListingRepository(BaseRepository[Listing]):
    """Repository for marketplace listings."""

    def __init__(self):
        """Initialize the repository with the Listing model."""
        super().__init__(Listing)
    
    def get_by_listing_id(self, listing_id: str, db_session: Optional[Session] = None) -> Optional[Listing]:
        """
        Get a listing by its external listing ID.
        
        Args:
            listing_id: External listing ID from marketplace
            db_session: Optional database session
            
        Returns:
            Listing if found, otherwise None
        """
        with db_session or get_db_session() as session:
            query = select(Listing).where(Listing.listing_id == listing_id)
            return session.execute(query).scalar_one_or_none()
    
    def create_with_images(
        self, 
        listing_data: Dict[str, Any], 
        image_urls: List[str], 
        db_session: Optional[Session] = None
    ) -> Listing:
        """
        Create a listing with its associated images.
        
        Args:
            listing_data: Listing data
            image_urls: List of image URLs
            db_session: Optional database session
            
        Returns:
            Created listing
        """
        with db_session or get_db_session() as session:
            # Create listing
            listing = Listing(**listing_data)
            session.add(listing)
            
            # Create images
            for index, url in enumerate(image_urls):
                image = ListingImage(
                    url=url,
                    position=index,
                    downloaded=False
                )
                listing.images.append(image)
                
            session.commit()
            session.refresh(listing)
            
            logger.info(f"Created listing with ID {listing.id} and {len(image_urls)} images")
            return listing
    
    def get_new_listings(
        self, 
        limit: int = 100, 
        db_session: Optional[Session] = None
    ) -> List[Listing]:
        """
        Get listings with NEW status for processing.
        
        Args:
            limit: Maximum number of listings to retrieve
            db_session: Optional database session
            
        Returns:
            List of new listings
        """
        with db_session or get_db_session() as session:
            query = (
                select(Listing)
                .where(Listing.status == ListingStatus.NEW)
                .order_by(Listing.created_at)
                .limit(limit)
            )
            return list(session.execute(query).scalars().all())
    
    def update_status(
        self, 
        listing_id: int, 
        status: ListingStatus, 
        db_session: Optional[Session] = None
    ) -> bool:
        """
        Update the status of a listing.
        
        Args:
            listing_id: ID of the listing
            status: New status
            db_session: Optional database session
            
        Returns:
            True if successful, False if listing not found
        """
        with db_session or get_db_session() as session:
            stmt = (
                update(Listing)
                .where(Listing.id == listing_id)
                .values(
                    status=status,
                    updated_at=datetime.utcnow(),
                    processed_at=datetime.utcnow() if status == ListingStatus.PROCESSED else None
                )
            )
            result = session.execute(stmt)
            session.commit()
            
            return result.rowcount > 0
    
    def search_listings(
        self,
        search_term: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        location: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
        db_session: Optional[Session] = None
    ) -> Tuple[List[Listing], int]:
        """
        Search listings with various filters.
        
        Args:
            search_term: Optional text to search in title and description
            min_price: Optional minimum price filter
            max_price: Optional maximum price filter
            location: Optional location filter
            category: Optional category filter
            start_date: Optional start date for scraped_at
            end_date: Optional end date for scraped_at
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            db_session: Optional database session
            
        Returns:
            Tuple of (list of listings, total count)
        """
        with db_session or get_db_session() as session:
            # Build filters
            filters = []
            
            if search_term:
                search_filters = []
                search_term = f"%{search_term}%"
                search_filters.append(Listing.title.ilike(search_term))
                search_filters.append(Listing.description.ilike(search_term))
                
                # Also check if we have keywords extracted
                if search_term.startswith("%") and search_term.endswith("%"):
                    clean_term = search_term[1:-1].lower()
                    # This is a simplistic approach - in production you'd use a proper JSON query
                    search_filters.append(Listing.keywords.cast(str).ilike(f"%{clean_term}%"))
                
                filters.append(or_(*search_filters))
            
            if min_price is not None:
                filters.append(Listing.price >= min_price)
            
            if max_price is not None:
                filters.append(Listing.price <= max_price)
            
            if location:
                filters.append(Listing.location.ilike(f"%{location}%"))
            
            if category:
                filters.append(Listing.category == category)
            
            if start_date:
                filters.append(Listing.scraped_at >= start_date)
            
            if end_date:
                filters.append(Listing.scraped_at <= end_date)
            
            # Non-deleted/archived listings only
            filters.append(Listing.status != ListingStatus.ARCHIVED)
            
            # Build query for results
            query = (
                select(Listing)
                .options(joinedload(Listing.images))
                .where(and_(*filters))
                .order_by(desc(Listing.scraped_at))
                .offset(skip)
                .limit(limit)
            )
            
            # Count query
            count_query = (
                select(func.count())
                .select_from(Listing)
                .where(and_(*filters))
            )
            
            # Execute queries
            listings = list(session.execute(query).scalars().all())
            total_count = session.execute(count_query).scalar() or 0
            
            return listings, total_count
    
    def get_recent_listings(
        self,
        hours: int = 24,
        limit: int = 50,
        db_session: Optional[Session] = None
    ) -> List[Listing]:
        """
        Get recent listings from the last N hours.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of listings to return
            db_session: Optional database session
            
        Returns:
            List of recent listings
        """
        with db_session or get_db_session() as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = (
                select(Listing)
                .options(joinedload(Listing.images))
                .where(Listing.scraped_at >= cutoff_time)
                .order_by(desc(Listing.scraped_at))
                .limit(limit)
            )
            
            return list(session.execute(query).scalars().all())
    
    def get_categories(self, db_session: Optional[Session] = None) -> List[str]:
        """
        Get all unique categories.
        
        Args:
            db_session: Optional database session
            
        Returns:
            List of unique categories
        """
        with db_session or get_db_session() as session:
            query = select(Listing.category).distinct()
            results = session.execute(query).scalars().all()
            return [cat for cat in results if cat]  # Filter out None values


# Singleton instance
listing_repository = ListingRepository() 