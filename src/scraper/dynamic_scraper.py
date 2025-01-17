from src.scraper.base_scraper import BaseScraper
from playwright.async_api import async_playwright
from src.monitoring.metrics import SCRAPE_DURATION
import asyncio

class DynamicScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="dynamic")
        self.playwright = None
        self.browser = None
        
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
    async def scrape_category(self, category: str):
        try:
            page = await self.browser.new_page()
            await page.route("**/*", lambda route: route.continue_())
            
            with SCRAPE_DURATION.labels(category=category).time():
                await page.goto(f"{self.base_url}/category/{category}")
                await page.wait_for_selector("[data-testid='marketplace_listing_item']")
                
                # Scroll to load more items
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)
                
                listings = await page.query_selector_all("[data-testid='marketplace_listing_item']")
                return [await self._parse_listing(listing) for listing in listings]
                
        except Exception as e:
            self.logger.error(f"Error scraping category {category}: {str(e)}")
            raise
            
    async def _parse_listing(self, element):
        try:
            return {
                'title': await element.query_selector('h2').inner_text(),
                'price': await element.query_selector('[data-testid="price"]').inner_text(),
                'location': await element.query_selector('[data-testid="location"]').inner_text(),
                'url': await element.query_selector('a').get_attribute('href')
            }
        except Exception as e:
            self.logger.error(f"Error parsing listing: {str(e)}")
            return None
