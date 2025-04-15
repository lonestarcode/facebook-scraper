import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
import uuid
import logging
from pydantic import BaseModel

from ..config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Pydantic models for tokens
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    sub: str  # Subject (user ID)
    exp: datetime  # Expiration time
    iat: datetime  # Issued at
    jti: str  # JWT ID
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[List[str]] = None
    scopes: List[str] = []


def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token
    
    Args:
        data: The data to encode in the token
        expires_delta: Optional expiration time delta, defaults to settings value
        
    Returns:
        The encoded JWT token as a string
    """
    to_encode = data.copy()
    
    # Set expiration time
    expires_delta = expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    
    # Add standard JWT claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4()),  # Unique token ID
    })
    
    try:
        # Encode the token
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.JWT_SECRET_KEY, 
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating JWT token: {str(e)}")
        raise


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token
    
    Args:
        token: The JWT token to decode
        
    Returns:
        The decoded token payload
        
    Raises:
        jwt.PyJWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature": True}
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Expired JWT token")
        raise
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error decoding JWT token: {str(e)}")
        raise


def create_refresh_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token
    
    Args:
        data: The data to encode in the token
        expires_delta: Optional expiration time delta, defaults to settings value
        
    Returns:
        The encoded JWT token as a string
    """
    to_encode = data.copy()
    
    # Set expiration time (usually longer than access token)
    expires_delta = expires_delta or timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    expire = datetime.utcnow() + expires_delta
    
    # Add standard JWT claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4()),  # Unique token ID
        "token_type": "refresh"
    })
    
    try:
        # Encode the token using a different key for refresh tokens
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.JWT_REFRESH_SECRET_KEY, 
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating refresh token: {str(e)}")
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash using PassLib
    
    Args:
        plain_password: The plain text password
        hashed_password: The hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using PassLib
    
    Args:
        password: The plain text password
        
    Returns:
        The hashed password
    """
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password) 