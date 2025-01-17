import pytest
from src.scraper.factory import ScraperFactory

@pytest.fixture
def scraper_factory():
    return ScraperFactory()
