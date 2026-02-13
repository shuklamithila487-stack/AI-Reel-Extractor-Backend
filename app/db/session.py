"""
Database session utilities and helpers.
Provides context managers and helper functions for database operations.
"""

from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, set_user_context, clear_user_context
from app.core.logging import get_logger

logger = get_logger(__name__)


# ===================================
# SESSION CONTEXT MANAGERS
# ===================================

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database session.
    
    Automatically commits on success and rolls back on error.
    
    Example:
        with get_db_session() as db:
            user = db.query(User).first()
            user.name = "New Name"
            # Commits automatically
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error("Database session error", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_session_with_user_context(
    user_id: str
) -> Generator[Session, None, None]:
    """
    Context manager for database session with user context (for RLS).
    
    Sets user context for row-level security before yielding session.
    
    Args:
        user_id: User ID to set in context
        
    Example:
        with get_db_session_with_user_context("user-123") as db:
            # All queries automatically filtered by user_id
            videos = db.query(Video).all()
    
    Yields:
        Database session with user context
    """
    db = SessionLocal()
    try:
        # Set user context for RLS
        set_user_context(db, user_id)
        yield db
        db.commit()
    except Exception as e:
        logger.error(
            "Database session error",
            error=str(e),
            user_id=user_id
        )
        db.rollback()
        raise
    finally:
        clear_user_context(db)
        db.close()


# ===================================
# SESSION HELPERS
# ===================================

def refresh_object(db: Session, obj):
    """
    Refresh an object from the database.
    
    Useful after updates to reload relationships.
    
    Args:
        db: Database session
        obj: SQLAlchemy model instance to refresh
    """
    db.refresh(obj)


def expunge_object(db: Session, obj):
    """
    Expunge an object from the session.
    
    Makes the object detached from the session.
    
    Args:
        db: Database session
        obj: SQLAlchemy model instance to expunge
    """
    db.expunge(obj)


def merge_object(db: Session, obj):
    """
    Merge a detached object back into the session.
    
    Args:
        db: Database session
        obj: Detached SQLAlchemy model instance
        
    Returns:
        Merged object
    """
    return db.merge(obj)


# ===================================
# BULK OPERATIONS
# ===================================

def bulk_insert(db: Session, objects: list):
    """
    Bulk insert objects.
    
    More efficient than individual inserts for large batches.
    
    Args:
        db: Database session
        objects: List of model instances to insert
        
    Example:
        users = [User(email=f"user{i}@example.com") for i in range(100)]
        bulk_insert(db, users)
    """
    try:
        db.bulk_save_objects(objects)
        db.commit()
        logger.info("Bulk insert successful", count=len(objects))
    except Exception as e:
        logger.error("Bulk insert failed", error=str(e), count=len(objects))
        db.rollback()
        raise


def bulk_update(db: Session, mappings: list):
    """
    Bulk update objects.
    
    Args:
        db: Database session
        mappings: List of dictionaries with 'id' and fields to update
        
    Example:
        updates = [
            {"id": 1, "status": "completed"},
            {"id": 2, "status": "completed"}
        ]
        bulk_update(db, updates)
    """
    try:
        db.bulk_update_mappings(mappings)
        db.commit()
        logger.info("Bulk update successful", count=len(mappings))
    except Exception as e:
        logger.error("Bulk update failed", error=str(e), count=len(mappings))
        db.rollback()
        raise


# ===================================
# QUERY HELPERS
# ===================================

def get_or_create(
    db: Session,
    model,
    defaults: Optional[dict] = None,
    **kwargs
):
    """
    Get an existing object or create a new one.
    
    Args:
        db: Database session
        model: SQLAlchemy model class
        defaults: Default values for creation
        **kwargs: Filter parameters
        
    Returns:
        Tuple of (instance, created)
        
    Example:
        user, created = get_or_create(
            db,
            User,
            defaults={"name": "John"},
            email="john@example.com"
        )
    """
    instance = db.query(model).filter_by(**kwargs).first()
    
    if instance:
        return instance, False
    else:
        params = kwargs.copy()
        if defaults:
            params.update(defaults)
        instance = model(**params)
        db.add(instance)
        db.commit()
        db.refresh(instance)
        return instance, True


def update_or_create(
    db: Session,
    model,
    defaults: dict,
    **kwargs
):
    """
    Update an existing object or create a new one.
    
    Args:
        db: Database session
        model: SQLAlchemy model class
        defaults: Values to update/create
        **kwargs: Filter parameters
        
    Returns:
        Tuple of (instance, created)
        
    Example:
        user, created = update_or_create(
            db,
            User,
            defaults={"name": "John Doe"},
            email="john@example.com"
        )
    """
    instance = db.query(model).filter_by(**kwargs).first()
    
    if instance:
        # Update existing
        for key, value in defaults.items():
            setattr(instance, key, value)
        db.commit()
        db.refresh(instance)
        return instance, False
    else:
        # Create new
        params = kwargs.copy()
        params.update(defaults)
        instance = model(**params)
        db.add(instance)
        db.commit()
        db.refresh(instance)
        return instance, True


# ===================================
# SAFE DELETE
# ===================================

def safe_delete(db: Session, obj) -> bool:
    """
    Safely delete an object with error handling.
    
    Args:
        db: Database session
        obj: Object to delete
        
    Returns:
        True if deletion successful, False otherwise
    """
    try:
        db.delete(obj)
        db.commit()
        logger.info("Object deleted", model=obj.__class__.__name__)
        return True
    except Exception as e:
        logger.error(
            "Delete failed",
            error=str(e),
            model=obj.__class__.__name__
        )
        db.rollback()
        return False


# ===================================
# EXAMPLE USAGE
# ===================================

if __name__ == "__main__":
    # Example: Using session context manager
    """
    from app.models import User
    
    # Create a user
    with get_db_session() as db:
        user = User(email="test@example.com", password_hash="hashed")
        db.add(user)
        # Automatically commits
    
    # Query with user context (RLS)
    with get_db_session_with_user_context("user-123") as db:
        videos = db.query(Video).all()
        # Only returns videos owned by user-123
    
    # Get or create
    with get_db_session() as db:
        user, created = get_or_create(
            db,
            User,
            email="john@example.com",
            defaults={"name": "John"}
        )
        print(f"User created: {created}")
    """
    print("Session utilities loaded. See docstrings for usage examples.")