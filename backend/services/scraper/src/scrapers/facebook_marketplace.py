"""Scraper for Facebook Marketplace listings."""

import json
import logging
import re
import time
import uuid
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger("scraper.facebook")

class FacebookMarketplaceScraper:
    """Scraper for Facebook Marketplace listings."""
    
    def __init__(
        self,
        user_agent: str,
        timeout: int = 30,
        max_retries: int = 3,
        proxy_url: Optional[str] = None
    ):
        """
        Initialize the Facebook Marketplace scraper.
        
        Args:
            user_agent: User agent string to use for requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            proxy_url: Optional proxy URL
        """
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self.proxy_url = proxy_url
        
        # Base URLs
        self.base_url = "https://www.facebook.com/marketplace"
        self.search_url = f"{self.base_url}/search"
        
        # Session will be initialized when needed
        self._session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_session()
    
    async def initialize_session(self):
        """Initialize the HTTP session."""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={
                    "User-Agent": self.user_agent,
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                }
            )
    
    async def close_session(self):
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def _make_request(self, url: str) -> str:
        """
        Make an HTTP request with retries.
        
        Args:
            url: URL to request
            
        Returns:
            Response text
            
        Raises:
            Exception: If the request fails after all retries
        """
        # Ensure session is initialized
        await self.initialize_session()
        
        # Retry logic
        for attempt in range(self.max_retries + 1):
            try:
                async with self._session.get(
                    url,
                    timeout=self.timeout,
                    proxy=self.proxy_url
                ) as response:
                    response.raise_for_status()
                    return await response.text()
            except aiohttp.ClientError as e:
                if attempt == self.max_retries:
                    logger.error(f"Failed to fetch {url} after {self.max_retries} attempts: {str(e)}")
                    raise
                
                # Exponential backoff
                wait_time = 2 ** attempt
                logger.warning(f"Request to {url} failed (attempt {attempt + 1}/{self.max_retries + 1}). Retrying in {wait_time} seconds")
                await asyncio.sleep(wait_time)
    
    async def get_listings_from_category(
        self,
        category: str,
        location: str,
        max_listings: int = 100
    ) -> List[str]:
        """
        Get listing URLs from a category page.
        
        Args:
            category: Category to scrape
            location: Location to search in
            max_listings: Maximum number of listings to return
            
        Returns:
            List of listing URLs
        """
        # Build the search URL
        search_params = []
        
        if category and category != "all":
            search_params.append(f"category={category}")
        
        if location:
            search_params.append(f"location={location}")
        
        search_url = self.search_url
        if search_params:
            search_url += "?" + "&".join(search_params)
        
        logger.info(f"Fetching listings from {search_url}")
        
        try:
            # Make the request
            html = await self._make_request(search_url)
            
            # Parse the HTML
            soup = BeautifulSoup(html, "html.parser")
            
            # Find all listing links
            listing_links = []
            
            # Facebook's HTML structure is complex and changes frequently
            # This is a simplified approach and may need updates
            for link in soup.find_all("a", href=True):
                href = link["href"]
                # Check if it's a marketplace item link
                if "/marketplace/item/" in href:
                    full_url = f"https://www.facebook.com{href}" if not href.startswith("http") else href
                    listing_links.append(full_url)
                    
                    if len(listing_links) >= max_listings:
                        break
            
            logger.info(f"Found {len(listing_links)} listings")
            return listing_links
        
        except Exception as e:
            logger.error(f"Error getting listings from category {category}: {str(e)}")
            return []
    
    async def scrape_listing(self, url: str) -> Dict[str, Any]:
        """
        Scrape a single marketplace listing.
        
        Args:
            url: URL of the listing to scrape
            
        Returns:
            Dictionary with listing data
            
        Raises:
            Exception: If the listing cannot be scraped
        """
        logger.info(f"Scraping listing: {url}")
        
        try:
            # Make the request
            html = await self._make_request(url)
            
            # Parse the HTML
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract listing ID from URL
            external_id = re.search(r"/item/([^/?]+)", url)
            external_id = external_id.group(1) if external_id else f"unknown-{uuid.uuid4()}"
            
            # Extract listing data
            title = self._extract_title(soup)
            price = self._extract_price(soup)
            description = self._extract_description(soup)
            location = self._extract_location(soup)
            seller_name = self._extract_seller_name(soup)
            category = self._extract_category(soup)
            image_urls = self._extract_image_urls(soup)
            listed_date = self._extract_listed_date(soup)
            
            # Create listing data structure
            listing_data = {
                "external_id": external_id,
                "title": title,
                "description": description,
                "price": price,
                "currency": "USD",  # Default to USD, could be extracted from the page
                "location": location,
                "seller_name": seller_name,
                "category": category,
                "image_urls": image_urls,
                "listing_url": url,
                "listed_date": listed_date.isoformat() if listed_date else None,
                "scraped_date": datetime.utcnow().isoformat(),
                "source": "facebook",
                "is_sold": False,
                "is_deleted": False,
                "metadata": {
                    "original_html": None,  # Don't store the full HTML for privacy/storage reasons
                    "scraper_version": "2.0.0"
                }
            }
            
            return listing_data
        
        except Exception as e:
            logger.error(f"Error scraping listing {url}: {str(e)}")
            raise
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the listing title from the soup."""
        # Find the title element (this selector may need updates)
        title_elem = soup.select_one("h1") or soup.select_one(".title")
        
        if title_elem:
            return title_elem.text.strip()
        
        # Fallback: look for og:title meta tag
        meta_title = soup.select_one('meta[property="og:title"]')
        if meta_title and meta_title.get("content"):
            return meta_title["content"].strip()
            
        return "Unknown Title"
    
    def _extract_price(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract the listing price from the soup."""
        # Find the price element
        price_elem = soup.select_one(".price") or soup.select_one('[data-testid="marketplace-item-price"]')
        
        if price_elem:
            price_text = price_elem.text.strip()
            # Extract numbers from the price
            price_match = re.search(r'[\$£€]?\s*([0-9,]+(?:\.[0-9]+)?)', price_text)
            if price_match:
                price_str = price_match.group(1).replace(',', '')
                try:
                    return float(price_str)
                except ValueError:
                    pass
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the listing description from the soup."""
        # Find the description element
        desc_elem = soup.select_one(".description") or soup.select_one('[data-testid="marketplace-item-description"]')
        
        if desc_elem:
            return desc_elem.text.strip()
            
        return None
    
    def _extract_location(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the listing location from the soup."""
        # Find the location element
        location_elem = soup.select_one(".location") or soup.select_one('[data-testid="marketplace-item-location"]')
        
        if location_elem:
            return location_elem.text.strip()
            
        return None
    
    def _extract_seller_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the seller name from the soup."""
        # Find the seller element
        seller_elem = soup.select_one(".seller") or soup.select_one('[data-testid="marketplace-item-seller"]')
        
        if seller_elem:
            return seller_elem.text.strip()
            
        return None
    
    def _extract_category(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the listing category from the soup."""
        # Find the category element
        category_elem = soup.select_one(".category") or soup.select_one('[data-testid="marketplace-item-category"]')
        
        if category_elem:
            return category_elem.text.strip()
            
        # Try to find breadcrumbs
        breadcrumbs = soup.select(".breadcrumb a")
        if breadcrumbs and len(breadcrumbs) > 1:
            return breadcrumbs[1].text.strip()
            
        return None
    
    def _extract_image_urls(self, soup: BeautifulSoup) -> List[str]:
        """Extract image URLs from the soup."""
        # Find all image elements
        image_urls = []
        
        # Check for image elements
        for img in soup.select("img"):
            if img.get("src") and "marketplace" in img.get("src", ""):
                image_urls.append(img["src"])
        
        # Check for JSON-LD data
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and "image" in data:
                    if isinstance(data["image"], list):
                        image_urls.extend(data["image"])
                    else:
                        image_urls.append(data["image"])
            except (json.JSONDecodeError, AttributeError):
                pass
        
        return image_urls
    
    def _extract_listed_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract the listed date from the soup."""
        # Find the date element
        date_elem = soup.select_one(".date") or soup.select_one('[data-testid="marketplace-item-date"]')
        
        if date_elem:
            date_text = date_elem.text.strip().lower()
            
            # Parse relative dates
            if "today" in date_text:
                return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            elif "yesterday" in date_text:
                return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            elif "days ago" in date_text:
                days_match = re.search(r'(\d+) days ago', date_text)
                if days_match:
                    days = int(days_match.group(1))
                    return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)
            elif "weeks ago" in date_text:
                weeks_match = re.search(r'(\d+) weeks ago', date_text)
                if weeks_match:
                    weeks = int(weeks_match.group(1))
                    return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=weeks*7)
            
            # Try standard date formats
            try:
                return datetime.strptime(date_text, "%b %d, %Y")
            except ValueError:
                pass
                
            try:
                return datetime.strptime(date_text, "%Y-%m-%d")
            except ValueError:
                pass
        
        # Fallback: metadata
        for meta in soup.select('meta[property="article:published_time"]'):
            if meta.get("content"):
                try:
                    return datetime.fromisoformat(meta["content"].replace("Z", "+00:00"))
                except ValueError:
                    pass
        
        return None 