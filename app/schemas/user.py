"""
User profile and settings Pydantic schemas.
"""

from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


# Shared properties
class UserBase(BaseModel):
    """
    Base user schema with common fields.
    """
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    profile_photo_url: Optional[str] = None
    timezone: Optional[str] = "Asia/Kolkata"
    language: Optional[str] = "en"
    notify_processing_complete: Optional[bool] = True
    notify_processing_failed: Optional[bool] = True
    notify_weekly_summary: Optional[bool] = False
    notify_product_updates: Optional[bool] = False


# Properties to receive via API on creation
class UserCreate(UserBase):
    """
    User creation schema (internal use).
    """
    password: str
    
    # Required for MVP as per UI designs? Or optional?
    # Usually name/email/pass are required.
    full_name: str


# Properties to receive via API on update
class UserUpdate(BaseModel):
    """
    User profile update schema.
    """
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    company_name: Optional[str] = Field(None, max_length=255)
    profile_photo_url: Optional[str] = None
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "full_name": "John Doe",
                "phone": "+91-9876543210",
                "company_name": "Acme Real Estate",
                "timezone": "Asia/Kolkata",
                "language": "en"
            }]
        }
    }


# Properties available for API responses
class UserResponse(UserBase):
    """
    User response schema (public data only).
    """
    id: UUID
    email_verified: bool
    account_status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "phone": "+91-9876543210",
                "company_name": "Acme Real Estate",
                "timezone": "Asia/Kolkata",
                "language": "en",
                "email_verified": True,
                "account_status": "active",
                "created_at": "2026-01-01T00:00:00Z",
                "last_login_at": "2026-02-13T00:00:00Z"
            }]
        }
    }


class UserProfileResponse(UserResponse):
    """
    Extended user profile with additional details.
    """
    # Statistics
    total_videos: Optional[int] = 0
    total_extractions: Optional[int] = 0


class NotificationPreferences(BaseModel):
    """
    User notification preferences.
    """
    notify_processing_complete: bool = True
    notify_processing_failed: bool = True
    notify_weekly_summary: bool = False
    notify_product_updates: bool = False
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "notify_processing_complete": True,
                "notify_processing_failed": True,
                "notify_weekly_summary": False,
                "notify_product_updates": False
            }]
        }
    }


class UserStats(BaseModel):
    """
    User usage statistics.
    """
    videos_uploaded: int
    videos_completed: int
    videos_failed: int
    total_extractions: int
    last_upload_at: Optional[datetime] = None
    last_extraction_at: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True
    }


class UserListItem(BaseModel):
    """
    User item in list (minimal info).
    """
    id: UUID
    email: str
    full_name: Optional[str] = None
    email_verified: bool
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class AccountStatusUpdate(BaseModel):
    """
    Update account status (admin only).
    """
    account_status: str = Field(
        description="Account status: active, suspended, deleted"
    )
    
    @field_validator('account_status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate account status."""
        allowed = ['active', 'suspended', 'deleted']
        if v not in allowed:
            raise ValueError(f'Status must be one of: {", ".join(allowed)}')
        return v