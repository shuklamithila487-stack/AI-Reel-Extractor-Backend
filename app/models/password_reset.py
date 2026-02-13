"""
Password reset model for password recovery.
"""

from datetime import datetime, timedelta
from sqlalchemy import (
    Column, String, DateTime, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class PasswordReset(Base):
    """
    Password reset model for password recovery.
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        token: Unique reset token
        expires_at: Token expiration timestamp
        used_at: Token usage timestamp
        created_at: Token creation timestamp
    """
    
    __tablename__ = "password_resets"
    
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
    
    # ===================================
    # EXPIRATION
    # ===================================
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # ===================================
    # USAGE STATUS
    # ===================================
    used_at = Column(DateTime, nullable=True)
    
    # ===================================
    # TIMESTAMPS
    # ===================================
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # ===================================
    # RELATIONSHIPS
    # ===================================
    user = relationship("User", back_populates="password_resets")
    
    # ===================================
    # METHODS
    # ===================================
    def __repr__(self):
        return f"<PasswordReset(id={self.id}, user_id={self.user_id}, used={self.is_used})>"
    
    def to_dict(self):
        """Convert password reset to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "is_used": self.is_used,
            "is_expired": self.is_expired,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "used_at": self.used_at.isoformat() if self.used_at else None,
        }
    
    @property
    def is_used(self) -> bool:
        """Check if token has been used."""
        return self.used_at is not None
    
    @property
    def is_expired(self) -> bool:
        """Check if reset token has expired."""
        if self.expires_at is None:
            return True
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)."""
        return not self.is_used and not self.is_expired
    
    def mark_used(self):
        """Mark token as used."""
        if not self.is_used:
            self.used_at = datetime.utcnow()
    
    @classmethod
    def create_reset(cls, user_id: uuid.UUID, token: str, hours: int = 1):
        """
        Create a new password reset record.
        
        Args:
            user_id: User UUID
            token: Reset token
            hours: Expiration hours (default 1)
            
        Returns:
            PasswordReset instance
        """
        return cls(
            user_id=user_id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=hours)
        )