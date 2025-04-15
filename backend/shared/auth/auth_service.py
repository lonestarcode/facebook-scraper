import hashlib
import os
from typing import Optional, Dict, Any, List, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
import secrets
import jwt
import string

from backend.shared.auth.jwt import jwt_handler, Token, TokenData
from backend.shared.config.logging_config import get_logger
from backend.shared.models.user import User
from backend.shared.config.settings import get_settings

# Get app settings
settings = get_settings()
logger = get_logger("auth_service")

class AuthService:
    """
    Service for handling user authentication and authorization.
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES or 30
        self.reset_token_expire_minutes = settings.RESET_TOKEN_EXPIRE_MINUTES or 15
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Dict[str, str]:
        """Hash a password with an optional salt or generate a new salt"""
        if not salt:
            salt = os.urandom(32).hex()
        
        # Create a hash using pbkdf2_hmac with sha256
        hashed_password = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # Number of iterations
        ).hex()
        
        return {
            'hashed_password': hashed_password,
            'salt': salt
        }
    
    @staticmethod
    def verify_password_with_salt(plain_password: str, hashed_password: str, salt: str) -> bool:
        """Verify a password against a hash and salt"""
        password_data = AuthService.hash_password(plain_password, salt)
        return password_data['hashed_password'] == hashed_password
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: The password in plain text
            hashed_password: The stored password hash
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """
        Generate a hash for the given password.
        
        Args:
            password: The password to hash
            
        Returns:
            str: The password hash
        """
        return self.pwd_context.hash(password)
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user by username and password.
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            Optional[User]: User object if authentication is successful, None otherwise
        """
        # Check if username is actually an email
        if '@' in username:
            user = self.db.query(User).filter(User.email == username).first()
        else:
            user = self.db.query(User).filter(User.username == username).first()
        
        if not user:
            return None
        
        if not self.verify_password(password, user.password_hash):
            return None
            
        return user
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get a user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            Optional[User]: User object if found, None otherwise
        """
        return self.db.query(User).filter(User.id == user_id).first()
    
    async def create_user(self, username: str, password: str, email: str, role: str = "user") -> Optional[User]:
        """Create a new user"""
        try:
            # Check if user exists
            query = select(User).where(User.username == username)
            result = await self.db.execute(query)
            existing_user = result.scalars().first()
            
            if existing_user:
                logger.warning(f"User creation failed: Username {username} already exists")
                return None
            
            # Hash the password
            password_data = self.hash_password(password)
            
            # Create new user
            new_user = User(
                username=username,
                email=email,
                hashed_password=password_data['hashed_password'],
                salt=password_data['salt'],
                role=role
            )
            
            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)
            
            logger.info(f"User {username} created successfully")
            return new_user
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating user: {str(e)}")
            return None
    
    def create_access_token(
        self, 
        user_id: int, 
        username: str, 
        role: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.token_expire_minutes)
        
        to_encode = {
            "sub": str(user_id),
            "user_id": user_id,
            "username": username,
            "role": role,
            "exp": expire
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a token and return its payload.
        
        Args:
            token: JWT token
            
        Returns:
            Optional[Dict[str, Any]]: Token payload if valid, None otherwise
        """
        return jwt_handler.validate_token(token)
    
    def get_current_user(self, token: str) -> Optional[User]:
        """Get the current user from a token"""
        token_data = jwt_handler.validate_token(token)
        
        if not token_data:
            return None
            
        user = self.db.query(User).filter(User.id == token_data.user_id).first()
        return user
    
    def check_permissions(self, user: User, required_permissions: List[str]) -> bool:
        """
        Check if a user has all the required permissions.
        
        Args:
            user: User object
            required_permissions: List of required permission strings
            
        Returns:
            bool: True if user has all required permissions, False otherwise
        """
        if not user or not user.permissions:
            return False
            
        # Convert user permissions to a set for faster lookup
        user_permissions = set(user.permissions)
        
        # Admin role has all permissions
        if user.role == "admin" or "admin" in user_permissions:
            return True
            
        # Check if all required permissions are in the user's permissions
        return all(perm in user_permissions for perm in required_permissions)
    
    def generate_reset_token(self, user: User) -> str:
        """
        Generate a password reset token for a user.
        
        Args:
            user: User object
            
        Returns:
            str: Reset token
        """
        # Generate a secure random token
        reset_token = secrets.token_urlsafe(32)
        
        # Update the user's reset token in the database
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=24)
        self.db.commit()
        
        return reset_token
    
    def validate_reset_token(self, token: str) -> Optional[int]:
        """
        Validate a reset token and return the user ID if valid.
        
        Args:
            token: Reset token
            
        Returns:
            Optional[int]: User ID if token is valid, None otherwise
        """
        # Find user with this token
        user = self.db.query(User).filter(
            User.reset_token == token,
            User.reset_token_expires > datetime.utcnow()
        ).first()
        
        if not user:
            return None
            
        return user.id
    
    def reset_password(self, user_id: int, new_password: str) -> bool:
        """
        Reset a user's password.
        
        Args:
            user_id: User ID
            new_password: New password
            
        Returns:
            bool: True if password reset successful, False otherwise
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return False
                
            # Update password
            user.password_hash = self.get_password_hash(new_password)
            user.reset_token = None
            user.reset_token_expires = None
            self.db.commit()
            
            logger.info(f"Password reset for user {user.username}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error resetting password: {str(e)}")
            return False
    
    def generate_verification_token(self, user_id: int) -> str:
        """
        Generate an email verification token
        
        Args:
            user_id: User ID
            
        Returns:
            str: Verification token
        """
        # Generate random token
        verification_token = secrets.token_urlsafe(32)
        
        # Get user and update token fields
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.verification_token = verification_token
            user.verification_token_expires = datetime.utcnow() + timedelta(days=3)  # Longer expiry for verification
            self.db.commit()
        
        return verification_token
    
    def validate_verification_token(self, token: str) -> Optional[int]:
        """
        Validate a verification token and return user ID if valid
        
        Args:
            token: Verification token
            
        Returns:
            Optional[int]: User ID if token is valid, None otherwise
        """
        # Find user with this token
        user = self.db.query(User).filter(
            User.verification_token == token,
            User.verification_token_expires > datetime.utcnow()
        ).first()
        
        if not user:
            return None
            
        # Update user verification status
        user.is_verified = True
        user.verification_token = None
        user.verification_token_expires = None
        self.db.commit()
        
        return user.id 