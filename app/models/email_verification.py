"""
Email verification model for account activation.
"""

from datetime import datetime, timedelta
from sqlalchemy import (
    Column, String, DateTime, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class EmailVerification(Base):
    """
    Email verification model for account activation.
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        token: Unique verification token
        email: Email address being verified
        expires_at: Token expiration timestamp
        verified_at: Verification completion timestamp
        created_at: Token creation timestamp
    """
    
    __tablename__ = "email_verifications"
    
    # ===================================
    # PRIMARY KEY
    # ===================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # ===================================
    # FOREIGN KEYS
    # ===================================
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # ===================================
    # TOKEN DATA
    # ===================================
    token = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False)
    
    # ===================================
    # EXPIRATION
    # ===================================
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # ===================================
    # VERIFICATION STATUS
    # ===================================
    verified_at = Column(DateTime, nullable=True)
    
    # ===================================
    # TIMESTAMPS
    # ===================================
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # ===================================
    # RELATIONSHIPS
    # ===================================
    user = relationship("User", back_populates="email_verifications")
    
    # ===================================
    # METHODS
    # ===================================
    def __repr__(self):
        return f"<EmailVerification(id={self.id}, email={self.email}, verified={self.is_verified})>"
    
    def to_dict(self):
        """Convert email verification to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "email": self.email,
            "is_verified": self.is_verified,
            "is_expired": self.is_expired,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }
    
    @property
    def is_verified(self) -> bool:
        """Check if email has been verified."""
        return self.verified_at is not None
    
    @property
    def is_expired(self) -> bool:
        """Check if verification token has expired."""
        if self.expires_at is None:
            return True
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not verified and not expired)."""
        return not self.is_verified and not self.is_expired
    
    def mark_verified(self):
        """Mark email as verified."""
        if not self.is_verified:
            self.verified_at = datetime.utcnow()
    
    @classmethod
    def create_verification(cls, user_id: uuid.UUID, email: str, token: str, hours: int = 24):
        """
        Create a new email verification record.
        
        Args:
            user_id: User UUID
            email: Email to verify
            token: Verification token
            hours: Expiration hours (default 24)
            
        Returns:
            EmailVerification instance
        """
        return cls(
            user_id=user_id,
            email=email,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=hours)
        )