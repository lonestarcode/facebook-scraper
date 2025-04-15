from typing import Callable, List, Optional
from functools import wraps
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..auth.jwt import jwt_handler
from ..auth.auth_service import AuthService
from ..database.session import get_db_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def get_auth_service(db: Session = Depends(get_db_session)):
    """Dependency for getting the auth service"""
    return AuthService(db)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Dependency for getting the current authenticated user"""
    user = auth_service.get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def require_permissions(required_permissions: List[str]):
    """Middleware to check if the user has the required permissions"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            if not request:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not process request"
                )
            
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            token_data = jwt_handler.validate_token(token)
            if not token_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            db = next(get_db_session())
            auth_service = AuthService(db)
            user = auth_service.get_current_user(token)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if not auth_service.validate_permissions(user, required_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions",
                )
            
            # Add user to request state for use in the endpoint
            request.state.user = user
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator 