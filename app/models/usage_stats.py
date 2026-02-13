"""
Usage statistics model for tracking user activity.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, DateTime, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class UsageStats(Base):
    """
    Usage statistics model for tracking user activity.
    
    Useful for analytics, weekly summaries, and user engagement tracking.
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User (one-to-one relationship)
        
        # Counters
        videos_uploaded: Total videos uploaded
        videos_completed: Total videos successfully processed
        videos_failed: Total videos that failed processing
        total_extractions: Total extraction operations performed
        
        # Last activity
        last_upload_at: Last video upload timestamp
        last_extraction_at: Last extraction timestamp
        
        # Timestamps
        created_at: Stats creation timestamp
        updated_at: Stats update timestamp
    """
    
    __tablename__ = "usage_stats"
    
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
        unique=True,  # One-to-one relationship
        nullable=False,
        index=True
    )
    
    # ===================================
    # COUNTERS
    # ===================================
    videos_uploaded = Column(Integer, default=0, nullable=False)
    videos_completed = Column(Integer, default=0, nullable=False)
    videos_failed = Column(Integer, default=0, nullable=False)
    total_extractions = Column(Integer, default=0, nullable=False)
    
    # ===================================
    # LAST ACTIVITY
    # ===================================
    last_upload_at = Column(DateTime, nullable=True)
    last_extraction_at = Column(DateTime, nullable=True)
    
    # ===================================
    # TIMESTAMPS
    # ===================================
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # ===================================
    # RELATIONSHIPS
    # ===================================
    user = relationship("User", back_populates="usage_stats")
    
    # ===================================
    # METHODS
    # ===================================
    def __repr__(self):
        return f"<UsageStats(user_id={self.user_id}, videos={self.videos_uploaded})>"
    
    def to_dict(self):
        """Convert usage stats to dictionary."""
        return {
            "user_id": str(self.user_id),
            "videos_uploaded": self.videos_uploaded,
            "videos_completed": self.videos_completed,
            "videos_failed": self.videos_failed,
            "total_extractions": self.total_extractions,
            "last_upload_at": self.last_upload_at.isoformat() if self.last_upload_at else None,
            "last_extraction_at": self.last_extraction_at.isoformat() if self.last_extraction_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def increment_upload(self):
        """Increment video upload counter."""
        self.videos_uploaded += 1
        self.last_upload_at = datetime.utcnow()
    
    def increment_completed(self):
        """Increment completed video counter."""
        self.videos_completed += 1
    
    def increment_failed(self):
        """Increment failed video counter."""
        self.videos_failed += 1
    
    def increment_extraction(self):
        """Increment extraction counter."""
        self.total_extractions += 1
        self.last_extraction_at = datetime.utcnow()
    
    @property
    def success_rate(self) -> float:
        """
        Calculate video processing success rate.
        
        Returns:
            Success rate as percentage (0-100)
        """
        if self.videos_uploaded == 0:
            return 0.0
        return (self.videos_completed / self.videos_uploaded) * 100
    
    @property
    def avg_extractions_per_video(self) -> float:
        """
        Calculate average extractions per video.
        
        Returns:
            Average number of extractions
        """
        if self.videos_completed == 0:
            return 0.0
        return self.total_extractions / self.videos_completed
    
    @property
    def is_active_user(self) -> bool:
        """
        Check if user is active (uploaded in last 30 days).
        
        Returns:
            True if active, False otherwise
        """
        if not self.last_upload_at:
            return False
        
        from datetime import timedelta
        threshold = datetime.utcnow() - timedelta(days=30)
        return self.last_upload_at > threshold