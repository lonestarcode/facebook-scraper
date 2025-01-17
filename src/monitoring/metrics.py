from prometheus_client import Counter, Histogram

SCRAPE_COUNTER = Counter(
    'marketplace_scrape_total',
    'Total number of scraping operations',
    ['category', 'scraper_type']
)

SCRAPE_DURATION = Histogram(
    'marketplace_scrape_duration_seconds',
    'Time spent scraping marketplace listings',
    ['category', 'scraper_type']
)

PROCESSING_ERRORS = Counter(
    'marketplace_error_total',
    'Total number of errors',
    ['function', 'scraper_type', 'error_type']
)

# Listing metrics
LISTING_COUNTER = Counter(
    'marketplace_listings_total',
    'Total number of listings processed',
    ['category', 'status']
)
