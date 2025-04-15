from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta

from backend.shared.auth.auth_service import AuthService
from backend.shared.models.user import User
from backend.shared.config.settings import get_settings
from backend.shared.config.logging_config import get_logger
from backend.services.api.src.dependencies import get_db

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = get_logger("auth_routes")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
settings = get_settings()

# Pydantic models for request validation
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    username: str
    password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str
    role: str

class MessageResponse(BaseModel):
    message: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)) -> Any:
    """Register a new user and return access token"""
    auth_service = AuthService(db)
    
    # Check if username or email already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Create new user
    try:
        password_hash = auth_service.get_password_hash(user_data.password)
        
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            role="user",
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Generate access token
        access_token = auth_service.create_access_token(
            user_id=new_user.id,
            username=new_user.username,
            role=new_user.role
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": new_user.id,
            "username": new_user.username,
            "role": new_user.role
        }
    
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error registering user"
        )


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Any:
    """Authenticate a user and return an access token"""
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login time
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = auth_service.create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "role": user.role
    }


@router.post("/reset-password-request", response_model=MessageResponse)
async def request_password_reset(request_data: PasswordResetRequest, db: Session = Depends(get_db)) -> Any:
    """Request a password reset token"""
    auth_service = AuthService(db)
    user = db.query(User).filter(User.email == request_data.email).first()
    
    # Always return success even if user doesn't exist (security best practice)
    if not user:
        logger.warning(f"Password reset requested for non-existent email: {request_data.email}")
        return {"message": "If your email is registered, you will receive a password reset link"}
    
    # Generate reset token
    reset_token = auth_service.generate_reset_token(user.id)
    
    # In a real application, you would send this token via email
    # For this demo, we'll just log it
    logger.info(f"Password reset token for {user.email}: {reset_token}")
    
    return {"message": "If your email is registered, you will receive a password reset link"}


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(reset_data: PasswordReset, db: Session = Depends(get_db)) -> Any:
    """Reset a user's password using a valid reset token"""
    auth_service = AuthService(db)
    
    # Validate token and get user
    user_id = auth_service.validate_reset_token(reset_data.token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    user.password_hash = auth_service.get_password_hash(reset_data.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    
    return {"message": "Password has been reset successfully"}


@router.get("/verify-token", response_model=Dict[str, Any])
async def verify_token(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Any:
    """Verify a token and return user information"""
    auth_service = AuthService(db)
    payload = auth_service.validate_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database to ensure they still exist and are active
    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User inactive or deleted",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "email": user.email,
        "is_active": user.is_active
    } 