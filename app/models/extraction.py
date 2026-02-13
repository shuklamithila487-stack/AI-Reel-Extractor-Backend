"""
Extraction model for storing extraction results.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, DateTime, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class Extraction(Base):
    """
    Extraction model for storing extraction results.
    Each video can have multiple extractions (up to 3).
    """
    
    __tablename__ = "extractions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Extraction data
    suggested_columns = Column(JSONB, nullable=True)  # AI-suggested columns
    selected_columns = Column(JSONB, nullable=True)   # User-selected columns
    extracted_data = Column(JSONB, nullable=True)      # Final extracted data
    
    # Metadata
    extraction_number = Column(Integer, default=1)  # 1st, 2nd, or 3rd extraction
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    video = relationship("Video", back_populates="extractions")
    user = relationship("User", back_populates="extractions")
    
    def __repr__(self) -> str:
        return f"<Extraction(id={self.id}, video_id={self.video_id}, number={self.extraction_number})>"
    
    def is_latest(self) -> bool:
        """Check if this is the latest extraction for the video."""
        if not self.video or not self.video.extractions:
            return True
        max_number = max(e.extraction_number for e in self.video.extractions)
        return self.extraction_number == max_number
    
    def get_column_count(self) -> int:
        """Get number of selected columns."""
        if self.selected_columns:
            return len(self.selected_columns)
        return 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "video_id": str(self.video_id),
            "suggested_columns": self.suggested_columns,
            "selected_columns": self.selected_columns,
            "extracted_data": self.extracted_data,
            "extraction_number": self.extraction_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }