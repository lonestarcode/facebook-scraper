"""Rate limiting utilities for API and scraper services."""

import time
import functools
import logging
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass, field

from fastapi import Request, Response, HTTPException

logger = logging.getLogger(__name__)

@dataclass
class RateLimiter:
    """Rate limiter implementation using token bucket algorithm."""
    
    rate: float  # tokens per second
    max_tokens: int
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    
    def __post_init__(self) -> None:
        """Initialize tokens and last refill timestamp."""
        self.tokens = self.max_tokens
        self.last_refill = time.time()
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.rate
        
        self.tokens = min(self.max_tokens, self.tokens + new_tokens)
        self.last_refill = now
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False otherwise
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


# In-memory store for rate limiters
_limiters: Dict[str, Dict[str, RateLimiter]] = {}


def get_limiter(
    key: str, 
    namespace: str = "default", 
    rate: float = 10.0, 
    max_tokens: int = 10
) -> RateLimiter:
    """
    Get or create a rate limiter for a specific key.
    
    Args:
        key: Unique identifier for the rate limiter
        namespace: Group to organize limiters
        rate: Tokens per second refill rate
        max_tokens: Maximum token bucket capacity
        
    Returns:
        RateLimiter instance
    """
    if namespace not in _limiters:
        _limiters[namespace] = {}
    
    if key not in _limiters[namespace]:
        _limiters[namespace][key] = RateLimiter(rate=rate, max_tokens=max_tokens)
    
    return _limiters[namespace][key]


def rate_limit(
    key_func: Optional[Callable[[Request], str]] = None,
    rate: float = 10.0,
    max_tokens: int = 10,
    namespace: str = "default",
    status_code: int = 429,
    error_message: str = "Rate limit exceeded"
) -> Callable:
    """
    Rate limiting decorator for FastAPI endpoints.
    
    Args:
        key_func: Function to extract key from request (defaults to IP address)
        rate: Tokens per second
        max_tokens: Maximum token bucket size
        namespace: Group name for limiters
        status_code: HTTP status code on rate limit
        error_message: Error message on rate limit
        
    Returns:
        Decorator function
    """
    def default_key_func(request: Request) -> str:
        """Default key function using client IP."""
        return request.client.host if request.client else "unknown"
    
    key_extractor = key_func or default_key_func
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = None
            
            # Find request object in args or kwargs
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
                    
            if request is None:
                request = kwargs.get("request")
                
            if request is None:
                logger.warning("Rate limit decorator used without request parameter")
                return await func(*args, **kwargs)
                
            key = key_extractor(request)
            limiter = get_limiter(key, namespace, rate, max_tokens)
            
            if not limiter.consume():
                logger.warning(f"Rate limit exceeded for {key} in {namespace}")
                
                # Add rate limit headers
                response = Response(
                    content={"detail": error_message},
                    status_code=status_code,
                    media_type="application/json"
                )
                response.headers["X-RateLimit-Limit"] = str(max_tokens)
                response.headers["X-RateLimit-Remaining"] = str(int(limiter.tokens))
                response.headers["Retry-After"] = str(int((1 - limiter.tokens) / rate) + 1)
                
                raise HTTPException(
                    status_code=status_code,
                    detail=error_message,
                    headers=dict(response.headers)
                )
                
            return await func(*args, **kwargs)
            
        return wrapper
        
    return decorator 