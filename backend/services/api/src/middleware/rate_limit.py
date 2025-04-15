"""Rate limiting middleware for the API service."""

import time
from typing import Dict, Tuple, Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from shared.config.settings import get_settings

# Get settings
settings = get_settings("api")

class RateLimiter:
    """
    Simple in-memory rate limiter using the token bucket algorithm.
    
    For production use, this should be replaced with a Redis-based implementation.
    """
    
    def __init__(self, rate: int, per: int, burst: int = 1):
        """
        Initialize the rate limiter.
        
        Args:
            rate: Number of requests allowed per time period
            per: Time period in seconds
            burst: Maximum burst size (additional tokens allowed)
        """
        self.rate = rate  # Tokens per second
        self.per = per    # Time window in seconds
        self.burst = burst
        self.tokens: Dict[str, Tuple[float, int]] = {}  # client_id -> (last_updated, tokens)
    
    def is_allowed(self, client_id: str) -> bool:
        """
        Check if a request from the client is allowed.
        
        Args:
            client_id: Unique identifier for the client (typically IP address)
            
        Returns:
            True if the request is allowed, False otherwise
        """
        now = time.time()
        
        # Get current token state for client, or initialize if new
        if client_id not in self.tokens:
            self.tokens[client_id] = (now, self.burst)
            return True
        
        # Get last update time and token count
        last_updated, tokens = self.tokens[client_id]
        
        # Calculate token refill based on time passed
        time_passed = now - last_updated
        token_refill = time_passed * (self.rate / self.per)
        
        # Update token count, but don't exceed burst limit
        new_tokens = min(self.burst, tokens + token_refill)
        
        # Check if request can be allowed
        if new_tokens >= 1:
            # Deduct one token for this request
            self.tokens[client_id] = (now, new_tokens - 1)
            return True
        else:
            # Not enough tokens, request is denied
            self.tokens[client_id] = (now, new_tokens)
            return False
    
    def get_retry_after(self, client_id: str) -> float:
        """
        Get the time (in seconds) after which the client should retry.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            Seconds to wait before retrying
        """
        if client_id not in self.tokens:
            return 0
        
        last_updated, tokens = self.tokens[client_id]
        
        # Calculate how many tokens are needed
        tokens_needed = 1 - tokens
        
        # Calculate time needed to refill those tokens
        return tokens_needed * self.per / self.rate


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests.
    
    Uses a token bucket algorithm to limit requests per client.
    """
    
    def __init__(self, app):
        """Initialize the middleware with settings from configuration."""
        super().__init__(app)
        self.rate_limit_enabled = settings.api.rate_limit.enabled
        self.rate = settings.api.rate_limit.rate
        self.per = settings.api.rate_limit.per
        self.burst = settings.api.rate_limit.burst
        self.rate_limiter = RateLimiter(self.rate, self.per, self.burst)
        self.exclude_paths = settings.api.rate_limit.exclude_paths.split(",")
    
    def get_client_id(self, request: Request) -> str:
        """
        Get a unique identifier for the client.
        
        Uses X-Forwarded-For header if available, otherwise client host.
        
        Args:
            request: The incoming request
            
        Returns:
            Unique identifier for the client
        """
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first IP in the list (client IP)
            return forwarded_for.split(",")[0].strip()
        else:
            # Fall back to the client's host
            return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and apply rate limiting."""
        # Skip rate limiting for excluded paths
        if not self.rate_limit_enabled or request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Skip rate limiting for health check endpoints
        if request.url.path.startswith("/health"):
            return await call_next(request)
        
        # Get client identifier
        client_id = self.get_client_id(request)
        
        # Check rate limit
        if not self.rate_limiter.is_allowed(client_id):
            retry_after = int(self.rate_limiter.get_retry_after(client_id))
            raise HTTPException(
                status_code=429,
                detail="Too many requests",
                headers={"Retry-After": str(retry_after)}
            )
        
        # Request is allowed, proceed
        return await call_next(request) 