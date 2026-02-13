"""
Database configuration and session management.
Handles SQLAlchemy engine, session factory, and database utilities.
"""

from typing import Generator
from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ===================================
# DATABASE ENGINE
# ===================================

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    # Use NullPool for serverless environments (optional)
    # poolclass=NullPool if settings.is_production else pool.QueuePool,
)


# ===================================
# SESSION FACTORY
# ===================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# ===================================
# DECLARATIVE BASE
# ===================================

Base = declarative_base()


# ===================================
# DATABASE SESSION DEPENDENCY
# ===================================

def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    Yields:
        Database session
        
    Example:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ===================================
# DATABASE UTILITIES
# ===================================

def init_db():
    """
    Initialize database - create all tables.
    
    WARNING: This should only be used for development/testing.
    In production, use Alembic migrations.
    """
    logger.info("Initializing database tables")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")


def drop_db():
    """
    Drop all database tables.
    
    WARNING: This will delete all data!
    Only use in development/testing.
    """
    logger.warning("Dropping all database tables")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All tables dropped")


def check_db_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        return False


# ===================================
# ROW LEVEL SECURITY (RLS) HELPERS
# ===================================

def set_user_context(db: Session, user_id: str):
    """
    Set user context for row-level security in PostgreSQL.
    
    Args:
        db: Database session
        user_id: User ID to set in context
        
    Example:
        set_user_context(db, current_user.id)
        # Now all queries will be filtered by user_id
    """
    db.execute(
        f"SET LOCAL app.current_user_id = '{user_id}';"
    )
    logger.debug("User context set", user_id=user_id)


def clear_user_context(db: Session):
    """
    Clear user context.
    
    Args:
        db: Database session
    """
    db.execute("RESET app.current_user_id;")
    logger.debug("User context cleared")


# ===================================
# EVENT LISTENERS
# ===================================

@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """
    Event listener for new database connections.
    Useful for setting connection-level settings.
    """
    logger.debug("New database connection established")
    # You can set connection-level parameters here
    # Example: dbapi_conn.execute("SET timezone TO 'UTC'")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """
    Event listener when connection is checked out from pool.
    Useful for logging pool usage.
    """
    logger.debug("Connection checked out from pool")


# ===================================
# TRANSACTION HELPERS
# ===================================

class TransactionContext:
    """
    Context manager for database transactions with automatic rollback on error.
    
    Example:
        with TransactionContext(db) as session:
            session.add(user)
            session.add(video)
            # Commits automatically on success, rolls back on error
    """
    
    def __init__(self, db: Session):
        """
        Initialize transaction context.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def __enter__(self) -> Session:
        """Start transaction."""
        return self.db
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Commit or rollback transaction.
        
        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        if exc_type is not None:
            # Exception occurred, rollback
            logger.warning("Transaction rolled back", error=str(exc_val))
            self.db.rollback()
        else:
            # No exception, commit
            try:
                self.db.commit()
                logger.debug("Transaction committed")
            except Exception as e:
                logger.error("Transaction commit failed", error=str(e))
                self.db.rollback()
                raise


# ===================================
# PAGINATION HELPER
# ===================================

def paginate_query(
    query,
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = 100
):
    """
    Paginate a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        page_size: Items per page
        max_page_size: Maximum allowed page size
        
    Returns:
        Tuple of (items, total_count, page, page_size)
    """
    # Validate inputs
    page = max(1, page)
    page_size = min(max(1, page_size), max_page_size)
    
    # Get total count
    total_count = query.count()
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Get paginated items
    items = query.limit(page_size).offset(offset).all()
    
    return items, total_count, page, page_size


# ===================================
# DATABASE HEALTH CHECK
# ===================================

def get_db_health() -> dict:
    """
    Get database health status.
    
    Returns:
        Dictionary with health information
    """
    try:
        with engine.connect() as connection:
            # Execute simple query
            result = connection.execute(text("SELECT 1 as health_check"))
            result.fetchone()
            
            # Get pool status
            pool_status = {
                "size": engine.pool.size(),
                "checked_in": engine.pool.checkedin(),
                "checked_out": engine.pool.checkedout(),
                "overflow": engine.pool.overflow(),
                "total": engine.pool.size() + engine.pool.overflow()
            }
            
            return {
                "status": "healthy",
                "connected": True,
                "pool": pool_status
            }
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }


# ===================================
# EXAMPLE USAGE
# ===================================

if __name__ == "__main__":
    # Test database connection
    print("Testing database connection...")
    if check_db_connection():
        print("✓ Database connection successful")
        
        # Get health status
        health = get_db_health()
        print(f"\nDatabase Health:")
        print(f"  Status: {health['status']}")
        print(f"  Connected: {health['connected']}")
        if 'pool' in health:
            print(f"  Pool Status:")
            print(f"    Total connections: {health['pool']['total']}")
            print(f"    Checked out: {health['pool']['checked_out']}")
            print(f"    Checked in: {health['pool']['checked_in']}")
    else:
        print("✗ Database connection failed")