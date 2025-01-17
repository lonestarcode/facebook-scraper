from transformers import pipeline
from src.logging.logger import get_logger, log_execution_time
from src.monitoring.metrics import SUMMARY_GENERATION_TIME
import time

logger = get_logger('llm_handler')

class LLMHandler:
    def __init__(self):
        self.summarizer = pipeline("summarization")
        self.classifier = pipeline("text-classification")
        
    @log_execution_time
    async def process_listing(self, listing_data: dict) -> dict:
        """Process a single listing with LLM models"""
        try:
            start_time = time.time()
            
            # Generate summary
            summary = await self._generate_summary(listing_data.get('description', ''))
            
            # Classify content
            classification = await self._classify_content(listing_data.get('title', ''))
            
            duration = time.time() - start_time
            SUMMARY_GENERATION_TIME.labels(model='default').observe(duration)
            
            return {
                'summary': summary,
                'classification': classification,
                'processing_time': duration
            }
            
        except Exception as e:
            logger.error(f"Error in LLM processing: {str(e)}")
            raise
            
    async def _generate_summary(self, text: str) -> str:
        """Generate a summary of the listing description"""
        if not text:
            return ''
        try:
            result = self.summarizer(text, max_length=100, min_length=30)
            return result[0]['summary_text']
        except Exception as e:
            logger.error(f"Summary generation failed: {str(e)}")
            return text[:100]
            
    async def _classify_content(self, text: str) -> dict:
        """Classify the listing content"""
        try:
            result = self.classifier(text)
            return {
                'label': result[0]['label'],
                'confidence': result[0]['score']
            }
        except Exception as e:
            logger.error(f"Classification failed: {str(e)}")
            return {'label': 'unknown', 'confidence': 0.0}
