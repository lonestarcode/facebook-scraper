"""Database session management for the API service."""

import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from shared.config.settings import get_settings

# Get settings
settings = get_settings("api")

# Configure logging
logger = logging.getLogger("api.database")

# Create the SQLAlchemy engine
engine = create_engine(
    settings.database.url,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_timeout=settings.database.pool_timeout,
    pool_recycle=settings.database.pool_recycle,
    echo=settings.database.echo,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """
    Get a database session.
    
    This function is used as a dependency in FastAPI route functions.
    It yields a database session and ensures it is closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Get a database session as a context manager.
    
    This function is used in non-FastAPI contexts where a dependency
    can't be used, such as background tasks or scripts.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize the database.
    
    This function creates all tables if they don't exist.
    It's meant to be called during application startup.
    """
    try:
        # Import all models to ensure they are registered with the Base
        from shared.models.marketplace import Listing, PriceAlert, User
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise 