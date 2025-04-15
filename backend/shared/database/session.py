from typing import Generator
import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from shared.config.settings import Settings
from shared.utils.logging_config import get_logger

logger = get_logger(__name__)

# Create declarative base for SQLAlchemy models
Base = declarative_base()

class DatabaseSession:
    """Database session manager for SQLAlchemy."""
    
    def __init__(self, settings: Settings = None):
        """
        Initialize the database session manager.
        
        Args:
            settings: Application settings, if None will be loaded from environment
        """
        self.settings = settings or Settings()
        self.engine = None
        self.session_factory = None
        self._initialize_engine()
    
    def _initialize_engine(self) -> None:
        """Initialize SQLAlchemy engine and session factory."""
        try:
            # Get database URL from settings
            db_url = self.settings.database.url
            
            # Create engine with appropriate pool settings
            self.engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=5,
                max_overflow=10,
                echo=self.settings.database.echo_sql
            )
            
            # Create session factory
            self.session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("Database engine initialized", extra={"db_url": self._mask_db_url(db_url)})
            
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {str(e)}", exc_info=True)
            raise
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic cleanup.
        
        Yields:
            SQLAlchemy session
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}", exc_info=True)
            raise
        finally:
            session.close()
    
    def create_all(self) -> None:
        """Create all tables defined in SQLAlchemy models."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Created all database tables")
    
    def get_session(self) -> Session:
        """
        Get a new database session.
        
        Note: Caller is responsible for committing and closing the session.
        For most cases, use the session() context manager instead.
        
        Returns:
            SQLAlchemy session
        """
        return self.session_factory()
    
    def _mask_db_url(self, db_url: str) -> str:
        """
        Mask sensitive information in database URL for logging.
        
        Args:
            db_url: Database URL to mask
            
        Returns:
            Masked database URL
        """
        if not db_url:
            return ""
            
        try:
            # Simple masking - replace password with ***
            if "@" in db_url and "://" in db_url:
                # Split URL into components
                protocol_part = db_url.split("://")[0]
                auth_part = db_url.split("://")[1].split("@")[0]
                host_part = db_url.split("@")[1]
                
                # Mask password if present
                if ":" in auth_part:
                    username = auth_part.split(":")[0]
                    masked_auth = f"{username}:***"
                else:
                    masked_auth = auth_part
                
                return f"{protocol_part}://{masked_auth}@{host_part}"
            return db_url
        except Exception:
            # In case of parsing error, return a generic masked URL
            return "***MASKED-DB-URL***"

# Global database session instance
db = DatabaseSession()

def get_db() -> DatabaseSession:
    """
    Get the database session manager instance.
    
    Returns:
        Database session manager
    """
    return db

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Get a database session using the global database manager.
    
    This is a convenience function that wraps db.session().
    
    Yields:
        SQLAlchemy session
    """
    with db.session() as session:
        yield session 