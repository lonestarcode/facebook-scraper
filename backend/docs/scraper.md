# Facebook Marketplace Scraper Documentation

## Overview

The Facebook Marketplace Scraper is a microservice-based system designed to extract listing data from Facebook Marketplace for analysis and monitoring. This document outlines the architecture, implementation details, and usage of the scraper service.

## Architecture

The scraper is implemented as a dedicated microservice in the backend architecture with the following components:

1. **Core Scraper Engine**: Handles the extraction of data from Facebook Marketplace
2. **Anti-Detection Strategies**: Implements techniques to avoid blocking
3. **Parser Modules**: Extract structured data from raw HTML
4. **Scheduling System**: Manages periodic scraping tasks
5. **Health Monitoring**: Provides health status of the scraper service

## Implementation

### Core Components

The scraper is implemented in the `backend/services/scraper/src` directory with the following structure:

```
scraper/
├── src/
│   ├── main.py                 # Service entry point
│   ├── health_setup.py         # Health check implementation
│   ├── scrapers/               # Scraper implementations
│   │   ├── facebook_marketplace.py  # Facebook marketplace implementation
│   │   └── base.py                  # Base scraper class
│   ├── anti_detection/         # Anti-detection strategies
│   │   ├── rotate_user_agent.py     # User agent rotation
│   │   ├── proxy_manager.py         # Proxy management
│   │   └── request_throttling.py    # Request throttling
│   ├── parsers/                # Data extraction
│   │   ├── listing_parser.py        # Listing data parser
│   │   └── search_parser.py         # Search results parser
│   ├── scheduling/             # Task scheduling
│   │   ├── scheduler.py             # Task scheduler
│   │   └── tasks.py                 # Task definitions
│   └── utils/                  # Utility functions
│       ├── http.py                  # HTTP utilities
│       └── logging.py               # Logging utilities
├── tests/                      # Test suite
└── requirements.txt            # Dependencies
```

### Scraper Implementation

The Facebook Marketplace scraper is implemented as a class that handles various aspects of scraping:

```python
class FacebookMarketplaceScraper:
    def __init__(self, config: Dict[str, Any]):
        self.session = aiohttp.ClientSession()
        self.config = config
        self.proxy_manager = ProxyManager(config.get("proxies", []))
        self.user_agent_rotator = UserAgentRotator()
        self.logger = logging.getLogger("scraper.facebook")
        self.throttler = RequestThrottler(
            min_delay=config.get("min_request_delay", 2.0),
            max_delay=config.get("max_request_delay", 5.0)
        )
        
    async def search_listings(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for listings with the given parameters"""
        url = self._build_search_url(search_params)
        html = await self._make_request(url)
        
        if not html:
            return []
            
        parser = SearchResultsParser()
        listings = parser.extract_listings(html)
        
        return listings
        
    async def get_listing_details(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific listing"""
        url = f"https://www.facebook.com/marketplace/item/{listing_id}"
        html = await self._make_request(url)
        
        if not html:
            return None
            
        parser = ListingDetailsParser()
        details = parser.extract_details(html)
        
        return details
        
    async def _make_request(self, url: str) -> Optional[str]:
        """Make an HTTP request with anti-detection measures"""
        headers = {
            "User-Agent": self.user_agent_rotator.get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.facebook.com/marketplace/",
            "DNT": "1",
        }
        
        proxy = self.proxy_manager.get_next_proxy()
        
        # Apply request throttling
        await self.throttler.throttle()
        
        try:
            async with self.session.get(
                url, 
                headers=headers,
                proxy=proxy,
                timeout=30
            ) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    self.logger.error(
                        f"Failed to fetch {url}, status: {response.status}"
                    )
                    return None
        except Exception as e:
            self.logger.exception(f"Error fetching {url}: {str(e)}")
            return None
            
    def _build_search_url(self, params: Dict[str, Any]) -> str:
        """Build a search URL from parameters"""
        base_url = "https://www.facebook.com/marketplace/search"
        query_params = []
        
        if "query" in params:
            query_params.append(f"query={urllib.parse.quote(params['query'])}")
            
        if "location" in params:
            query_params.append(f"location={urllib.parse.quote(params['location'])}")
            
        if "distance" in params:
            query_params.append(f"distance={params['distance']}")
            
        if "min_price" in params:
            query_params.append(f"minPrice={params['min_price']}")
            
        if "max_price" in params:
            query_params.append(f"maxPrice={params['max_price']}")
            
        return f"{base_url}?{'&'.join(query_params)}"
        
    async def close(self):
        """Close the session"""
        await self.session.close()
```

### Anti-Detection Strategies

To avoid being blocked by Facebook, the scraper uses several anti-detection strategies:

1. **User Agent Rotation**:
   ```python
   class UserAgentRotator:
       def __init__(self):
           self.user_agents = [
               # Common browser user agents
               "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
               "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
               # More user agents...
           ]
           
       def get_random_user_agent(self) -> str:
           return random.choice(self.user_agents)
   ```

2. **Proxy Management**:
   ```python
   class ProxyManager:
       def __init__(self, proxies: List[str]):
           self.proxies = proxies
           self.current_index = 0
           
       def get_next_proxy(self) -> Optional[str]:
           if not self.proxies:
               return None
               
           proxy = self.proxies[self.current_index]
           self.current_index = (self.current_index + 1) % len(self.proxies)
           return proxy
   ```

