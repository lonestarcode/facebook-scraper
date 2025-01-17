import pytest
from src.scraper.static_scraper import StaticScraper

def test_static_scraper_initialization():
    scraper = StaticScraper()
    assert scraper is not None
