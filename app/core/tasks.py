import os
from huey import RedisHuey, SqliteHuey, PriorityRedisHuey

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

def get_huey_instance():
    """
    Get or create Huey instance based on configuration.
    """
    if settings.HUEY_BACKEND == "redis":
        return PriorityRedisHuey(
            settings.HUEY_NAME,
            url=settings.REDIS_URL,
            immediate=settings.HUEY_IMMEDIATE,
            results=True,
            store_none=True,
        )
    elif settings.HUEY_BACKEND == "sqlite":
        # Useful for local dev without Redis
        return SqliteHuey(
            filename="huey_db.sqlite",
            immediate=settings.HUEY_IMMEDIATE,
            results=True,
            store_none=True,
        )
    else:
        # Default/Fallback (or if you want to use the immediate mode primarily)
        # Using Sqlite as a safe default if no redis is configured but backend says something else
        return SqliteHuey(
            filename="huey_db.sqlite",
            immediate=settings.HUEY_IMMEDIATE,
        )

# Initialize huey
huey = get_huey_instance()

@huey.on_startup()
def on_startup():
    logger.info("Huey worker started")

@huey.on_shutdown()
def on_shutdown():
    logger.info("Huey worker stopped")
