import pytest
from unittest.mock import Mock, patch
from src.pipeline.data_pipeline import MarketplacePipeline
from src.database.models import MarketplaceListing, ListingAnalysis

@pytest.fixture
def mock_scrapers():
    return {
        'dynamic_scraper': Mock(),
        'api_scraper': Mock(),
        'llm_scraper': Mock()
    }

@pytest.mark.asyncio
async def test_process_category_success(mock_scrapers):
    # Setup
    pipeline = MarketplacePipeline()
    pipeline.dynamic_scraper = mock_scrapers['dynamic_scraper']
    pipeline.api_scraper = mock_scrapers['api_scraper']
    pipeline.llm_scraper = mock_scrapers['llm_scraper']
    
    # Mock return values
    mock_scrapers['dynamic_scraper'].scrape_category.return_value = [
        {'url': 'test/1', 'title': 'Test Listing'}
    ]
    mock_scrapers['api_scraper'].enrich_listings.return_value = [
        {'url': 'test/1', 'title': 'Test Listing', 'description': 'Enriched'}
    ]
    mock_scrapers['llm_scraper'].process_listings.return_value = [
        {'url': 'test/1', 'title': 'Test Listing', 'description': 'Enriched', 
         'analysis': {'confidence': 0.9}}
    ]
    
    # Execute
    await pipeline.process_category('bikes')
    
    # Assert
    mock_scrapers['dynamic_scraper'].scrape_category.assert_called_once_with('bikes')
    mock_scrapers['api_scraper'].enrich_listings.assert_called_once()
    mock_scrapers['llm_scraper'].process_listings.assert_called_once()
