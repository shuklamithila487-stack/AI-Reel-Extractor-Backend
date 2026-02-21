"""
Logging configuration for the application.
Uses structlog for structured logging with context.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.stdlib import BoundLogger

from app.core.config import settings

try:
    from sentry_sdk.integrations.logging import LoggingIntegration
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False



# ===================================
# STRUCTLOG PROCESSORS
# ===================================

def add_app_context(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    Add application context to log entries.
    
    Args:
        logger: Logger instance
        method_name: Logging method name
        event_dict: Event dictionary
        
    Returns:
        Updated event dictionary
    """
    event_dict["app"] = settings.APP_NAME
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def drop_color_message_key(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    Remove color_message key from event dict (used by ConsoleRenderer).
    
    Args:
        logger: Logger instance
        method_name: Logging method name
        event_dict: Event dictionary
        
    Returns:
        Updated event dictionary
    """
    event_dict.pop("color_message", None)
    return event_dict


# ===================================
# LOGGING CONFIGURATION
# ===================================

def configure_logging():
    """
    Configure application logging with structlog.
    """
    # Set log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Silence noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Structlog processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_app_context,
    ]
    
    # Add Sentry processor if available
    if SENTRY_AVAILABLE and settings.SENTRY_DSN:
        from structlog_sentry import SentryProcessor
        shared_processors.append(SentryProcessor(level=logging.ERROR))

    
    # Choose renderer based on environment
    if settings.is_development:
        # Pretty console output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        # JSON output for production (better for log aggregation)
        processors = shared_processors + [
            drop_color_message_key,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ===================================
# LOGGER GETTER
# ===================================

def get_logger(name: str = None) -> BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured structlog logger
    """
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()


# ===================================
# CONTEXT MANAGERS
# ===================================

class LogContext:
    """
    Context manager for adding temporary logging context.
    
    Example:
        with LogContext(user_id="123", request_id="abc"):
            logger.info("Processing request")
    """
    
    def __init__(self, **kwargs):
        """
        Initialize log context.
        
        Args:
            **kwargs: Key-value pairs to add to logging context
        """
        self.context = kwargs
        self.token = None
    
    def __enter__(self):
        """Enter context manager."""
        structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        structlog.contextvars.unbind_contextvars(*self.context.keys())


# ===================================
# LOGGING DECORATORS
# ===================================

def log_execution_time(logger: BoundLogger = None):
    """
    Decorator to log function execution time.
    
    Args:
        logger: Logger instance (creates one if not provided)
        
    Example:
        @log_execution_time()
        def slow_function():
            time.sleep(1)
    """
    import time
    from functools import wraps
    
    if logger is None:
        logger = get_logger(__name__)
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    "function_executed",
                    function=func.__name__,
                    duration_seconds=round(duration, 3),
                    success=True
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "function_failed",
                    function=func.__name__,
                    duration_seconds=round(duration, 3),
                    error=str(e),
                    success=False
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    "function_executed",
                    function=func.__name__,
                    duration_seconds=round(duration, 3),
                    success=True
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "function_failed",
                    function=func.__name__,
                    duration_seconds=round(duration, 3),
                    error=str(e),
                    success=False
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# ===================================
# HELPER FUNCTIONS
# ===================================

def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: str = None,
    logger: BoundLogger = None
):
    """
    Log HTTP request details.
    
    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        user_id: User ID (if authenticated)
        logger: Logger instance
    """
    if logger is None:
        logger = get_logger(__name__)
    
    log_data = {
        "event": "http_request",
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2)
    }
    
    if user_id:
        log_data["user_id"] = user_id
    
    # Log level based on status code
    if status_code >= 500:
        logger.error(**log_data)
    elif status_code >= 400:
        logger.warning(**log_data)
    else:
        logger.info(**log_data)


def log_background_task(
    task_name: str,
    task_id: str,
    status: str,
    duration_seconds: float = None,
    error: str = None,
    logger: BoundLogger = None
):
    """
    Log background task execution.
    
    Args:
        task_name: Name of the task
        task_id: Task ID
        status: Task status (started, completed, failed)
        duration_seconds: Task duration
        error: Error message (if failed)
        logger: Logger instance
    """
    if logger is None:
        logger = get_logger(__name__)
    
    log_data = {
        "event": "background_task",
        "task_name": task_name,
        "task_id": task_id,
        "status": status
    }
    
    if duration_seconds is not None:
        log_data["duration_seconds"] = round(duration_seconds, 2)
    
    if error:
        log_data["error"] = error
        logger.error(**log_data)
    elif status == "failed":
        logger.error(**log_data)
    else:
        logger.info(**log_data)


def log_api_call(
    service: str,
    endpoint: str,
    status_code: int,
    duration_ms: float,
    error: str = None,
    logger: BoundLogger = None
):
    """
    Log external API call.
    
    Args:
        service: Service name (e.g., 'sarvam', 'claude', 'cloudinary')
        endpoint: API endpoint
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        error: Error message (if failed)
        logger: Logger instance
    """
    if logger is None:
        logger = get_logger(__name__)
    
    log_data = {
        "event": "external_api_call",
        "service": service,
        "endpoint": endpoint,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2)
    }
    
    if error:
        log_data["error"] = error
        logger.error(**log_data)
    elif status_code >= 400:
        logger.warning(**log_data)
    else:
        logger.info(**log_data)


# ===================================
# INITIALIZE LOGGING ON IMPORT
# ===================================

# Configure logging when module is imported
configure_logging()


# ===================================
# EXAMPLE USAGE
# ===================================

if __name__ == "__main__":
    # Get logger
    logger = get_logger(__name__)
    
    # Basic logging
    logger.info("Application started", version="1.0.0")
    logger.debug("Debug message", some_data={"key": "value"})
    logger.warning("Warning message", user_id="123")
    logger.error("Error occurred", error="Something went wrong")
    
    # Using context
    with LogContext(request_id="abc-123", user_id="user-456"):
        logger.info("Processing request")
        logger.info("Request completed")
    
    # Log HTTP request
    log_request(
        method="POST",
        path="/api/v1/videos/upload",
        status_code=200,
        duration_ms=150.5,
        user_id="user-123"
    )
    
    # Log background task
    log_background_task(
        task_name="process_video",
        task_id="task-789",
        status="completed",
        duration_seconds=45.3
    )
    
    # Log API call
    log_api_call(
        service="claude",
        endpoint="/v1/messages",
        status_code=200,
        duration_ms=1250.8
    )