from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from collections import defaultdict
import time
from src.logging.logger import get_logger

logger = get_logger(__name__)

# Rate limiting storage
request_counts = defaultdict(lambda: {"count": 0, "reset_time": time.time()})

class RateLimitMiddleware:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.reset_interval = 60  # seconds

    async def __call__(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host

        # Check rate limit
        current_time = time.time()
        client_requests = request_counts[client_ip]

        if current_time > client_requests["reset_time"] + self.reset_interval:
            # Reset counter if interval has passed
            client_requests["count"] = 0
            client_requests["reset_time"] = current_time

        if client_requests["count"] >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."}
            )

        # Increment request counter
        client_requests["count"] += 1

        # Process request
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )

class AuthenticationMiddleware:
    async def __call__(self, request: Request, call_next):
        # Get API key from header
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            logger.warning("Missing API key in request")
            raise HTTPException(status_code=401, detail="API key required")

        # Validate API key (implement your own validation logic)
        if not self._validate_api_key(api_key):
            logger.warning(f"Invalid API key: {api_key}")
            raise HTTPException(status_code=403, detail="Invalid API key")

        return await call_next(request)

    def _validate_api_key(self, api_key: str) -> bool:
        # Implement your API key validation logic
        valid_keys = ["your-api-key"]  # Store these securely
        return api_key in valid_keys
