# Database Documentation

## Overview

This document describes the database schema and design for the Facebook Marketplace Scraper project. The system uses a PostgreSQL database to store user accounts, marketplace listings, alerts, and other application data.

## Database Design

### Entity-Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    Users    │       │   Listings  │       │   Alerts    │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id          │       │ id          │       │ id          │
│ username    │       │ external_id │       │ name        │
│ email       │┌─────►│ title       │◄──────┤ user_id     │
│ password    ││      │ description │       │ criteria    │
│ role        ││      │ price       │       │ query       │
│ created_at  ││      │ currency    │       │ created_at  │
│ updated_at  ││      │ location    │       │ updated_at  │
└─────────────┘│      │ category    │       │ is_active   │
               │      │ subcategory │       └──────┬──────┘
               │      │ seller_id   │              │
               │      │ created_at  │              │
               │      │ updated_at  │              │
               │      │ is_sold     │              │
               │      │ is_deleted  │              │
               │      └─────────────┘              │
               │                                   │
               │       ┌─────────────┐             │
               │       │ Alert Match │             │
               │       ├─────────────┤             │
               └──────►│ id          │◄────────────┘
                       │ user_id     │             
                       │ listing_id  │◄─┐           
                       │ alert_id    │  │           
                       │ matched_at  │  │           
                       │ notified_at │  │  ┌─────────────┐
                       └─────────────┘  │  │  Images     │
                                        │  ├─────────────┤
┌─────────────┐       ┌─────────────┐   │  │ id          │
│ User Auth   │       │ Listing     │   │  │ listing_id  │
├─────────────┤       │ Attributes  │   │  │ url         │
│ id          │       ├─────────────┤   │  │ position    │
│ user_id     │       │ id          │   │  │ created_at  │
│ token       │       │ listing_id  │◄──┘  └─────────────┘
│ type        │       │ key         │      
│ expires_at  │       │ value       │      
│ created_at  │       │ created_at  │      
└─────────────┘       └─────────────┘      
```

## Table Schemas

### Users

Stores user account information.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
```

### User Authentication

Stores authentication tokens for users.

```sql
CREATE TABLE user_auth (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL,
    token_type VARCHAR(20) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    device_info JSONB,
    ip_address VARCHAR(45),
    UNIQUE (user_id, token)
);

CREATE INDEX idx_user_auth_token ON user_auth(token);
CREATE INDEX idx_user_auth_user_id ON user_auth(user_id);
```

### Listings

Stores marketplace listings.

```sql
CREATE TABLE listings (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    location VARCHAR(255),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    seller_name VARCHAR(100),
    seller_id VARCHAR(100),
    listing_url TEXT NOT NULL,
    listed_date TIMESTAMP,
    scraped_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50) NOT NULL,
    is_sold BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (external_id, source)
);

CREATE INDEX idx_listings_external_id ON listings(external_id);
CREATE INDEX idx_listings_category ON listings(category);
CREATE INDEX idx_listings_price ON listings(price);
CREATE INDEX idx_listings_location ON listings(location);
CREATE INDEX idx_listings_scraped_date ON listings(scraped_date);
CREATE INDEX idx_listings_source ON listings(source);
```

### Listing Attributes

Stores additional attributes for listings in a key-value format.

```sql
CREATE TABLE listing_attributes (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    key VARCHAR(100) NOT NULL,
    value TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_listing_attributes_listing_id ON listing_attributes(listing_id);
CREATE INDEX idx_listing_attributes_key ON listing_attributes(key);
```

### Images

Stores listing images.

```sql
CREATE TABLE images (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    width INTEGER,
    height INTEGER,
    size INTEGER,
    format VARCHAR(10),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_images_listing_id ON images(listing_id);
```

### Alerts

Stores user-defined alerts for marketplace listings.

```sql
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    criteria JSONB NOT NULL,
    query VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_checked TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    notification_settings JSONB NOT NULL DEFAULT '{"email": true, "push": false, "frequency": "instant"}'
);

CREATE INDEX idx_alerts_user_id ON alerts(user_id);
```

### Alert Matches

Tracks matches between alerts and listings.

```sql
CREATE TABLE alert_matches (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    matched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notified_at TIMESTAMP,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    is_saved BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (alert_id, listing_id)
);

CREATE INDEX idx_alert_matches_alert_id ON alert_matches(alert_id);
CREATE INDEX idx_alert_matches_listing_id ON alert_matches(listing_id);
CREATE INDEX idx_alert_matches_user_id ON alert_matches(user_id);
```

### Notifications

