from contextlib import contextmanager
from typing import List, Optional, Type, TypeVar
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.sql import func
from datetime import datetime, timezone
import logging
import sys
from database import SessionLocal, Base
from models import Adam 

# Generic type for SQLAlchemy models
ModelType = TypeVar("ModelType")


class DatabaseManager:
    """
    A comprehensive database manager class for secure and efficient database operations.
    Provides methods for CRUD operations, complex queries, and transaction management.
    """
    
    def __init__(self):
        """Initialize the DatabaseManager."""
        self.session_factory = SessionLocal
    
    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions.
        Ensures proper session cleanup and error handling.
        """
        session = self.session_factory()
        try:
            yield session
        except SQLAlchemyError as e:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.
        Automatically commits on success or rolls back on error.
        """
        with self.get_session() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
    
    def create(self, model_class: Type[ModelType], **kwargs) -> bool:
        """
        Create a new record in the database.
        
        Args:
            model_class: The SQLAlchemy model class
            **kwargs: Field values for the new record
            
        Returns:
            True if creation was successful, False otherwise
        """
        try:
            with self.transaction() as session:
                instance = model_class(**kwargs)
                session.add(instance)
                session.flush()  # Get the ID before commit
                session.refresh(instance)
                return True
        except IntegrityError as e:
            return False
        except Exception as e:

            return False
    
    def get_by_id(self, model_class: Type[ModelType], record_id: int) -> Optional[ModelType]:
        """
        Retrieve a record by its ID.
        
        Args:
            model_class: The SQLAlchemy model class
            record_id: The ID of the record to retrieve
            
        Returns:
            The model instance or None if not found
        """
        try:
            with self.get_session() as session:
                return session.query(model_class).filter(model_class.id == record_id).first() # type: ignore
        except Exception as e:
            return None

    def update_adam_record(self, output_realizowane: str, output_oczekuje: str, 
                          output_combined: str, output_nie_dodane: str, output_wykonane: str) -> bool:
        """
        Update the Adam record with id=1 with new values and current timestamp.
        
        Args:
            output_realizowane: Value for realizowane field
            output_oczekuje: Value for oczekuje field
            output_combined: Value for combined field
            output_nie_dodane: Value for nie_dodane field
            output_wykonane: Value for wykonane field
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            # Get current time in UTC
            current_time_utc = datetime.now(timezone.utc)
            
            with self.transaction() as session:
                # Try to update existing record with id=1
                updated_rows = session.query(Adam).filter(Adam.id == 1).update({
                    'created_at': current_time_utc,
                    'realizowane': output_realizowane,
                    'oczekuje': output_oczekuje,
                    'combined': output_combined,
                    'nie_dodane': output_nie_dodane,
                    'wykonane': output_wykonane
                })
                
                # If no record was updated, create a new one with id=1
                if updated_rows == 0:
                    new_record = Adam(
                        id=1,
                        created_at=current_time_utc,
                        realizowane=output_realizowane,
                        oczekuje=output_oczekuje,
                        combined=output_combined,
                        nie_dodane=output_nie_dodane,
                        wykonane=output_wykonane
                    )
                    session.add(new_record)
                
                return True
        except Exception as e:
            logging.error(f"Error updating Adam record: {e}")
            return False