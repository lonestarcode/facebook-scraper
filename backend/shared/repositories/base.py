from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import Session

from shared.database.session import get_db_session
from shared.utils.logging_config import get_logger

logger = get_logger(__name__)

# Type variable for the model class
ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, model_class: Type[ModelType]):
        """
        Initialize with the model class.
        
        Args:
            model_class: SQLAlchemy model class
        """
        self.model_class = model_class
    
    def get_by_id(self, id_value: Union[int, str], db_session: Optional[Session] = None) -> Optional[ModelType]:
        """
        Get a record by its ID.
        
        Args:
            id_value: ID value of the record
            db_session: Optional database session
            
        Returns:
            Record if found, otherwise None
        """
        with db_session or get_db_session() as session:
            return session.get(self.model_class, id_value)
    
    def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        db_session: Optional[Session] = None
    ) -> List[ModelType]:
        """
        Get all records with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            db_session: Optional database session
            
        Returns:
            List of records
        """
        with db_session or get_db_session() as session:
            query = select(self.model_class).offset(skip).limit(limit)
            return list(session.execute(query).scalars().all())
    
    def count(self, db_session: Optional[Session] = None) -> int:
        """
        Count the total number of records.
        
        Args:
            db_session: Optional database session
            
        Returns:
            Count of records
        """
        with db_session or get_db_session() as session:
            query = select(func.count()).select_from(self.model_class)
            return session.execute(query).scalar() or 0
    
    def create(self, obj_data: Dict[str, Any], db_session: Optional[Session] = None) -> ModelType:
        """
        Create a new record.
        
        Args:
            obj_data: Data for the new record
            db_session: Optional database session
            
        Returns:
            Created record
        """
        with db_session or get_db_session() as session:
            db_obj = self.model_class(**obj_data)
            session.add(db_obj)
            session.commit()
            session.refresh(db_obj)
            return db_obj
    
    def update(
        self, 
        id_value: Union[int, str], 
        obj_data: Dict[str, Any], 
        db_session: Optional[Session] = None
    ) -> Optional[ModelType]:
        """
        Update a record by ID.
        
        Args:
            id_value: ID of the record to update
            obj_data: New data for the record
            db_session: Optional database session
            
        Returns:
            Updated record if found, otherwise None
        """
        with db_session or get_db_session() as session:
            db_obj = session.get(self.model_class, id_value)
            if db_obj is None:
                return None
                
            # Update fields
            for key, value in obj_data.items():
                if hasattr(db_obj, key):
                    setattr(db_obj, key, value)
            
            session.commit()
            session.refresh(db_obj)
            return db_obj
    
    def delete(self, id_value: Union[int, str], db_session: Optional[Session] = None) -> bool:
        """
        Delete a record by ID.
        
        Args:
            id_value: ID of the record to delete
            db_session: Optional database session
            
        Returns:
            True if deleted, False if not found
        """
        with db_session or get_db_session() as session:
            db_obj = session.get(self.model_class, id_value)
            if db_obj is None:
                return False
                
            session.delete(db_obj)
            session.commit()
            return True
    
    def exists(self, id_value: Union[int, str], db_session: Optional[Session] = None) -> bool:
        """
        Check if a record with the given ID exists.
        
        Args:
            id_value: ID to check
            db_session: Optional database session
            
        Returns:
            True if exists, False otherwise
        """
        with db_session or get_db_session() as session:
            query = select(func.count()).select_from(self.model_class).where(
                self.model_class.id == id_value
            )
            return session.execute(query).scalar() > 0
    
    def bulk_create(self, objects_data: List[Dict[str, Any]], db_session: Optional[Session] = None) -> List[ModelType]:
        """
        Create multiple records in bulk.
        
        Args:
            objects_data: List of data dictionaries for new records
            db_session: Optional database session
            
        Returns:
            List of created records
        """
        with db_session or get_db_session() as session:
            db_objs = [self.model_class(**data) for data in objects_data]
            session.add_all(db_objs)
            session.commit()
            for obj in db_objs:
                session.refresh(obj)
            return db_objs 