import pytest
from src.scraper.dynamic_scraper import DynamicScraper

def test_dynamic_scraper_initialization():
    scraper = DynamicScraper()
    assert scraper is not None
