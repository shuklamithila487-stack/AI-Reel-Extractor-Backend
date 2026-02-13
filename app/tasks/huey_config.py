"""
Huey configuration for background task processing.
Uses PostgreSQL as the storage backend (no Redis needed).
"""

from huey import SqliteHuey
try:
    # Try importing SqlHuey which supports PostgreSQL via peewee
    from huey.contrib.sql_huey import SqlHuey
    from peewee import PostgresqlDatabase
except ImportError:
    # Fallback to Sqlite if peewee not available
    SqlHuey = None
    PostgresqlDatabase = None

from app.core.config import settings
from app.core.logging import get_logger
import urllib.parse

logger = get_logger(__name__)


def create_huey_instance():
    """
    Create Huey instance based on configuration.
    Uses PostgreSQL for production, SQLite for development.
    """
    
    if settings.HUEY_BACKEND == "postgresql" and SqlHuey and PostgresqlDatabase:
        # Parse DATABASE_URL to get connection parameters
        # Format: postgresql://user:password@host:port/database
        try:
            parsed = urllib.parse.urlparse(settings.DATABASE_URL)
            
            # Create PEWEE database instance
            db = PostgresqlDatabase(
                parsed.path.lstrip('/'),  # database name
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
            )
            
            # Initialize Huey with SqlHuey
            huey = SqlHuey(
                name=settings.HUEY_NAME,
                database=db,
                immediate=settings.HUEY_IMMEDIATE,  # Run immediately in tests
            )
            
            logger.info(
                "Huey initialized with PostgreSQL",
                database=parsed.path.lstrip('/'),
                host=parsed.hostname
            )
            
            return huey
            
        except Exception as e:
            logger.error("Failed to initialize Huey with PostgreSQL", error=str(e))
            # Fallback to SQLite for development
            logger.warning("Falling back to SQLite for Huey")
            return SqliteHuey(
                name=settings.HUEY_NAME,
                filename='/tmp/huey.db',
                immediate=settings.HUEY_IMMEDIATE
            )
    
    else:
        # SQLite backend (development only)
        if settings.HUEY_BACKEND == "postgresql" and not SqlHuey:
            logger.warning("PostgreSQL backend requested but huey[postgres] dependencies missing. Using SQLite.")
            
        huey = SqliteHuey(
            name=settings.HUEY_NAME,
            filename='/tmp/huey.db',
            immediate=settings.HUEY_IMMEDIATE
        )
        
        logger.info("Huey initialized with SQLite")
        
        return huey


# Create global Huey instance
huey = create_huey_instance()


# Huey task decorators
def task(*args, **kwargs):
    """
    Task decorator with default settings.
    
    Usage:
        @task()
        def my_task():
            pass
    """
    # Set default retry settings
    kwargs.setdefault('retries', 3)
    kwargs.setdefault('retry_delay', 60)  # 60 seconds
    
    return huey.task(*args, **kwargs)


def periodic_task(*args, **kwargs):
    """
    Periodic task decorator.
    
    Usage:
        @periodic_task(crontab(hour='0', minute='0'))
        def daily_task():
            pass
    """
    return huey.periodic_task(*args, **kwargs)