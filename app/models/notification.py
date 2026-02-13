"""
Notification model for user notifications and email tracking.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class Notification(Base):
    """
    Notification model for in-app and email notifications.
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        
        # Notification details
        type: Notification type (processing_complete, processing_failed, etc.)
        title: Notification title
        message: Notification message
        
        # Associated data
        video_id: Related video (optional)
        data: Additional data (JSON)
        
        # Email tracking
        email_sent: Whether email was sent
        email_sent_at: Email send timestamp
        email_opened: Whether email was opened
        email_opened_at: Email open timestamp
        
        # Status
        read: Whether notification was read
        read_at: Read timestamp
        
        # Timestamps
        created_at: Notification creation timestamp
    """
    
    __tablename__ = "notifications"
    
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
    
    video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # ===================================
    # NOTIFICATION DETAILS
    # ===================================
    type = Column(
        String(50),
        nullable=False,
        index=True
    )
    # Types: processing_complete, processing_failed, weekly_summary, product_update
    
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    
    # ===================================
    # ASSOCIATED DATA
    # ===================================
    data = Column(JSONB, nullable=True)
    # Store additional context (extracted data preview, error details, etc.)
    
    # ===================================
    # EMAIL TRACKING
    # ===================================
    email_sent = Column(Boolean, default=False, nullable=False)
    email_sent_at = Column(DateTime, nullable=True)
    email_opened = Column(Boolean, default=False, nullable=False)
    email_opened_at = Column(DateTime, nullable=True)
    
    # ===================================
    # STATUS
    # ===================================
    read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)
    
    # ===================================
    # TIMESTAMPS
    # ===================================
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # ===================================
    # RELATIONSHIPS
    # ===================================
    user = relationship("User", back_populates="notifications")
    
    # ===================================
    # METHODS
    # ===================================
    def __repr__(self):
        return f"<Notification(id={self.id}, type={self.type}, user_id={self.user_id})>"
    
    def to_dict(self):
        """Convert notification to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "video_id": str(self.video_id) if self.video_id else None,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "read": self.read,
            "email_sent": self.email_sent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }
    
    def mark_as_read(self):
        """Mark notification as read."""
        if not self.read:
            self.read = True
            self.read_at = datetime.utcnow()
    
    def mark_email_sent(self):
        """Mark email as sent."""
        if not self.email_sent:
            self.email_sent = True
            self.email_sent_at = datetime.utcnow()
    
    def mark_email_opened(self):
        """Mark email as opened."""
        if not self.email_opened:
            self.email_opened = True
            self.email_opened_at = datetime.utcnow()
    
    @property
    def is_unread(self) -> bool:
        """Check if notification is unread."""
        return not self.read
    
    @property
    def age_minutes(self) -> int:
        """Get notification age in minutes."""
        if not self.created_at:
            return 0
        delta = datetime.utcnow() - self.created_at
        return int(delta.total_seconds() / 60)