import pytest
from src.scraper.api_scraper import APIScraper

def test_api_scraper_initialization():
    scraper = APIScraper()
    assert scraper is not None
