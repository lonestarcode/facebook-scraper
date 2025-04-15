from passlib.context import CryptContext
import secrets
import string
from typing import Tuple

# Configure the password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password matches hash, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def generate_password(length: int = 12) -> str:
    """
    Generate a secure random password
    
    Args:
        length: Length of the password to generate
        
    Returns:
        Securely generated random password
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    # Ensure password has at least one uppercase, lowercase, digit and special character
    if (any(c.islower() for c in password) 
        and any(c.isupper() for c in password) 
        and any(c.isdigit() for c in password)
        and any(c in "!@#$%^&*()" for c in password)):
        return password
    
    # If criteria not met, generate again
    return generate_password(length)


def generate_reset_token() -> str:
    """
    Generate a secure token for password reset
    
    Returns:
        Secure token string
    """
    return secrets.token_urlsafe(32)


def is_password_strong(password: str) -> Tuple[bool, str]:
    """
    Check if a password is strong enough
    
    Args:
        password: Password to check
    
    Returns:
        Tuple of (is_valid, message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/~`" for c in password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong" 