Stores notifications for users.

```sql
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    read_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);
CREATE INDEX idx_notifications_status ON notifications(status);
```

## Database Access Patterns

### ORM Implementation

The application uses SQLAlchemy as the ORM layer. Models are defined in the `backend/shared/models/` directory.

Example model definition:

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.shared.models.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")
    first_name = Column(String(100))
    last_name = Column(String(100))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, nullable=False, default=True)
    
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    matches = relationship("AlertMatch", back_populates="user", cascade="all, delete-orphan")
    auth_tokens = relationship("UserAuth", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
```

### Database Access Repositories

Data access is encapsulated in repository classes located in each service's `repositories` directory. These classes provide type-safe, reusable database operations.

Example repository:

```python
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.future import select

from backend.shared.models.marketplace import Listing
from backend.shared.pagination import Pagination, PaginatedResult

class ListingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, listing_id: int) -> Optional[Listing]:
        result = await self.session.execute(
            select(Listing).where(Listing.id == listing_id)
        )
        return result.scalars().first()
    
    async def get_by_external_id(self, external_id: str, source: str) -> Optional[Listing]:
        result = await self.session.execute(
            select(Listing).where(
                Listing.external_id == external_id,
                Listing.source == source
            )
        )
        return result.scalars().first()
    
    async def search(
        self, 
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        location: Optional[str] = None,
        query: Optional[str] = None,
        pagination: Pagination = Pagination()
    ) -> PaginatedResult[Listing]:
        # Implementation of search with pagination
        # ...
```

## Migrations

The system uses Alembic for database migrations. Migration scripts are stored in the `backend/migrations/versions/` directory with the main configuration in `backend/alembic.ini`.

### Migration Setup

The project uses a structured migration system with:

1. `alembic.ini` - Contains database connection settings and migration configuration
2. `migrations/env.py` - Configures the migration environment and imports all models
3. `migrations/script.py.mako` - Template for new migration files
4. `migrations/versions/` - Directory containing individual migration scripts

The initial database schema is defined in `migrations/versions/initial_migration.py`.

### Creating Migrations

To create a new migration:

```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

This will automatically detect changes in your SQLAlchemy models and generate a new migration script.

### Running Migrations

To apply all pending migrations:

```bash
# Apply all migrations
alembic upgrade head

# Apply specific number of migrations
alembic upgrade +2

# Upgrade to a specific migration
alembic upgrade 001_initial
```

To roll back migrations:

```bash
# Roll back one migration
alembic downgrade -1

# Roll back to a specific migration
alembic downgrade 001_initial

# Roll back all migrations
alembic downgrade base
```

### Migration Best Practices

1. **Review autogenerated migrations** - Always review the autogenerated migration files before applying them to ensure they accurately reflect your intended changes
2. **Test migrations** - Test migrations on a staging environment before applying to production
3. **Version control** - Keep all migration files in version control
4. **Include data migrations** - When schema changes require data transformations, include them in the migration script
5. **Don't modify existing migrations** - Create new migrations instead of modifying existing ones

### Migration Environment

The migration environment in `migrations/env.py` is configured to:

1. Import all models to ensure they're included in metadata
2. Support overriding the database URL via environment variables
3. Apply appropriate database-specific dialect options
4. Handle both online and offline migration modes

## Database Optimization

### Indexing Strategy

The system uses the following indexing strategies:

1. Primary key indices on all tables
2. Foreign key indices on all reference columns
3. Indices on frequently queried columns (e.g., email, username)
4. Composite indices for multi-column queries

### Performance Considerations

1. **Connection Pooling**: The application uses SQLAlchemy's connection pooling to efficiently manage database connections
2. **Pagination**: All list endpoints use pagination to limit result set size
3. **Query Optimization**: Complex queries use joins instead of multiple separate queries
4. **Caching**: Frequently accessed data can be cached in Redis

## Data Security

### Sensitive Data

The following data is considered sensitive:

1. User passwords (stored as hashes, never in plaintext)
2. Authentication tokens
3. User personal information

### Database Security Measures

1. **Encryption**: Sensitive fields are encrypted at rest
2. **Role-Based Access**: Database users have limited permissions
3. **Least Privilege**: Application connections use the least privilege required
4. **Audit Logging**: Database changes are logged for security auditing

## Backup and Recovery

See the [Deployment Documentation](deployment.md) for detailed information on backup and recovery procedures.

## Related Documentation

- [Architecture Overview](architecture.md)
- [Deployment Guide](deployment.md)
- [Security Documentation](security.md)
