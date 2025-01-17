import random
import time
from typing import List, Optional
from urllib.parse import urljoin
import aiohttp
from bs4 import BeautifulSoup
from src.logging.logger import get_logger

logger = get_logger(__name__)

class ProxyRotator:
    def __init__(self, proxies: List[str]):
        self.proxies = proxies
        self.current_index = 0

    def get_next_proxy(self) -> str:
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy

class UserAgentRotator:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        ]

    def get_random_user_agent(self) -> str:
        return random.choice(self.user_agents)

class RequestThrottler:
    def __init__(self, requests_per_minute: int):
        self.min_interval = 60.0 / requests_per_minute
        self.last_request_time = 0

    async def throttle(self):
        """Throttle requests to respect rate limits"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_interval:
            delay = self.min_interval - time_since_last_request
            await asyncio.sleep(delay)
        
        self.last_request_time = time.time()

class HTMLParser:
    @staticmethod
    def extract_text(element: BeautifulSoup) -> str:
        """Extract clean text from HTML element"""
        if not element:
            return ""
        return element.get_text(strip=True)

    @staticmethod
    def extract_attribute(element: BeautifulSoup, attr: str) -> Optional[str]:
        """Extract attribute value from HTML element"""
        if not element:
            return None
        return element.get(attr)

    @staticmethod
    def make_absolute_url(base_url: str, relative_url: str) -> str:
        """Convert relative URL to absolute URL"""
        return urljoin(base_url, relative_url)
