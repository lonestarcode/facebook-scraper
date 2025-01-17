import functools
from src.logging.logger import get_logger

logger = get_logger('error_handler')

class ScraperError(Exception):
    """Base exception for scraper errors"""
    pass

def with_error_handling(func):
    """Decorator for handling errors in pipeline functions"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise ScraperError(f"Pipeline error in {func.__name__}: {str(e)}")
    return wrapper
