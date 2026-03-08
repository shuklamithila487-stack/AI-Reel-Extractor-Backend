"""
Video service.
Handles video upload URL generation, status tracking, and video management.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.models import Video, User, Extraction
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas import VideoStatus, VideoResponse, VideoFilterParams

logger = get_logger(__name__)


class VideoError(Exception):
    """Custom exception for video errors."""
    pass


# ===================================
# VIDEO UPLOAD
# ===================================

def generate_upload_url(user_id: str, db: Session) -> Dict[str, Any]:
    """
    Generate Cloudinary signed upload URL for video.
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        Dictionary with video_id, upload_url, and upload_params
        
    Raises:
        VideoError: If URL generation fails
    """
    try:
        from app.services.cloudinary_service import generate_signed_upload_url
        import uuid
        
        # Generate unique video ID
        video_id = str(uuid.uuid4())
        
        # Create video record with pending status
        video = Video(
            id=video_id,
            user_id=user_id,
            video_url="",  # Will be updated by webhook
            status="pending"
        )
        
        db.add(video)
        db.commit()
        db.refresh(video)
        
        # Generate Cloudinary signed upload URL
        folder = f"pipeline/{video_id}"
        notification_url = settings.get_cloudinary_webhook_url()
        upload_data = generate_signed_upload_url(folder, video_id, notification_url=notification_url)
        
        logger.info(
            "Upload URL generated",
            video_id=video_id,
            user_id=user_id
        )
        
        return {
            "video_id": video_id,
            "upload_url": upload_data["upload_url"],
            "upload_params": upload_data["upload_params"]  # notification_url is now inside upload_params
        }
        
    except Exception as e:
        db.rollback()
        logger.error("Failed to generate upload URL", error=str(e))
        raise VideoError(f"Failed to generate upload URL: {str(e)}")


def upload_video_from_file(file: Any, user_id: str, db: Session, filename: str = None) -> Video:
    """
    Upload video file directly to Cloudinary and create record.
    
    Args:
        file: File object (bytes or UploadFile)
        user_id: User ID
        db: Database session
        filename: Original filename
        
    Returns:
        Created Video object
    """
    try:
        from app.services import cloudinary_service
        import uuid
        
        # Generate ID
        video_id = str(uuid.uuid4())
        
        # Upload to Cloudinary
        folder = f"pipeline/{video_id}"
        
        # If file is UploadFile (FastAPI), use file.file, else assume bytes/file-like
        # Check if file has 'file' attribute (UploadFile)
        file_obj = file.file if hasattr(file, 'file') else file
        
        result = cloudinary_service.upload_video(
            file_obj,
            folder=folder,
            public_id=video_id
        )
        
        # Create Video record
        # Note: id is UUID type in DB, but SQLAlchemy usually handles passing UUID object or string if defined
        video = Video(
            id=video_id,
            user_id=user_id,
            video_url=result.get("secure_url"),
            status="pending", # Initial status for pipeline
            original_filename=filename or "uploaded_video.mp4",
            duration_seconds=int(result.get("duration", 0) or 0),
            file_size_mb=float(result.get("bytes", 0)) / (1024 * 1024)
        )
        
        db.add(video)
        db.commit()
        db.refresh(video)
        
        logger.info(
            "Video uploaded directly",
            video_id=video_id,
            user_id=user_id
        )
        
        return video
        
    except Exception as e:
        db.rollback()
        logger.error("Failed to upload video directly", error=str(e))
        raise VideoError(f"Failed to upload video: {str(e)}")



# ===================================
# VIDEO STATUS
# ===================================

def get_video_status(video_id: str, user_id: Optional[str], db: Session) -> Dict[str, Any]:
    """
    Get video processing status.
    
    Args:
        video_id: Video ID
        user_id: User ID (optional, if None allows access to any video)
        db: Database session
    """
    try:
        # Get video
        query = db.query(Video).filter(Video.id == video_id)
        if user_id:
            query = query.filter(Video.user_id == user_id)
        
        video = query.first()
        
        if not video:
            raise VideoError("Video not found or unauthorized")
        
        # Get extractions
        all_extractions = db.query(Extraction).filter(
            Extraction.video_id == video_id
        ).all()
        
        # Actual user extractions
        user_extractions = [e for e in all_extractions if e.extraction_number > 0]
        user_extractions.sort(key=lambda x: x.created_at, reverse=True)
        
        # Suggestion record (number 0)
        latest_extraction = next((e for e in all_extractions if e.extraction_number == 0), None)
        # If no suggestion record, use latest user extraction for suggestions if available
        if not latest_extraction and user_extractions:
            latest_extraction = user_extractions[0]
            
        extraction_count = len(user_extractions)
        extractions_remaining = max(0, settings.MAX_EXTRACTIONS_PER_VIDEO - extraction_count)
        
        # Build progress object
        progress = {
            "video_uploaded": video.video_url is not None and video.video_url != "",
            "audio_extracted": video.audio_url is not None,
            "transcription_complete": video.transcript is not None and len(video.transcript) > 0,
            "columns_suggested": latest_extraction is not None and latest_extraction.suggested_columns is not None,
            "extraction_complete": video.status == "completed"
        }
        
        # Get suggested columns
        suggested_columns = None
        if latest_extraction and latest_extraction.suggested_columns:
            suggested_columns = latest_extraction.suggested_columns
        
        # Get extracted data (MERGED from all extractions, starting from baseline)
        all_extracted_data = {}
        # Iterate from oldest to newest across ALL extractions (including extraction_number 0) 
        # so later extractions additive-ly overwrite or add to the earlier baseline.
        for ext in sorted(all_extractions, key=lambda x: x.created_at):
            if ext.extracted_data:
                all_extracted_data.update(ext.extracted_data)
        
        return {
            "video_id": str(video.id),
            "video_url": video.video_url,
            "thumbnail_url": video.thumbnail_url,
            "status": video.status,
            "progress": progress,
            "suggested_columns": suggested_columns,
            "extracted_data": all_extracted_data,
            "transcript": video.transcript,
            "title": video.title,
            "description": video.description,
            "can_re_extract": video.can_re_extract(settings.MAX_EXTRACTIONS_PER_VIDEO),
            "extractions_remaining": extractions_remaining,
            "extraction_count": extraction_count,
            "suggestions_remaining": max(0, 3 - video.suggestion_count),
            "suggestions_count": video.suggestion_count,
            "error_message": video.error_message,
            "retry_count": video.retry_count,
            "created_at": video.created_at,
            "completed_at": video.completed_at
        }
        
    except VideoError:
        raise
    except Exception as e:
        logger.error("Failed to get video status", error=str(e), video_id=video_id)
        raise VideoError(f"Failed to get video status: {str(e)}")


# ===================================
# VIDEO LISTING
# ===================================

def list_user_videos(
    user_id: Optional[str],
    filters: VideoFilterParams,
    db: Session
) -> Tuple[List[Video], int]:
    """
    List videos with filters and pagination.
    If user_id is provided, filter by user. If None, return all videos (admin/public view).
    
    Args:
        user_id: User ID (optional)
        filters: Filter parameters
        db: Database session
        
    Returns:
        Tuple of (videos, total_count)
    """
    try:
        # Base query
        query = db.query(Video)
        
        # Filter by user if provided
        if user_id:
            query = query.filter(Video.user_id == user_id)
        
        # Apply status filter
        if filters.status and filters.status != "all":
            if filters.status == "completed":
                query = query.filter(Video.status == "completed")
            elif filters.status == "processing":
                query = query.filter(Video.status.in_(["transcribing", "extracting"]))
            elif filters.status == "failed":
                query = query.filter(Video.status == "failed")
        
        # Apply search filter
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                or_(
                    Video.transcript.ilike(search_term),
                    Video.original_filename.ilike(search_term)
                )
            )
        
        # Get total count before pagination
        total = query.count()
        
        # Apply sorting
        if filters.sort_by == "created_at":
            order_col = Video.created_at
        elif filters.sort_by == "completed_at":
            order_col = Video.completed_at
        elif filters.sort_by == "duration":
            order_col = Video.duration_seconds
        else:
            order_col = Video.created_at
        
        if filters.sort_order == "asc":
            query = query.order_by(order_col.asc())
        else:
            query = query.order_by(order_col.desc())
        
        # Apply pagination
        offset = (filters.page - 1) * filters.page_size
        videos = query.limit(filters.page_size).offset(offset).all()
        
        logger.info(
            "Videos listed",
            user_id=user_id,
            count=len(videos),
            total=total
        )
        
        return videos, total
        
    except Exception as e:
        logger.error("Failed to list videos", error=str(e))
        raise VideoError(f"Failed to list videos: {str(e)}")


# ===================================
# VIDEO DETAILS
# ===================================

def get_video_details(video_id: str, user_id: Optional[str], db: Session) -> Video:
    """
    Get detailed video information.
    
    Args:
        video_id: Video ID
        user_id: User ID (optional)
        db: Database session
    """
    try:
        query = db.query(Video).filter(Video.id == video_id)
        if user_id:
            query = query.filter(Video.user_id == user_id)
            
        video = query.first()
        
        if not video:
            raise VideoError("Video not found or unauthorized")
        
        return video
        
    except VideoError:
        raise
    except Exception as e:
        logger.error("Failed to get video details", error=str(e))
        raise VideoError(f"Failed to get video details: {str(e)}")


# ===================================
# VIDEO DELETION
# ===================================

def delete_video(video_id: str, user_id: str, db: Session) -> bool:
    """
    Delete a video and all associated data.
    
    Args:
        video_id: Video ID
        user_id: User ID (for authorization)
        db: Database session
        
    Returns:
        True if deleted successfully
        
    Raises:
        VideoError: If deletion fails
    """
    try:
        # Get video
        video = db.query(Video).filter(
            Video.id == video_id,
            Video.user_id == user_id
        ).first()
        
        if not video:
            raise VideoError("Video not found or unauthorized")
        
        # Delete from Cloudinary (optional - can be done in background)
        # This will also delete associated extractions due to cascade
        
        db.delete(video)
        db.commit()
        
        logger.info("Video deleted", video_id=video_id, user_id=user_id)
        
        return True
        
    except VideoError:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to delete video", error=str(e))
        raise VideoError(f"Failed to delete video: {str(e)}")


# ===================================
# VIDEO UPDATE
# ===================================

def update_video_status(
    video_id: str,
    status: str,
    db: Session,
    **kwargs
) -> Video:
    """
    Update video status and related fields.
    
    Args:
        video_id: Video ID
        status: New status
        db: Database session
        **kwargs: Additional fields to update
        
    Returns:
        Updated video
        
    Raises:
        VideoError: If update fails
    """
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        
        if not video:
            raise VideoError("Video not found")
        
        # Update status
        video.status = status
        
        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(video, key):
                setattr(video, key, value)
        
        # Mark as completed if status is completed
        if status == "completed" and not video.completed_at:
            video.mark_completed()
        
        db.commit()
        db.refresh(video)
        
        logger.info(
            "Video status updated",
            video_id=video_id,
            status=status
        )
        
        return video
        
    except VideoError:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to update video status", error=str(e))
        raise VideoError(f"Failed to update video status: {str(e)}")


def mark_video_failed(
    video_id: str,
    error_message: str,
    db: Session
) -> Video:
    """
    Mark video as failed with error message.
    
    Args:
        video_id: Video ID
        error_message: Error message
        db: Database session
        
    Returns:
        Updated video
    """
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        
        if not video:
            raise VideoError("Video not found")
        
        video.mark_failed(error_message)
        
        db.commit()
        db.refresh(video)
        
        logger.error(
            "Video marked as failed",
            video_id=video_id,
            error=error_message
        )
        
        return video
        
    except Exception as e:
        db.rollback()
        logger.error("Failed to mark video as failed", error=str(e))
        raise VideoError(f"Failed to mark video as failed: {str(e)}")


# ===================================
# STATISTICS
# ===================================

def get_user_video_stats(user_id: str, db: Session) -> Dict[str, Any]:
    """
    Get user's video statistics.
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        Statistics dictionary
    """
    try:
        total = db.query(Video).filter(Video.user_id == user_id).count()
        completed = db.query(Video).filter(
            Video.user_id == user_id,
            Video.status == "completed"
        ).count()
        processing = db.query(Video).filter(
            Video.user_id == user_id,
            Video.status.in_(["transcribing", "extracting"])
        ).count()
        failed = db.query(Video).filter(
            Video.user_id == user_id,
            Video.status == "failed"
        ).count()
        
        return {
            "total": total,
            "completed": completed,
            "processing": processing,
            "failed": failed
        }
        
    except Exception as e:
        logger.error("Failed to get video stats", error=str(e))
        return {
            "total": 0,
            "completed": 0,
            "processing": 0,
            "failed": 0
        }