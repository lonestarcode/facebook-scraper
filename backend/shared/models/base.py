"""Base model for SQLAlchemy ORM."""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.declarative import declared_attr


class Base:
    """
    Base model class for SQLAlchemy models.
    
    Provides:
    - Auto-generated table names (pluralized class name)
    - Common columns (id, created_at, updated_at)
    """
    
    @declared_attr
    def __tablename__(cls):
        """
        Generate table name automatically.
        
        Converts CamelCase class name to snake_case plural.
        Example: UserProfile -> user_profiles
        """
        import re
        # Convert camel case to snake case
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        # Pluralize (simple version, not handling irregular plurals)
        if not name.endswith('s'):
            name += 's'
        return name
    
    # Auto-incrementing primary key column
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Automatic timestamp columns
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    @classmethod
    def columns(cls):
        """Get all column names for the model."""
        return [c.name for c in cls.__table__.columns]
    
    def to_dict(self):
        """Convert model instance to dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def __repr__(self):
        """String representation of the model."""
        values = ', '.join(
            f"{c.name}={getattr(self, c.name)!r}" 
            for c in self.__table__.columns[:3]
        )
        return f"<{self.__class__.__name__}({values})>" 