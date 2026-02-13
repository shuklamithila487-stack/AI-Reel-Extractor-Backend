"""
Base model imports for Alembic auto-generation.

Import all models here so Alembic can detect them for migrations.
"""

from app.db.database import Base

# Import all models
from app.models.user import User
from app.models.video import Video
from app.models.extraction import Extraction
from app.models.notification import Notification
from app.models.email_verification import EmailVerification
from app.models.password_reset import PasswordReset
from app.models.usage_stats import UsageStats

# This allows Alembic to auto-detect all models
__all__ = [
    "Base",
    "User",
    "Video",
    "Extraction",
    "Notification",
    "EmailVerification",
    "PasswordReset",
    "UsageStats",
]