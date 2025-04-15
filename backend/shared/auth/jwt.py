import jwt
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
import logging
from fastapi import HTTPException, status
from jwt.exceptions import PyJWTError

from pydantic import BaseModel, Field, validator

from backend.shared.config.settings import get_settings
from backend.shared.config.logging_config import get_logger

# Configure logging
logger = logging.getLogger(__name__)

# Pydantic models for tokens
class Token(BaseModel):
    """Token model returned to clients"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until expiration


class TokenData(BaseModel):
    """Data extracted from a token"""
    user_id: int
    username: str
    email: str
    role: str = "user"
    permissions: list = Field(default_factory=list)
    exp: Optional[datetime] = None
    
    @validator("exp")
    def validate_expiration(cls, v):
        """Validate that the token is not expired"""
        if v and v < datetime.utcnow():
            raise ValueError("Token expired")
        return v


class JWTHandler:
    """JWT token handler for creating and validating tokens"""

    def __init__(self):
        """Initialize with settings from configuration"""
        self.settings = get_settings()
        self.algorithm = self.settings.JWT_ALGORITHM
        self.secret_key = self.settings.JWT_SECRET_KEY
        self.access_token_expire_minutes = self.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        
        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY must be set in the environment")
    
    def create_access_token(self, data: Dict) -> Token:
        """
        Create a new JWT access token.
        
        Args:
            data: Dictionary containing user data for token payload
            
        Returns:
            Token: A Token object with the access token and metadata
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        
        try:
            encoded_jwt = jwt.encode(
                to_encode, 
                self.secret_key, 
                algorithm=self.algorithm
            )
            
            # Log token creation (without the actual token)
            logger.info(
                f"Created access token for user {data.get('username')} expiring at {expire.isoformat()}"
            )
            
            return Token(
                access_token=encoded_jwt,
                expires_in=self.access_token_expire_minutes * 60
            )
        except Exception as e:
            logger.error(f"Failed to create token: {str(e)}")
            raise
    
    def decode_token(self, token: str) -> TokenData:
        """
        Decode and validate a JWT token.
        
        Args:
            token: The JWT token to decode
            
        Returns:
            TokenData: Data extracted from the token
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # Extract user data from payload
            token_data = TokenData(
                user_id=payload.get("user_id"),
                username=payload.get("username"),
                email=payload.get("email"),
                role=payload.get("role", "user"),
                permissions=payload.get("permissions", []),
                exp=datetime.fromtimestamp(payload.get("exp"))
            )
            
            return token_data
            
        except PyJWTError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except ValueError as e:
            logger.warning(f"Token validation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def format_error_response(self, error: Union[PyJWTError, ValueError, Exception]) -> Dict[str, Any]:
        """
        Format a consistent error response for JWT errors.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Dict: A formatted error response
        """
        error_type = type(error).__name__
        
        if isinstance(error, PyJWTError):
            status_code = 401
            detail = "Invalid or expired token"
        elif isinstance(error, ValueError) and "expired" in str(error).lower():
            status_code = 401
            detail = "Token expired"
        else:
            status_code = 500
            detail = "Authentication error"
        
        return {
            "status_code": status_code,
            "error": error_type,
            "detail": detail,
            "timestamp": datetime.utcnow().isoformat()
        }

# Create singleton instance
jwt_handler = JWTHandler()

settings = get_settings()

def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # Encode the JWT
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token
    
    Args:
        token: JWT token to decode
        
    Returns:
        Decoded token payload
        
    Raises:
        jwt.PyJWTError: If token is invalid or expired
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )


def verify_token(token: str) -> Union[Dict[str, Any], None]:
    """
    Verify a JWT token and return the payload if valid
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        decoded_token = decode_token(token)
        return decoded_token
    except jwt.PyJWTError:
        return None
        
        
def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "refresh": True})
    
    # Encode the JWT
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt 