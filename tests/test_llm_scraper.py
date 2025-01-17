import pytest
from src.scraper.llm_scraper import LLMScraper

def test_llm_scraper_initialization():
    scraper = LLMScraper()
    assert scraper is not None
