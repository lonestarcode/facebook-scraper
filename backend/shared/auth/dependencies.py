from typing import Optional, Annotated, List, Union, Callable, Dict, Any
from functools import wraps
import logging
import jwt
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status, Security, Header, Query, WebSocket, Cookie
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError

from ..models.user import User, UserInDB
from .utils import decode_access_token, TokenData
from ..config.settings import get_settings
from backend.shared.auth.jwt import JWTHandler
from backend.shared.database.session import get_db_session

# Configure logger
logger = logging.getLogger(__name__)

settings = get_settings()

# Setup OAuth2 with password flow
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_PREFIX}/auth/token",
    scopes={
        "users:read": "Read user information",
        "users:write": "Create or modify users",
        "listings:read": "Read marketplace listings",
        "listings:write": "Create or modify listings",
        "admin": "Administrator access"
    }
)

jwt_handler = JWTHandler()

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """Dependency to get the current authenticated user.
    
    Args:
        token: JWT token
        db: Database session
        
    Returns:
        The authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify and decode the token
        token_data = jwt_handler.verify_token(token)
        if token_data is None:
            raise credentials_exception
            
        # Get the user from the database
        user = await get_user_by_id(db, token_data.user_id)
        if user is None:
            raise credentials_exception
            
        # Check if the user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user"
            )
            
        return user
    except JWTError:
        logger.warning(f"JWT validation error for token: {token[:10]}...")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Error in get_current_user: {str(e)}")
        raise credentials_exception

async def get_current_user_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None)
) -> User:
    """Get the current user from a WebSocket connection.
    
    Args:
        websocket: The WebSocket connection
        token: JWT token from query parameter
        authorization: Authorization header
        access_token: JWT token from cookie
        
    Returns:
        The authenticated user
        
    Raises:
        WebSocketDisconnect: If authentication fails
    """
    # Extract token from various sources
    jwt_token = None
    
    # First check the query parameter
    if token:
        jwt_token = token
    # Then check the authorization header
    elif authorization and authorization.startswith("Bearer "):
        jwt_token = authorization.replace("Bearer ", "")
    # Finally check the cookie
    elif access_token:
        jwt_token = access_token
        
    if not jwt_token:
        logger.warning("No authentication token found in WebSocket connection")
        await websocket.close(code=1008, reason="Unauthorized")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
        
    try:
        # Verify and decode the token
        token_data = jwt_handler.verify_token(jwt_token)
        if token_data is None:
            await websocket.close(code=1008, reason="Invalid token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
            
        # Get the user from the database
        async with get_db_session() as db:
            user = await get_user_by_id(db, token_data.user_id)
            
        if user is None:
            await websocket.close(code=1008, reason="User not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
            
        # Check if the user is active
        if not user.is_active:
            await websocket.close(code=1008, reason="User inactive")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user"
            )
            
        return user
    except JWTError:
        logger.warning(f"JWT validation error for WebSocket token: {jwt_token[:10]}...")
        await websocket.close(code=1008, reason="Invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"Error in get_current_user_ws: {str(e)}")
        await websocket.close(code=1008, reason="Authentication error")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication error"
        )

async def get_current_active_user(
    current_user: Annotated[UserInDB, Depends(get_current_user)]
) -> UserInDB:
    """
    Dependency that ensures the current user is active
    
    Args:
        current_user: The current user from get_current_user
        
    Returns:
        The current active user
        
    Raises:
        HTTPException: If the user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


# Define role-based dependencies
async def get_admin_user(
    current_user: Annotated[UserInDB, Security(get_current_user, scopes=["admin"])]
) -> UserInDB:
    """
    Dependency that ensures the current user has admin role
    
    Args:
        current_user: The current user with admin scope
        
    Returns:
        The current admin user
        
    Raises:
        HTTPException: If the user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


# Permission-based dependency
def has_permission(required_permission: str):
    """
    Factory for dependencies that check if a user has a specific permission
    
    Args:
        required_permission: The permission to check for
        
    Returns:
        A dependency function that checks the permission
    """
    async def check_permission(
        current_user: Annotated[UserInDB, Depends(get_current_active_user)]
    ) -> UserInDB:
        user_permissions = current_user.permissions or []
        
        # Admin users have all permissions
        if current_user.role == "admin":
            return current_user
            
        if required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {required_permission}"
            )
        return current_user
        
    return check_permission


def requires_role(role: Union[str, List[str]]) -> Callable:
    """
    Dependency factory for role-based access control.
    
    Args:
        role: Required role or list of roles (any match grants access)
        
    Returns:
        Callable: A dependency that checks if the user has the required role
    """
    roles = [role] if isinstance(role, str) else role
    
    async def role_checker(
        current_user: User = Security(get_current_active_user)
    ) -> User:
        if current_user.role not in roles and "admin" not in roles:
            logger.warning(
                f"Role access denied: User {current_user.username} with role {current_user.role} "
                f"attempted to access endpoint requiring {roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires role: {', '.join(roles)}",
            )
        return current_user
    
    return role_checker


def admin_required(current_user: User = Security(get_current_active_user)) -> User:
    """
    Dependency that ensures the current user has admin role.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        User: The authenticated admin user
        
    Raises:
        HTTPException: If the user is not an admin
    """
    if current_user.role != "admin":
        logger.warning(
            f"Admin access denied: User {current_user.username} attempted to access admin endpoint"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user

async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """Get a user by ID.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        The user or None if not found
    """
    user = await db.get(User, user_id)
    return user

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get a user by username.
    
    Args:
        db: Database session
        username: Username
        
    Returns:
        The user or None if not found
    """
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none() 