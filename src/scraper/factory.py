from typing import Dict, Type
from src.scraper.base_scraper import BaseScraper
from src.scraper.dynamic_scraper import DynamicScraper
from src.scraper.api_scraper import APIScraper
from src.scraper.static_scraper import StaticScraper
from src.scraper.llm_scraper import LLMScraper

class ScraperFactory:
    _scrapers: Dict[str, Type[BaseScraper]] = {
        'dynamic': DynamicScraper,
        'api': APIScraper,
        'static': StaticScraper,
        'llm': LLMScraper
    }

    @classmethod
    def get_scraper(cls, scraper_type: str) -> BaseScraper:
        if scraper_type not in cls._scrapers:
            raise ValueError(f"Unknown scraper type: {scraper_type}")
        return cls._scrapers[scraper_type]()