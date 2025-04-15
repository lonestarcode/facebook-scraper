import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ARRAY, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel, Field, EmailStr, validator

from .base import Base, PydanticBase


class UserBase(BaseModel):
    """Base User model with common attributes"""
    username: str
    email: EmailStr
    is_active: bool = True
    role: str = "user"  # user, moderator, admin
    permissions: Optional[List[str]] = []
    
    class Config:
        orm_mode = True


class UserCreate(UserBase):
    """User creation model with password"""
    password: str
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserUpdate(BaseModel):
    """User update model with optional fields"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None
    permissions: Optional[List[str]] = None
    password: Optional[str] = None
    
    class Config:
        orm_mode = True


class UserInDB(UserBase):
    """User model as stored in DB with hashed password"""
    id: str
    hashed_password: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True
        
    @classmethod
    def from_orm(cls, db_obj):
        """Convert ORM object to Pydantic model"""
        return cls(
            id=str(db_obj.id),
            username=db_obj.username,
            email=db_obj.email,
            is_active=db_obj.is_active,
            role=db_obj.role,
            permissions=db_obj.permissions,
            hashed_password=db_obj.hashed_password,
            created_at=db_obj.created_at,
            updated_at=db_obj.updated_at
        )


class User(Base):
    """SQLAlchemy User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user")
    permissions = Column(String)  # Stored as JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    @classmethod
    async def get_by_id(cls, user_id: str) -> Optional['User']:
        """Get user by ID"""
        # This is a placeholder - actual implementation will depend on your DB setup
        # Example using SQLAlchemy async:
        # async with async_session() as session:
        #     return await session.get(User, user_id)
        pass
    
    @classmethod
    async def get_by_email(cls, email: str) -> Optional['User']:
        """Get user by email"""
        # This is a placeholder
        pass
    
    @classmethod
    async def get_by_username(cls, username: str) -> Optional['User']:
        """Get user by username"""
        # This is a placeholder
        pass
    
    @property
    def get_permissions(self) -> List[str]:
        """Get user permissions as a list"""
        import json
        if self.permissions:
            return json.loads(self.permissions)
        return []


class UserResponse(PydanticBase):
    """User model for API responses"""
    id: str
    username: str
    email: str
    is_active: bool
    role: str
    permissions: List[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class User(Base):
    """SQLAlchemy model for users"""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=True)
    password_hash = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String(20), default="user")
    permissions = Column(Text, nullable=True)  # Stored as JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    
    # Account status
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)
    
    # Password reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    
    # User metadata
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    last_login = Column(DateTime, nullable=True)
    
    # User preferences
    preferences = Column(Text, nullable=True)  # JSON stored as text
    
    # OAuth integrations
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role == "admin"
    
    @property
    def has_valid_reset_token(self) -> bool:
        """Check if user has a valid reset token"""
        if not self.reset_token or not self.reset_token_expires:
            return False
        return self.reset_token_expires > datetime.utcnow()
    
    @property
    def has_valid_verification_token(self) -> bool:
        """Check if user has a valid verification token"""
        if not self.verification_token or not self.verification_token_expires:
            return False
        return self.verification_token_expires > datetime.utcnow()
        
    def is_token_valid(self, token_type: str) -> bool:
        """
        Check if a specific token is valid.
        
        Args:
            token_type: The type of token to check ("reset" or "verification")
            
        Returns:
            bool: True if the token is valid, False otherwise
        """
        if token_type == "reset":
            return self.has_valid_reset_token
        elif token_type == "verification":
            return self.has_valid_verification_token
        return False
        
    def get_permissions(self) -> List[str]:
        """Get user permissions as a list"""
        # Convert from stored format (JSON string) to list
        import json
        if not self.permissions:
            return []
        try:
            return json.loads(self.permissions)
        except json.JSONDecodeError:
            return []
    
    def verify_password(self, plain_password: str) -> bool:
        """Verify a password against the stored hash"""
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(plain_password, self.password_hash)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate password hash"""
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(password)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user model to dictionary"""
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "role": self.role,
            "permissions": self.get_permissions(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    async def get_by_id(cls, user_id: uuid.UUID) -> Optional["User"]:
        """Get user by ID (async placeholder)"""
        # This would be implemented with the actual database logic
        # For now, it's a placeholder
        return None
    
    @classmethod
    async def get_by_username(cls, username: str) -> Optional["User"]:
        """Get user by username (async placeholder)"""
        # This would be implemented with the actual database logic
        # For now, it's a placeholder
        return None
    
    @classmethod
    async def get_by_email(cls, email: str) -> Optional["User"]:
        """Get user by email (async placeholder)"""
        # This would be implemented with the actual database logic
        # For now, it's a placeholder
        return None 