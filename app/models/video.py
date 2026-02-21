"""
Video model for uploaded videos and processing status.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, ForeignKey, Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class Video(Base):
    """
    Video model for uploaded videos.
    """
    
    __tablename__ = "videos"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Cloudinary URLs
    video_url = Column(Text, nullable=False)
    audio_url = Column(Text, nullable=True)
    transcript_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    
    # Processing data
    transcript = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    file_size_mb = Column(Numeric(10, 2), nullable=True)
    
    # Metadata
    original_filename = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Status
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        index=True
    )  # pending, uploading, transcribing, awaiting_selection, extracting, completed, failed
    
    # Error handling
    retry_count = Column(Integer, default=0)
    suggestion_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="videos")
    extractions = relationship("Extraction", back_populates="video", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Video(id={self.id}, status={self.status})>"
    
    def is_completed(self) -> bool:
        """Check if video processing is completed."""
        return self.status == "completed"
    
    def is_failed(self) -> bool:
        """Check if video processing failed."""
        return self.status == "failed"
    
    def is_processing(self) -> bool:
        """Check if video is currently being processed."""
        return self.status in ["transcribing", "extracting"]
    
    def can_extract(self) -> bool:
        """Check if video can be extracted (has transcript)."""
        return self.transcript is not None and len(self.transcript) > 0
    
    def get_extraction_count(self) -> int:
        """Get number of extractions for this video (excluding suggestions)."""
        if not self.extractions:
            return 0
        return len([e for e in self.extractions if e.extraction_number > 0])
    
    def can_re_extract(self, max_extractions: int = 3) -> bool:
        """Check if video can be re-extracted."""
        return self.can_extract() and self.get_extraction_count() < max_extractions
    
    def mark_completed(self):
        """Mark video as completed."""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
    
    def mark_failed(self, error_message: str):
        """Mark video as failed."""
        self.status = "failed"
        self.error_message = error_message
        self.last_error_at = datetime.utcnow()
        self.retry_count += 1
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "video_url": self.video_url,
            "thumbnail_url": self.thumbnail_url,
            "status": self.status,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }