"""Main entry point for the scraper service."""

import asyncio
import logging
import signal
import sys
import time
import os
import json
import random
from typing import List, Dict, Any, Optional
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import threading

from shared.config.settings import get_settings, Settings
from shared.utils.kafka import get_kafka_client, kafka_producer
from shared.models.marketplace import Listing
from src.scrapers.facebook_marketplace import FacebookMarketplaceScraper
from src.utils.rate_limiter import RateLimiter
from shared.utils.logging_config import configure_logging, get_logger
from shared.utils.kafka import KafkaProducer

# Import health setup
from src.health_setup import setup_health_checks, create_health_check

# Create FastAPI app for health checks
from fastapi import FastAPI
app = FastAPI(
    title="Facebook Marketplace Scraper Service",
    description="Service for scraping Facebook Marketplace listings",
    version="2.0.0",
)

# Set up health checks
health_check = setup_health_checks(app)

# Get settings
settings = get_settings("scraper")

# Configure logging
configure_logging(service_name="scraper-service")
logger = get_logger(__name__)

# Rate limiter to avoid overloading the target website
rate_limiter = RateLimiter(
    requests_per_second=settings.scraper.rate_limit
)

# Create Kafka client
kafka_client = get_kafka_client("scraper")

# Flag to indicate if the service is running
running = True

def handle_shutdown(sig, frame):
    """Handle shutdown signals."""
    global running
    logger.info(f"Received shutdown signal {sig}")
    running = False

async def scrape_listing(scraper: FacebookMarketplaceScraper, listing_url: str) -> Optional[Dict[str, Any]]:
    """
    Scrape a single listing from the marketplace.
    
    Args:
        scraper: Initialized scraper instance
        listing_url: URL of the listing to scrape
    
    Returns:
        Listing data or None if failed
    """
    # Wait for rate limiter
    await rate_limiter.wait()
    
    try:
        # Scrape the listing
        listing_data = await scraper.scrape_listing(listing_url)
        logger.info(f"Scraped listing: {listing_data['title']}")
        return listing_data
    except Exception as e:
        logger.error(f"Error scraping listing {listing_url}: {str(e)}")
        return None

async def scrape_category(scraper: FacebookMarketplaceScraper, category: str, location: str, max_listings: int = 100) -> List[Dict[str, Any]]:
    """
    Scrape listings from a specific category in the marketplace.
    
    Args:
        scraper: Initialized scraper instance
        category: Category to scrape (e.g., "furniture", "electronics")
        location: Location to search in
        max_listings: Maximum number of listings to scrape
    
    Returns:
        List of scraped listings
    """
    logger.info(f"Scraping category {category} in {location}")
    
    # Wait for rate limiter
    await rate_limiter.wait()
    
    try:
        # Get listing URLs from category page
        listing_urls = await scraper.get_listings_from_category(category, location, max_listings)
        logger.info(f"Found {len(listing_urls)} listings in category {category}")
        
        # Scrape each listing
        listings = []
        for url in listing_urls:
            listing_data = await scrape_listing(scraper, url)
            if listing_data:
                listings.append(listing_data)
                
                # Publish to Kafka
                with kafka_producer("scraper") as producer:
                    producer.publish_event(
                        topic="marketplace.listing.discovered",
                        key=listing_data["external_id"],
                        value=listing_data
                    )
        
        return listings
    except Exception as e:
        logger.error(f"Error scraping category {category}: {str(e)}")
        return []

async def process_scrape_request(category: str, location: str, max_listings: int = 100) -> None:
    """
    Process a scrape request for a specific category and location.
    
    Args:
        category: Category to scrape
        location: Location to search in
        max_listings: Maximum number of listings to scrape
    """
    # Initialize scraper
    scraper = FacebookMarketplaceScraper(
        user_agent=settings.scraper.user_agent,
        timeout=settings.scraper.request_timeout,
        max_retries=settings.scraper.max_retries,
        proxy_url=settings.scraper.proxy_url
    )
    
    # Scrape the category
    await scrape_category(scraper, category, location, max_listings)

async def listen_for_scrape_requests() -> None:
    """
    Listen for scrape requests from Kafka.
    
    A scrape request should contain:
    - category: Category to scrape
    - location: Location to search in
    - max_listings: Maximum number of listings to scrape
    """
    logger.info("Starting to listen for scrape requests")
    
    # Subscribe to the scrape request topic
    topic = "marketplace.scrape.request"
    
    async for message in kafka_client.consume_async([topic]):
        try:
            # Parse the message
            key = message.key().decode('utf-8') if message.key() else None
            value = message.value()
            
            if not value:
                logger.warning(f"Received empty scrape request, skipping")
                continue
            
            # Parse the request
            import json
            request = json.loads(value)
            
            # Extract request parameters
            category = request.get("category", "all")
            location = request.get("location", "")
            max_listings = request.get("max_listings", 100)
            
            logger.info(f"Received scrape request for category {category} in {location}")
            
            # Process the request
            await process_scrape_request(category, location, max_listings)
            
        except Exception as e:
            logger.error(f"Error processing scrape request: {str(e)}")
        
        # Check if we should continue running
        if not running:
            break

async def run_scheduled_scrapes() -> None:
    """Run scheduled scrapes based on configuration."""
    logger.info("Starting scheduled scrapes")
    
    # Get categories to scrape
    categories = settings.scraper.categories.split(",")
    if categories == ["*"]:
        categories = ["all"]  # Default to all categories
    
    # We could make this more configurable in the future
    locations = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]
    
    while running:
        for category in categories:
            for location in locations:
                if not running:
                    break
                
                logger.info(f"Running scheduled scrape for {category} in {location}")
                await process_scrape_request(category, location, 50)
            
            if not running:
                break
        
        # Wait for next cycle if still running
        if running:
            logger.info("Completed scrape cycle, waiting for next cycle")
            await asyncio.sleep(3600)  # 1 hour between full scrapes

async def main() -> None:
    """Main entry point for the scraper service."""
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Ensure Kafka topics exist
    kafka_client.ensure_topics_exist([
        "marketplace.scrape.request",
        "marketplace.listing.discovered"
    ])
    
    # Update health check status for critical components
    try:
        # Try to connect to the database and update health status
        # This is a placeholder - replace with actual DB connection
        # db = connect_to_database()
        health_check.set_status("database", True)
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
    
    try:
        # Test browser engine availability
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)
        driver.quit()
        health_check.set_status("browser-engine", True)
        logger.info("Browser engine is available")
    except Exception as e:
        logger.error(f"Browser engine error: {str(e)}")
        health_check.set_status("browser-engine", False)
    
    try:
        # Check Kafka producer connectivity
        producer = KafkaProducer(bootstrap_servers=settings.kafka.bootstrap_servers)
        producer.flush()
        health_check.set_status("kafka-producer", True)
        logger.info("Kafka producer connected")
    except Exception as e:
        logger.error(f"Kafka producer connection failed: {str(e)}")
    
    # Start the request listener and scheduled scrapes
    tasks = [
        asyncio.create_task(listen_for_scrape_requests()),
        asyncio.create_task(run_scheduled_scrapes())
    ]
    
    # Wait for tasks to complete
    await asyncio.gather(*tasks, return_exceptions=True)
    
    logger.info("Scraper service shutting down")

class MarketplaceScraper:
    """Scraper for Facebook Marketplace listings."""
    
    def __init__(self, settings: Settings):
        """Initialize the scraper with configuration settings."""
        self.settings = settings
        
        # Initialize Kafka producer
        self.producer = KafkaProducer(
            bootstrap_servers=settings.kafka.bootstrap_servers,
            topic=settings.kafka.topics.raw_listings
        )
        
        # Configure browser
        self.browser_options = self._setup_browser_options()
        
        # Initialize health check
        self.health_check = health_check
        
        logger.info("Marketplace scraper initialized")
        
    def _setup_browser_options(self) -> Options:
        """Configure Chrome options for scraping."""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"user-agent={self.settings.scraper.user_agent}")
        
        return options
    
    def run(self) -> None:
        """Run the scraper service."""
        logger.info("Starting scraper service")
        
        # Check browser availability for health check
        try:
            driver = webdriver.Chrome(options=self.browser_options)
            driver.quit()
            self.health_check.set_status("browser-engine", True)
        except Exception as e:
            logger.error(f"Browser engine error: {str(e)}")
            self.health_check.set_status("browser-engine", False)
        
        try:
            # Main scraping loop
            while True:
                search_terms = self.settings.scraper.categories.split(",")
                
                for term in search_terms:
                    try:
                        driver = webdriver.Chrome(options=self.browser_options)
                        listings = self._scrape_listings(driver, term)
                        
                        # Publish to Kafka
                        for listing in listings:
                            self._publish_listing(listing)
                            
                    except Exception as e:
                        logger.error(f"Error scraping term '{term}': {str(e)}")
                    finally:
                        # Always close the browser
                        try:
                            driver.quit()
                        except:
                            pass
                
                # Sleep between scraping cycles
                sleep_time = self.settings.scraper.scrape_interval_seconds
                logger.info(f"Completed scraping cycle, sleeping for {sleep_time} seconds")
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Scraper interrupted by user")
        except Exception as e:
            logger.error(f"Unhandled exception in scraper: {str(e)}", exc_info=True)
            self.health_check.set_status("service", False)

# Run the FastAPI app for health checks in a separate thread
def run_health_server():
    """Run the FastAPI app for health checks."""
    import uvicorn
    port = int(os.getenv("HEALTH_PORT", "8080"))
    logger.info(f"Starting health check server on port {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="error"
    )

def main() -> None:
    """Main entry point for the scraper service."""
    # Load settings
    settings = Settings()
    
    # Start health check server in a separate thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Initialize and run the scraper
    scraper = MarketplaceScraper(settings)
    scraper.run()

if __name__ == "__main__":
    try:
        # Run asyncio main
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scraper service stopped by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1)