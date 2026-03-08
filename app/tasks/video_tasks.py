"""
Video processing background tasks.
Handles video transcription, column suggestion, and data extraction.
"""

import asyncio
from typing import List
from sqlalchemy.orm import Session

from app.tasks.huey_config import task
from app.db.database import SessionLocal
from app.models import Video, Extraction, User
from app.services import (
    cloudinary_service,
    sarvam_service,
    openai_service,
    extraction_service,
    video_service,
    email_service,
    airtable_service,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


# ===================================
# VIDEO PROCESSING PIPELINE
# ===================================

@task(retries=3, retry_delay=60)
def process_video_pipeline(video_id: str, **kwargs):
    """
    Complete video processing pipeline:
    1. Extract audio from video
    2. Transcribe audio
    3. Suggest columns
    4. Update status to awaiting_selection
    5. Send email notification
    
    Args:
        video_id: Video ID
    """
    db = SessionLocal()
    
    try:
        logger.info("Starting video processing pipeline", video_id=video_id)
        
        # Get video
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error("Video not found", video_id=video_id)
            return
        
        # Update status to transcribing
        video_service.update_video_status(
            video_id=video_id,
            status="transcribing",
            db=db
        )
        
        # Step 1: Extract audio from video
        logger.info("Extracting audio from video", video_id=video_id)
        try:
            audio_url = cloudinary_service.extract_audio_from_video(video.video_url)
            
            # Update video with audio URL
            video_service.update_video_status(
                video_id=video_id,
                status="transcribing",
                db=db,
                audio_url=audio_url
            )
            
            logger.info("Audio extracted successfully", video_id=video_id)
            
        except Exception as e:
            logger.error("Audio extraction failed", video_id=video_id, error=str(e))
            video_service.mark_video_failed(
                video_id=video_id,
                error_message=f"Audio extraction failed: {str(e)}",
                db=db
            )
            
            # Send failure email
            _send_failure_notification(video, str(e), db)
            return
        
        # Step 2: Transcribe audio
        logger.info("Transcribing audio", video_id=video_id)
        try:
            transcript = sarvam_service.transcribe_audio(audio_url)
            
            if not transcript or len(transcript.strip()) == 0:
                raise Exception("Transcript is empty")
            
            # Update video with transcript
            video_service.update_video_status(
                video_id=video_id,
                status="transcribing",
                db=db,
                transcript=transcript
            )
            
            logger.info(
                "Transcription completed",
                video_id=video_id,
                transcript_length=len(transcript)
            )
            
        except Exception as e:
            logger.error("Transcription failed", video_id=video_id, error=str(e))
            video_service.mark_video_failed(
                video_id=video_id,
                error_message=f"Transcription failed: {str(e)}",
                db=db
            )
            
            # Send failure email
            _send_failure_notification(video, str(e), db)
            return
        
        # Step 3: Suggest columns using OpenAI and Generate Metadata
        logger.info("Suggesting columns and generating metadata", video_id=video_id)
        try:
            # Run async function in sync context
            suggested_columns = [
                "Property Type", 
                "Location", 
                "Price/Rent", 
                "Size/Area", 
                "Property Status (Rent/Sale)", 
                "Furnishing", 
                "Amenities", 
                "Property Condition"
            ]
            
            metadata = asyncio.run(
                openai_service.generate_video_metadata(transcript)
            )
            
            video_service.update_video_status(
                video_id=video_id,
                status="transcribing",  # Still transcribing logically until thumbnail
                db=db,
                title=metadata.get("title"),
                description=metadata.get("description")
            )
            
            # Create initial extraction record with suggestions
            extraction = Extraction(
                video_id=video_id,
                user_id=video.user_id,
                suggested_columns=suggested_columns,
                extraction_number=0  # Suggestion only, not a full extraction
            )
            
            db.add(extraction)
            db.commit()

            # NEW: Immediately trigger the first extraction with default core columns 
            # so the user sees data right away after upload processing.
            try:
                # We need to run this async in a sync context
                from app.services.extraction_service import extract_data
                asyncio.run(extract_data(
                    video_id=video_id,
                    selected_columns=suggested_columns,
                    user_id=str(video.user_id),
                    db=db,
                    extraction_number=0
                ))
                logger.info("Automatic initial extraction completed", video_id=video_id)
            except Exception as auto_ext_err:
                logger.error("Automatic initial extraction failed", error=str(auto_ext_err), video_id=video_id)
            
            logger.info(
                "Columns suggested and auto-extracted",
                video_id=video_id,
                column_count=len(suggested_columns)
            )
            
        except Exception as e:
            logger.error("Column suggestion failed", video_id=video_id, error=str(e))
            # Don't fail the entire pipeline, just use default columns
            suggested_columns = [
                "Title", "Description", "Property Type", "BHK",
                "Location", "Price", "Amenities", "Key Features"
            ]
            
            extraction = Extraction(
                video_id=video_id,
                user_id=video.user_id,
                suggested_columns=suggested_columns,
                extraction_number=0
            )
            
            db.add(extraction)
            db.commit()
        
        # Step 4: Generate thumbnail
        try:
            thumbnail_url = cloudinary_service.generate_thumbnail(video.video_url)
            video_service.update_video_status(
                video_id=video_id,
                status="awaiting_selection",
                db=db,
                thumbnail_url=thumbnail_url
            )
        except Exception as e:
            logger.warning("Thumbnail generation failed", error=str(e))
            # Not critical, continue
            video_service.update_video_status(
                video_id=video_id,
                status="awaiting_selection",
                db=db
            )
        
        logger.info("Video processing pipeline completed", video_id=video_id)
        
    except Exception as e:
        logger.error(
            "Video processing pipeline failed",
            video_id=video_id,
            error=str(e)
        )
        
        try:
            video_service.mark_video_failed(
                video_id=video_id,
                error_message=str(e),
                db=db
            )
        except:
            pass
    
    finally:
        db.close()


# ===================================
# DATA EXTRACTION TASK
# ===================================

@task(retries=3, retry_delay=60)
def extract_data_task(video_id: str, selected_columns: List[str], user_id: str, **kwargs):
    """
    Extract data from video transcript with selected columns.
    
    Args:
        video_id: Video ID
        selected_columns: User-selected columns
        user_id: User ID
    """
    db = SessionLocal()
    
    try:
        logger.info(
            "Starting data extraction",
            video_id=video_id,
            column_count=len(selected_columns)
        )
        
        # Update status to extracting
        video_service.update_video_status(
            video_id=video_id,
            status="extracting",
            db=db
        )
        
        # Extract data
        extraction = asyncio.run(
            extraction_service.extract_data(
                video_id=video_id,
                selected_columns=selected_columns,
                user_id=user_id,
                db=db
            )
        )
        
        # Update video status to completed
        video_service.update_video_status(
            video_id=video_id,
            status="completed",
            db=db
        )
        
        logger.info(
            "Data extraction completed",
            video_id=video_id,
            extraction_id=str(extraction.id)
        )
        
        # Send success email
        _send_success_notification(video_id, extraction.id, db)
        
        # Trigger Airtable Sync
        sync_airtable_task(video_id)
        
    except Exception as e:
        logger.error(
            "Data extraction failed",
            video_id=video_id,
            error=str(e)
        )
        
        # Don't mark as globally FAILED for manual extraction issues
        # Revert to completed so the video remains accessible/healthy on dashboard
        video_service.update_video_status(
            video_id=video_id,
            status="completed",
            db=db,
            error_message=f"Extraction Error: {str(e)}"
        )
        
        # Send failure email
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            _send_failure_notification(video, str(e), db)
    
    finally:
        db.close()


# ===================================
# CLOUDINARY WEBHOOK HANDLER
# ===================================

@task()
def handle_cloudinary_upload(video_id: str, video_url: str, metadata: dict, **kwargs):
    """
    Handle Cloudinary upload completion webhook.
    Updates video record and triggers processing.
    
    Args:
        video_id: Video ID
        video_url: Cloudinary video URL
        metadata: Additional metadata from Cloudinary
    """
    db = SessionLocal()
    
    try:
        logger.info(
            "Handling Cloudinary upload",
            video_id=video_id,
            video_url=video_url
        )
        
        # Update video record
        video_service.update_video_status(
            video_id=video_id,
            status="transcribing",
            db=db,
            video_url=video_url,
            duration_seconds=metadata.get('duration'),
            file_size_mb=metadata.get('bytes', 0) / (1024 * 1024),
            original_filename=metadata.get('original_filename')
        )
        
        # Trigger processing pipeline
        process_video_pipeline(video_id)
        
        logger.info("Cloudinary upload handled", video_id=video_id)
        
    except Exception as e:
        logger.error(
            "Failed to handle Cloudinary upload",
            video_id=video_id,
            error=str(e)
        )
    
    finally:
        db.close()


# ===================================
# RETRY FAILED VIDEO
# ===================================

@task(retries=3, retry_delay=120)
def retry_failed_video(video_id: str, **kwargs):
    """
    Retry processing a failed video.
    
    Args:
        video_id: Video ID
    """
    db = SessionLocal()
    
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        
        if not video:
            logger.error("Video not found for retry", video_id=video_id)
            return
        
        if video.retry_count >= 3:
            logger.warning(
                "Maximum retry attempts reached",
                video_id=video_id
            )
            return
        
        logger.info("Retrying failed video", video_id=video_id)
        
        # Reset status
        video_service.update_video_status(
            video_id=video_id,
            status="pending",
            db=db
        )
        
        # Trigger processing
        process_video_pipeline(video_id)
        
    except Exception as e:
        logger.error("Failed to retry video", video_id=video_id, error=str(e))
    
    finally:
        db.close()


# ===================================
# HELPER FUNCTIONS
# ===================================

def _send_success_notification(video_id: str, extraction_id: str, db: Session):
    """Send processing complete email notification."""
    try:
        from app.tasks.email_tasks import send_processing_complete_email_task
        
        # Queue email task
        send_processing_complete_email_task(video_id, extraction_id)
        
        logger.info("Success notification queued", video_id=video_id)
        
    except Exception as e:
        logger.error("Failed to queue success notification", error=str(e))


def _send_failure_notification(video: Video, error_message: str, db: Session):
    """Send processing failed email notification."""
    try:
        from app.tasks.email_tasks import send_processing_failed_email_task
        
        # Queue email task
        send_processing_failed_email_task(str(video.id), error_message)
        
        logger.info("Failure notification queued", video_id=str(video.id))
        
    except Exception as e:
        logger.error("Failed to queue failure notification", error=str(e))
@task()
def sync_airtable_task(video_id: str, **kwargs):
    """
    Background task to sync current aggregated video data to Airtable.
    """
    db = SessionLocal()
    try:
        from app.services import video_service, airtable_service
        
        # Get full aggregated status (includes merged extracted_data)
        status = video_service.get_video_status(video_id, db)
        if not status or not status.get("extracted_data"):
            logger.warning("Airtable sync: No data to sync", video_id=video_id)
            return

        # Prepare payload: clean "Not mentioned" etc for cleaner Airtable records
        clean_data = {}
        for k, v in status["extracted_data"].items():
            if v and str(v).strip().lower() not in ["not mentioned", "n/a", "not found", "unknown"]:
                clean_data[k] = v
        
        if not clean_data:
            logger.info("Airtable sync: No meaningful data to sync", video_id=video_id)
            return

        logger.info("Syncing to Airtable...", video_id=video_id)
        # We need to run the async sync function in a sync context
        import asyncio
        asyncio.run(airtable_service.sync_to_airtable(clean_data, video_id))
        
    except Exception as e:
        logger.error("Airtable sync task failed", error=str(e), video_id=video_id)
    finally:
        db.close()
