"""
Video upload and processing Pydantic schemas.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from uuid import UUID


class VideoUploadURL(BaseModel):
    """
    Response containing Cloudinary signed upload URL.
    """
    video_id: Union[UUID, str]
    upload_url: str
    upload_params: Dict[str, Any]
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "video_id": "550e8400-e29b-41d4-a716-446655440000",
                "upload_url": "https://api.cloudinary.com/v1_1/your-cloud/upload",
                "upload_params": {
                    "timestamp": 1704067200,
                    "folder": "pipeline/550e8400-e29b-41d4-a716-446655440000",
                    "signature": "a1b2c3d4e5f6",
                    "api_key": "123456789"
                }
            }]
        }
    }


class VideoProgress(BaseModel):
    """
    Video processing progress details.
    """
    video_uploaded: bool = False
    audio_extracted: bool = False
    transcription_complete: bool = False
    columns_suggested: bool = False
    extraction_complete: bool = False


class VideoStatus(BaseModel):
    """
    Complete video status response.
    """
    video_id: Union[UUID, str]
    status: str  # pending, transcribing, awaiting_selection, extracting, completed, failed
    progress: Optional[VideoProgress] = None
    
    # Available after transcription
    suggested_columns: Optional[List[str]] = None
    
    # Available after extraction
    extracted_data: Optional[Dict[str, Any]] = None
    
    # Re-extraction info
    can_re_extract: bool = False
    extractions_remaining: int = 3
    extraction_count: int = 0
    
    # Error info
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # Timestamps
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "video_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "awaiting_selection",
                "progress": {
                    "video_uploaded": True,
                    "audio_extracted": True,
                    "transcription_complete": True,
                    "columns_suggested": True,
                    "extraction_complete": False
                },
                "suggested_columns": ["Title", "Location", "Price", "BHK"],
                "can_re_extract": True,
                "extractions_remaining": 3,
                "extraction_count": 0,
                "created_at": "2026-02-13T00:00:00Z"
            }]
        }
    }


class VideoResponse(BaseModel):
    """
    Video response with basic info.
    """
    id: Union[UUID, str]
    user_id: Union[UUID, str]
    video_url: str
    audio_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    transcript_url: Optional[str] = None
    
    status: str
    duration_seconds: Optional[int] = None
    file_size_mb: Optional[float] = None
    original_filename: Optional[str] = None
    
    # Latest extraction data
    latest_extraction: Optional[Dict[str, Any]] = None
    
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user-123",
                "video_url": "https://res.cloudinary.com/demo/video.mp4",
                "thumbnail_url": "https://res.cloudinary.com/demo/thumb.jpg",
                "status": "completed",
                "duration_seconds": 120,
                "created_at": "2026-02-13T00:00:00Z"
            }]
        }
    }


class VideoListItem(BaseModel):
    """
    Minimal video info for list views.
    """
    id: Union[UUID, str]
    video_url: str
    thumbnail_url: Optional[str] = None
    status: str
    created_at: datetime
    
    # Extracted title (if available)
    title: Optional[str] = None
    
    model_config = {
        "from_attributes": True
    }


class VideoListResponse(BaseModel):
    """
    Paginated list of videos.
    """
    videos: List[VideoListItem]
    total: int
    page: int = 1
    page_size: int = 20
    has_next: bool = False
    has_prev: bool = False


class VideoFilterParams(BaseModel):
    """
    Query parameters for filtering videos.
    """
    status: Optional[str] = Field(
        None,
        description="Filter by status: all, completed, processing, failed"
    )
    search: Optional[str] = Field(
        None,
        description="Search in titles and transcript"
    )
    sort_by: Optional[str] = Field(
        "created_at",
        description="Sort by: created_at, completed_at, duration"
    )
    sort_order: Optional[str] = Field(
        "desc",
        description="Sort order: asc, desc"
    )
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


class VideoDeleteResponse(BaseModel):
    """
    Response after deleting video.
    """
    success: bool = True
    message: str = "Video deleted successfully"
    video_id: Union[UUID, str]


class CloudinaryWebhook(BaseModel):
    """
    Cloudinary webhook payload.
    """
    notification_type: str
    secure_url: str
    public_id: str
    folder: Optional[str] = None
    format: Optional[str] = None
    resource_type: Optional[str] = None
    created_at: Optional[str] = None
    bytes: Optional[int] = None
    duration: Optional[float] = None
    
    # Additional fields may be present
    model_config = {
        "extra": "allow"
    }


class TranscriptResponse(BaseModel):
    """
    Transcript response.
    """
    video_id: Union[UUID, str]
    transcript: str
    duration_seconds: Optional[int] = None
    language: Optional[str] = None
    confidence: Optional[float] = None