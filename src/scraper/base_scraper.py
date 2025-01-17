from abc import ABC, abstractmethod
from src.logging.logger import get_logger
from src.scraper.utils import RequestThrottler
import asyncio
from typing import Optional, List

class BaseScraper(ABC):
    def __init__(self, name: str, requests_per_minute: int = 30):
        self.name = name
        self.logger = get_logger(f"scraper.{name}")
        self.base_url = "https://www.facebook.com/marketplace"
        self.throttler = RequestThrottler(requests_per_minute)
        
    @abstractmethod
    async def scrape_category(self, category: str) -> List[dict]:
        pass
        
    async def _make_request(self, url: str, retries: int = 3) -> Optional[str]:
        """Make request with retry logic and rate limiting"""
        for attempt in range(retries):
            try:
                await self.throttler.throttle()
                async with self.session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 429:  # Rate limited
                        wait_time = min(60 * (attempt + 1), 300)  # Max 5 minutes
                        self.logger.warning(f"Rate limited. Waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                    else:
                        self.logger.error(f"Request failed: {response.status}")
            except Exception as e:
                self.logger.error(f"Request error: {str(e)}")
                await asyncio.sleep(5 * (attempt + 1))
        return None 