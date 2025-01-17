from src.scraper.factory import ScraperFactory
from src.monitoring.metrics import SCRAPE_COUNTER, SCRAPE_DURATION, PROCESSING_ERRORS
from src.logging.logger import get_logger
from src.database.models import MarketplaceListing, ListingAnalysis
from src.pipeline.error_handler import with_error_handling
from src.database.session import get_db_session
from src.config.config_manager import ConfigManager
from src.websocket.listing_notifier import listing_notifier
import asyncio
from typing import List, Dict, Optional

logger = get_logger('pipeline')

class MarketplacePipeline:
    def __init__(self):
        self.config = ConfigManager()
        self.scraper_config = self.config.get_scraper_config()
        # Initialize all scraper types
        self.scraper_types = ['dynamic', 'api', 'static']
        self.scrapers = {
            scraper_type: ScraperFactory.get_scraper(scraper_type)
            for scraper_type in self.scraper_types
        }
        self.llm_scraper = ScraperFactory.get_scraper('llm')

    async def process_category(self, category: str) -> List[Dict]:
        """Try different scraping methods until one succeeds"""
        max_retries = self.scraper_config.get('max_retries', 3)
        last_error = None
        
        for scraper_type in self.scraper_types:
            logger.info(f"Attempting to scrape with {scraper_type} scraper")
            
            for attempt in range(max_retries):
                try:
                    async with self.scrapers[scraper_type] as scraper:
                        raw_listings = await scraper.scrape_category(category)
                        
                        if not raw_listings:
                            logger.warning(f"{scraper_type} scraper returned no listings")
                            continue
                            
                        # If we got listings, process them
                        enriched_listings = await self._enrich_listings(raw_listings)
                        processed_listings = await self._process_with_llm(enriched_listings)
                        
                        if processed_listings:
                            await self._store_listings(processed_listings)
                            SCRAPE_COUNTER.labels(
                                category=category,
                                scraper_type=scraper_type
                            ).inc()
                            return processed_listings
                            
                except Exception as e:
                    last_error = e
                    logger.error(f"Error with {scraper_type} scraper (attempt {attempt + 1}): {str(e)}")
                    PROCESSING_ERRORS.labels(
                        function='process_category',
                        scraper_type=scraper_type,
                        error_type=type(e).__name__
                    ).inc()
                    
                    if attempt < max_retries - 1:
                        wait_time = min(60 * (attempt + 1), 300)
                        logger.warning(f"Retrying {scraper_type} in {wait_time}s")
                        await asyncio.sleep(wait_time)
        
        # If we get here, all scrapers failed
        raise Exception(f"All scraping methods failed. Last error: {str(last_error)}")

    async def _enrich_listings(self, listings: List[Dict]) -> List[Dict]:
        """Attempt to enrich listings with API data"""
        try:
            return await self.scrapers['api'].enrich_listings(listings)
        except Exception as e:
            logger.warning(f"Enrichment failed: {str(e)}, continuing with raw listings")
            return listings

    async def _process_with_llm(self, listings: List[Dict]) -> List[Dict]:
        """Process listings with LLM, continue if it fails"""
        try:
            return await self.llm_scraper.process_listings(listings)
        except Exception as e:
            logger.warning(f"LLM processing failed: {str(e)}, continuing with unenriched listings")
            return listings

    async def _store_listings(self, listings):
        """Store processed listings and notify websocket clients"""
        async for session in get_db_session():
            try:
                for listing_data in listings:
                    # Create marketplace listing
                    listing = MarketplaceListing(
                        listing_id=listing_data['url'].split('/')[-1],
                        title=listing_data['title'],
                        price=float(listing_data['price'].replace('$', '')),
                        location=listing_data['location'],
                        listing_url=listing_data['url'],
                        category=listing_data.get('category', 'unknown'),
                        description=listing_data.get('description', ''),
                        seller_id=listing_data.get('seller_id'),
                        images=listing_data.get('images', [])
                    )
                    session.add(listing)
                    await session.flush()

                    # Create listing analysis
                    if 'analysis' in listing_data:
                        analysis = ListingAnalysis(
                            listing_id=listing.id,
                            quality_score=listing_data['analysis'].get('confidence', 0.0),
                            keywords=listing_data['analysis'].get('keywords', []),
                            category_confidence=listing_data['analysis'].get('category_confidence', 0.0)
                        )
                        session.add(analysis)

                await session.commit()
                
                # Add notification after successful storage
                try:
                    unique_categories = set(listing.get('category', 'unknown') for listing in listings)
                    for category in unique_categories:
                        await listing_notifier.broadcast_listings(category)
                except Exception as e:
                    logger.error(f"Error notifying websocket clients: {str(e)}")
                
                # Trigger notifications for new listing
                await self.notification_service.process_new_listing(listing, session)
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error storing listings: {str(e)}")
                raise