3. **Request Throttling**:
   ```python
   class RequestThrottler:
       def __init__(self, min_delay: float = 2.0, max_delay: float = 5.0):
           self.min_delay = min_delay
           self.max_delay = max_delay
           self.last_request_time = 0
           
       async def throttle(self):
           """Throttle requests to avoid detection"""
           now = time.time()
           
           if self.last_request_time > 0:
               elapsed = now - self.last_request_time
               delay = random.uniform(self.min_delay, self.max_delay)
               
               if elapsed < delay:
                   await asyncio.sleep(delay - elapsed)
                   
           self.last_request_time = time.time()
   ```

### Data Parsing

The scraper extracts structured data from HTML using parser modules:

```python
class SearchResultsParser:
    def extract_listings(self, html: str) -> List[Dict[str, Any]]:
        """Extract listings from search results HTML"""
        try:
            soup = BeautifulSoup(html, "html.parser")
            listings = []
            
            # Find listing containers
            containers = soup.select("div[data-testid='marketplace_search_feed_listing']")
            
            for container in containers:
                listing = {}
                
                # Extract listing ID
                listing_link = container.select_one("a[href*='/marketplace/item/']")
                if listing_link:
                    href = listing_link.get("href", "")
                    listing_id_match = re.search(r"/item/(\d+)", href)
                    if listing_id_match:
                        listing["id"] = listing_id_match.group(1)
                
                # Extract title
                title_elem = container.select_one("span[dir='auto']")
                if title_elem:
                    listing["title"] = title_elem.text.strip()
                
                # Extract price
                price_elem = container.select_one("span:contains('$')")
                if price_elem:
                    price_text = price_elem.text.strip()
                    listing["price"] = price_text
                
                # Extract location
                location_elem = container.select_one("span:contains('in')")
                if location_elem:
                    listing["location"] = location_elem.text.replace("in ", "").strip()
                
                # Extract thumbnail
                img_elem = container.select_one("img")
                if img_elem:
                    listing["thumbnail"] = img_elem.get("src", "")
                
                if "id" in listing and "title" in listing:
                    listings.append(listing)
            
            return listings
        except Exception as e:
            logging.exception(f"Error parsing search results: {str(e)}")
            return []
```

## Scheduling

The scraper uses a task scheduler to manage periodic scraping jobs:

```python
class ScraperScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.logger = logging.getLogger("scraper.scheduler")
        
    def start(self):
        """Start the scheduler"""
        self.scheduler.start()
        self.logger.info("Scheduler started")
        
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        self.logger.info("Scheduler stopped")
        
    def add_job(self, job_id: str, func: Callable, **kwargs):
        """Add a job to the scheduler"""
        self.scheduler.add_job(
            func,
            id=job_id,
            **kwargs
        )
        self.logger.info(f"Added job {job_id}")
        
    def remove_job(self, job_id: str):
        """Remove a job from the scheduler"""
        self.scheduler.remove_job(job_id)
        self.logger.info(f"Removed job {job_id}")
```

## Usage

### Starting the Scraper Service

The scraper service can be started using the following command:

```bash
python -m backend.services.scraper.src.main --host 0.0.0.0 --port 8081
```

### API Endpoints

The scraper service exposes RESTful API endpoints for on-demand scraping:

- `POST /api/v1/scrape/search`: Search for listings with specified parameters
- `POST /api/v1/scrape/listing/{listing_id}`: Get details for a specific listing
- `GET /api/v1/scheduler/jobs`: List currently scheduled jobs
- `POST /api/v1/scheduler/job`: Create a new scheduled scraping job
- `DELETE /api/v1/scheduler/job/{job_id}`: Remove a scheduled job

### Health Check Endpoints

- `GET /health`: Service health status
- `GET /health/ready`: Service readiness status
- `GET /health/live`: Service liveness status

## Configuration

The scraper service is configured using environment variables or a configuration file:

```yaml
# Scraper Configuration
scraper:
  # Request settings
  min_request_delay: 2.0
  max_request_delay: 5.0
  request_timeout: 30
  
  # Proxy configuration
  proxies:
    - http://proxy1.example.com:8080
    - http://proxy2.example.com:8080
  
  # Search parameters
  default_search_radius: 40
  default_location: "New York, NY"
  
  # Rate limits
  max_requests_per_minute: 10
  max_requests_per_hour: 100
  
  # Anti-detection
  rotate_user_agents: true
  randomize_request_intervals: true
```

## Error Handling

The scraper implements robust error handling to manage various failure scenarios:

1. **Network Errors**: Automatic retry with exponential backoff
2. **Parsing Errors**: Graceful degradation with partial data return
3. **Rate Limiting**: Detection and automatic pause
4. **Service Errors**: Proactive health reporting

## Monitoring

The scraper service exposes metrics for monitoring:

1. **Request Success/Failure Rates**: Tracks successful vs. failed requests
2. **Scraping Duration**: Measures time taken for scraping operations
3. **Items Scraped**: Counts number of listings successfully scraped
4. **Error Rates**: Tracks different types of errors

## Security Considerations

1. **Data Privacy**: The scraper only collects publicly available data
2. **Authentication**: API endpoints are secured using API keys
3. **Rate Limiting**: Prevents abuse of the scraper service

## Best Practices

1. **Respect Robots.txt**: The scraper respects the robots.txt file
2. **Reasonable Rate Limits**: Avoids overwhelming the target site
3. **Error Handling**: Gracefully handles network and parsing errors
4. **Data Validation**: Validates and sanitizes scraped data

## Troubleshooting

Common issues and their solutions:

1. **Blocked Requests**: Rotate proxies or decrease request frequency
2. **Parsing Errors**: Update parser to match site layout changes
3. **High CPU Usage**: Adjust concurrency settings
4. **Memory Leaks**: Ensure proper session cleanup

## Related Documentation

- [API Documentation](api.md)
- [Deployment Guide](deployment.md)
- [Monitoring Guide](monitoring.md)
