import aiohttp
from src.scraper.base_scraper import BaseScraper
from src.logging.logger import log_execution_time

class APIScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="api")
        
    @log_execution_time
    async def enrich_listings(self, listings):
        """Enrich listings with additional data from Facebook API"""
        try:
            enriched_listings = []
            async with aiohttp.ClientSession() as session:
                for listing in listings:
                    if not listing:
                        continue
                    
                    enriched_data = await self._fetch_listing_details(session, listing)
                    if enriched_data:
                        listing.update(enriched_data)
                    enriched_listings.append(listing)
                    
            return enriched_listings
            
        except Exception as e:
            self.logger.error(f"Error enriching listings: {str(e)}")
            raise
            
    async def _fetch_listing_details(self, session, listing):
        """Fetch additional details for a listing from Facebook API"""
        try:
            listing_id = listing['url'].split('/')[-1]
            url = f"{self.base_url}/api/graphql"
            
            # Facebook GraphQL query for listing details
            query = """
            query MarketplaceListingQuery($listingId: ID!) {
                marketplace_listing(listing_id: $listingId) {
                    description
                    seller {
                        id
                        name
                    }
                    images {
                        url
                    }
                }
            }
            """
            
            async with session.post(url, json={'query': query, 'variables': {'listingId': listing_id}}) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_api_response(data)
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching listing details: {str(e)}")
            return None
            
    def _parse_api_response(self, response_data):
        """Parse the API response and extract relevant data"""
        try:
            listing_data = response_data.get('data', {}).get('marketplace_listing', {})
            return {
                'description': listing_data.get('description', ''),
                'seller_id': listing_data.get('seller', {}).get('id'),
                'seller_name': listing_data.get('seller', {}).get('name'),
                'images': [img['url'] for img in listing_data.get('images', [])]
            }
        except Exception as e:
            self.logger.error(f"Error parsing API response: {str(e)}")
            return None

