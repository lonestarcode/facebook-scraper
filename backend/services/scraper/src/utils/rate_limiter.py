"""Rate limiter for controlling request rates."""

import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger("scraper.rate_limiter")

class RateLimiter:
    """
    Rate limiter for controlling the rate of requests.
    
    Uses the token bucket algorithm to limit request rates.
    """
    
    def __init__(
        self,
        requests_per_second: float,
        burst_size: Optional[int] = None
    ):
        """
        Initialize the rate limiter.
        
        Args:
            requests_per_second: Maximum number of requests per second
            burst_size: Maximum burst size (if None, uses 2x requests_per_second)
        """
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size if burst_size is not None else max(2, int(2 * requests_per_second))
        
        # Token bucket state
        self.tokens = self.burst_size
        self.last_refill_time = time.monotonic()
        
        # Lock for thread safety
        self.lock = asyncio.Lock()
        
        logger.debug(f"Rate limiter initialized: {requests_per_second} requests/second, burst size: {self.burst_size}")
    
    async def wait(self) -> None:
        """
        Wait until a token is available.
        
        This method blocks until a token is available and then consumes one token.
        """
        async with self.lock:
            # Refill tokens based on time passed
            now = time.monotonic()
            time_passed = now - self.last_refill_time
            
            # Calculate tokens to add
            new_tokens = time_passed * self.requests_per_second
            self.tokens = min(self.tokens + new_tokens, self.burst_size)
            self.last_refill_time = now
            
            # If we have at least one token, consume it immediately
            if self.tokens >= 1:
                self.tokens -= 1
                wait_time = 0
            else:
                # Not enough tokens, calculate wait time
                wait_time = (1 - self.tokens) / self.requests_per_second
                self.tokens = 0
                self.last_refill_time = now + wait_time
            
        # Wait outside the lock if needed
        if wait_time > 0:
            logger.debug(f"Rate limit reached, waiting for {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)
    
    def reset(self) -> None:
        """Reset the rate limiter to its initial state."""
        self.tokens = self.burst_size
        self.last_refill_time = time.monotonic()
        
        logger.debug("Rate limiter reset")


class DistributedRateLimiter(RateLimiter):
    """
    Rate limiter that works across multiple instances using Redis.
    
    Note: This requires a Redis connection and the redis-py library.
    """
    
    def __init__(
        self,
        requests_per_second: float,
        burst_size: Optional[int] = None,
        redis_client = None,
        key_prefix: str = "rate_limiter"
    ):
        """
        Initialize the distributed rate limiter.
        
        Args:
            requests_per_second: Maximum number of requests per second
            burst_size: Maximum burst size (if None, uses 2x requests_per_second)
            redis_client: Redis client for distributed locking
            key_prefix: Prefix for Redis keys
        """
        super().__init__(requests_per_second, burst_size)
        
        if redis_client is None:
            raise ValueError("Redis client is required for DistributedRateLimiter")
        
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.tokens_key = f"{key_prefix}:tokens"
        self.last_refill_key = f"{key_prefix}:last_refill"
        
        logger.debug(f"Distributed rate limiter initialized with Redis")
    
    async def wait(self) -> None:
        """
        Wait until a token is available.
        
        This method uses Redis for distributed rate limiting.
        """
        # Use Redis to implement distributed rate limiting
        # This is a simplified implementation and could be improved
        while True:
            # Get a lock
            async with self.lock:
                # Try to get the current state from Redis
                tokens = await self.redis.get(self.tokens_key)
                last_refill = await self.redis.get(self.last_refill_key)
                
                tokens = float(tokens) if tokens else self.burst_size
                last_refill = float(last_refill) if last_refill else time.monotonic()
                
                # Refill tokens based on time passed
                now = time.monotonic()
                time_passed = now - last_refill
                
                # Calculate tokens to add
                new_tokens = time_passed * self.requests_per_second
                tokens = min(tokens + new_tokens, self.burst_size)
                
                # If we have at least one token, consume it immediately
                if tokens >= 1:
                    tokens -= 1
                    wait_time = 0
                    
                    # Update Redis
                    await self.redis.set(self.tokens_key, str(tokens))
                    await self.redis.set(self.last_refill_key, str(now))
                    
                    # We got a token, return
                    return
                else:
                    # Not enough tokens, calculate wait time
                    wait_time = (1 - tokens) / self.requests_per_second
                    
                    # Update Redis
                    await self.redis.set(self.tokens_key, "0")
                    await self.redis.set(self.last_refill_key, str(now + wait_time))
            
            # Wait outside the lock
            logger.debug(f"Distributed rate limit reached, waiting for {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)
    
    async def reset(self) -> None:
        """Reset the rate limiter to its initial state."""
        await self.redis.set(self.tokens_key, str(self.burst_size))
        await self.redis.set(self.last_refill_key, str(time.monotonic()))
        
        logger.debug("Distributed rate limiter reset") 