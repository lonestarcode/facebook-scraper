from src.scraper.base import BaseScraper
from src.logging.logger import log_execution_time
from transformers import pipeline

class LLMScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="llm")
        self.summarizer = pipeline("summarization")
        self.classifier = pipeline("text-classification")
        
    @log_execution_time
    async def process_listings(self, listings):
        """Process listings with LLM for enhanced analysis"""
        try:
            processed_listings = []
            for listing in listings:
                if not listing:
                    continue
                    
                analysis = await self._analyze_listing(listing)
                listing['analysis'] = analysis
                processed_listings.append(listing)
                
            return processed_listings
            
        except Exception as e:
            self.logger.error(f"Error processing listings with LLM: {str(e)}")
            raise
            
    async def _analyze_listing(self, listing):
        """Analyze a single listing using LLM models"""
        try:
            description = listing.get('description', '')
            
            # Generate summary
            summary = self.summarizer(description, max_length=100)[0]['summary_text']
            
            # Classify listing
            classification = self.classifier(description)[0]
            
            return {
                'summary': summary,
                'category': classification['label'],
                'confidence': classification['score']
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing listing: {str(e)}")
            return None
