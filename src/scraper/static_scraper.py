from src.scraper.base import BaseScraper
from src.logging.logger import log_execution_time
import aiohttp
from bs4 import BeautifulSoup

class StaticScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="static")
        
    @log_execution_time
    async def scrape_category(self, category: str):
        """Scrape listings using static HTML requests"""
        try:
            url = f"{self.base_url}/category/{category}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_html(html)
                    return []
                    
        except Exception as e:
            self.logger.error(f"Error in static scraping: {str(e)}")
            raise
            
    def _parse_html(self, html):
        """Parse HTML content for listings"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            listings = soup.select('[data-testid="marketplace_listing_item"]')
            
            return [self._parse_listing(listing) for listing in listings]
            
        except Exception as e:
            self.logger.error(f"Error parsing HTML: {str(e)}")
            return []
            
    def _parse_listing(self, element):
        """Parse individual listing HTML"""
        try:
            return {
                'title': element.select_one('h2').text.strip(),
                'price': element.select_one('[data-testid="price"]').text.strip(),
                'location': element.select_one('[data-testid="location"]').text.strip(),
                'url': element.select_one('a')['href']
            }
        except Exception as e:
            self.logger.error(f"Error parsing listing element: {str(e)}")
            return None
