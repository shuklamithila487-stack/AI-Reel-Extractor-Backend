"""
User model for authentication and profile management.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class User(Base):
    """
    User model for authentication and profile.
    """
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    company_name = Column(String(255), nullable=True)
    profile_photo_url = Column(Text, nullable=True)
    
    # Settings
    timezone = Column(String(50), default="Asia/Kolkata")
    language = Column(String(10), default="en")
    
    # Notification preferences
    notify_processing_complete = Column(Boolean, default=True)
    notify_processing_failed = Column(Boolean, default=True)
    notify_weekly_summary = Column(Boolean, default=False)
    notify_product_updates = Column(Boolean, default=False)
    
    # Account status
    email_verified = Column(Boolean, default=False)
    account_status = Column(String(20), default="active", index=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    email_verified_at = Column(DateTime, nullable=True)
    
    # Relationships
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
    extractions = relationship("Extraction", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    email_verifications = relationship("EmailVerification", back_populates="user", cascade="all, delete-orphan")
    password_resets = relationship("PasswordReset", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
    
    def is_active(self) -> bool:
        """Check if account is active."""
        return self.account_status == "active"
    
    def is_locked(self) -> bool:
        """Check if account is locked."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    def can_login(self) -> bool:
        """Check if user can login."""
        return self.is_active() and not self.is_locked() and self.email_verified
    
    def increment_failed_login(self, max_attempts: int = 5) -> bool:
        """Increment failed login attempts and lock if needed."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            from datetime import timedelta
            self.locked_until = datetime.utcnow() + timedelta(minutes=15)
            return True
        return False
    
    def reset_failed_login(self):
        """Reset failed login attempts."""
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def verify_email(self):
        """Mark email as verified."""
        self.email_verified = True
        self.email_verified_at = datetime.utcnow()
    
    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert to dictionary (exclude sensitive fields)."""
        return {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }