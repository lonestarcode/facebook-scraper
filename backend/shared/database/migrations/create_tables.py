"""Database migration script to create initial tables."""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path to import shared modules
parent_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(parent_dir))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import CreateTable

from shared.config.settings import get_settings
from shared.models.base import Base
from shared.models.marketplace import User, Listing, PriceAlert, AlertHistory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("database.migrations")

async def create_tables(database_url: str, drop_existing: bool = False):
    """
    Create database tables.
    
    Args:
        database_url: Database connection URL
        drop_existing: Whether to drop existing tables
    """
    logger.info(f"Connecting to database: {database_url}")
    
    # Create engine
    engine = create_async_engine(
        database_url,
        echo=True
    )
    
    # Import all models to ensure they are registered with Base
    models = [User, Listing, PriceAlert, AlertHistory]
    
    async with engine.begin() as conn:
        if drop_existing:
            logger.warning("Dropping all existing tables")
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.info("Creating tables")
        await conn.run_sync(Base.metadata.create_all)
    
    # Log the SQL for each table
    for table in Base.metadata.sorted_tables:
        create_table_sql = CreateTable(table).compile(engine)
        logger.debug(f"Create table SQL for {table.name}:")
        logger.debug(str(create_table_sql).strip())
    
    logger.info("Tables created successfully")

async def create_sample_data(database_url: str):
    """
    Create sample data for development.
    
    Args:
        database_url: Database connection URL
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.future import select
    import uuid
    from datetime import datetime, timedelta
    
    logger.info("Creating sample data")
    
    # Create engine and session
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    
    async with async_session() as session:
        # Check if data already exists
        result = await session.execute(select(User).limit(1))
        existing_user = result.scalars().first()
        
        if existing_user:
            logger.info("Sample data already exists, skipping")
            return
        
        # Create sample users
        users = [
            User(
                id=uuid.uuid4(),
                username=f"user{i}",
                email=f"user{i}@example.com",
                password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
                first_name=f"User{i}",
                last_name="Test",
                is_active=True,
                is_admin=i == 1,  # First user is admin
                created_at=datetime.utcnow()
            )
            for i in range(1, 4)
        ]
        
        session.add_all(users)
        await session.flush()
        
        # Create sample listings
        listings = [
            Listing(
                id=uuid.uuid4(),
                external_id=f"ext-{uuid.uuid4()}",
                title=f"Sample Listing {i}",
                description=f"This is a sample listing {i} with detailed description.",
                price=100.0 * i,
                currency="USD",
                location="New York, NY",
                seller_name=f"Seller {i}",
                category="furniture" if i % 3 == 0 else "electronics" if i % 3 == 1 else "clothing",
                image_urls=["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
                listing_url=f"https://example.com/listing/{i}",
                listed_date=datetime.utcnow() - timedelta(days=i),
                scraped_date=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                is_sold=False,
                is_deleted=False,
                source="facebook",
                metadata={"condition": "new" if i % 2 == 0 else "used"}
            )
            for i in range(1, 11)
        ]
        
        session.add_all(listings)
        await session.flush()
        
        # Create sample alerts
        alerts = [
            PriceAlert(
                user_id=users[0].id,
                search_term="leather sofa",
                category="furniture",
                min_price=100.0,
                max_price=1000.0,
                location="New York",
                notification_method="email",
                notification_target=users[0].email,
                is_active=True,
                created_at=datetime.utcnow()
            ),
            PriceAlert(
                user_id=users[1].id,
                search_term=None,
                category="electronics",
                min_price=None,
                max_price=500.0,
                location=None,
                notification_method="email",
                notification_target=users[1].email,
                is_active=True,
                created_at=datetime.utcnow()
            ),
            PriceAlert(
                user_id=users[2].id,
                search_term="iphone",
                category=None,
                min_price=None,
                max_price=None,
                location="Los Angeles",
                notification_method="email",
                notification_target=users[2].email,
                is_active=True,
                created_at=datetime.utcnow()
            )
        ]
        
        session.add_all(alerts)
        await session.flush()
        
        # Create sample alert history
        alert_histories = [
            AlertHistory(
                alert_id=alerts[0].id,
                listing_id=listings[0].id,
                triggered_at=datetime.utcnow() - timedelta(hours=i),
                notification_sent=True,
                notification_time=datetime.utcnow() - timedelta(hours=i, minutes=5)
            )
            for i in range(1, 4)
        ]
        
        session.add_all(alert_histories)
        
        # Commit all changes
        await session.commit()
    
    logger.info("Sample data created successfully")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Database migration script")
    parser.add_argument(
        "--drop", 
        action="store_true", 
        help="Drop existing tables before creating new ones"
    )
    parser.add_argument(
        "--sample-data", 
        action="store_true", 
        help="Create sample data after creating tables"
    )
    parser.add_argument(
        "--database-url", 
        help="Database URL (overrides configuration)"
    )
    return parser.parse_args()

async def main():
    """Main entry point."""
    args = parse_args()
    
    # Get settings
    settings = get_settings("api")
    
    # Get database URL
    database_url = args.database_url or settings.database.url
    
    # Create tables
    await create_tables(database_url, args.drop)
    
    # Create sample data if requested
    if args.sample_data:
        await create_sample_data(database_url)

if __name__ == "__main__":
    asyncio.run(main()) 