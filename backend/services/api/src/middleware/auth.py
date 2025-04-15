"""Authentication middleware for the API service."""

import time
import jwt
from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from shared.config.settings import get_settings
from shared.models.marketplace import User
from src.database.session import get_db

# Get settings
settings = get_settings("api")
JWT_SECRET = settings.auth.jwt_secret
JWT_ALGORITHM = settings.auth.jwt_algorithm

# Setup security bearer
security = HTTPBearer()

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware that verifies JWT tokens.
    
    Excludes health check endpoints and OPTIONS requests.
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and handle authentication."""
        # Skip authentication for health check endpoints and OPTIONS requests
        if request.url.path.startswith("/health") or request.method == "OPTIONS":
            return await call_next(request)
        
        # Skip authentication for public endpoints if configured
        if request.url.path in settings.auth.public_endpoints.split(","):
            return await call_next(request)
            
        auth_header = request.headers.get("Authorization")
        
        # Check if Authorization header exists
        if not auth_header:
            return HTTPException(
                status_code=401,
                detail="Missing Authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify JWT token
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Verify and decode the token
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            
            # Check token expiration
            if payload.get("exp") < time.time():
                raise HTTPException(
                    status_code=401,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Add user ID to request state
            request.state.user_id = payload.get("sub")
            
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication error: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Continue processing the request
        return await call_next(request)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user.
    
    This is a dependency to be used in API endpoints where user information is needed.
    """
    try:
        # Decode the JWT token
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        
        # Check token expiration
        if payload.get("exp") < time.time():
            raise HTTPException(
                status_code=401,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def create_access_token(user_id: str) -> str:
    """
    Create a new JWT access token for a user.
    
    Args:
        user_id: The user ID to include in the token
        
    Returns:
        The encoded JWT token
    """
    # Set token expiration
    expiration = int(time.time()) + settings.auth.token_expiration_seconds
    
    # Create token payload
    payload = {
        "sub": str(user_id),
        "exp": expiration,
        "iat": int(time.time()),
        "type": "access"
    }
    
    # Encode and return the token
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM) 