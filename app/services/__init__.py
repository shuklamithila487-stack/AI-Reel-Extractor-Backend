"""
Business logic services.
Exports all service modules for easy importing.
"""

# Services are imported as modules, not individual functions
# This allows for cleaner imports like: from app.services import auth_service

from app.services import (
    auth_service,
    video_service,
    extraction_service,
    cloudinary_service,
    sarvam_service,
    openai_service,
    email_service,
)

__all__ = [
    "auth_service",
    "video_service",
    "extraction_service",
    "cloudinary_service",
    "sarvam_service",
    "openai_service",
    "email_service",
]