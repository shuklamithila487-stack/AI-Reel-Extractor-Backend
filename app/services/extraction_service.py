"""
Extraction service.
Handles AI-powered column suggestion and data extraction.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models import Video, Extraction
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExtractionError(Exception):
    """Custom exception for extraction errors."""
    pass


# ===================================
# COLUMN SUGGESTION
# ===================================

async def suggest_columns(transcript: str) -> List[str]:
    """
    Suggest relevant columns based on transcript using Claude API.
    
    Args:
        transcript: Video transcript
        
    Returns:
        List of suggested column names
        
    Raises:
        ExtractionError: If suggestion fails
    """
    try:
        from app.services.openai_service import suggest_columns_from_transcript
        
        if not transcript or len(transcript.strip()) == 0:
            raise ExtractionError("Transcript is empty")
        
        # Call OpenAI API
        suggested_columns = await suggest_columns_from_transcript(transcript)
        
        logger.info(
            "Columns suggested",
            column_count=len(suggested_columns)
        )
        
        return suggested_columns
        
    except Exception as e:
        logger.error("Failed to suggest columns", error=str(e))
        raise ExtractionError(f"Failed to suggest columns: {str(e)}")


# ===================================
# DATA EXTRACTION
# ===================================

async def extract_data(
    video_id: str,
    selected_columns: List[str],
    user_id: str,
    db: Session,
    extraction_number: Optional[int] = None
) -> Extraction:
    """
    Extract data from video transcript using selected columns.
    
    Args:
        video_id: Video ID
        selected_columns: User-selected columns to extract
        user_id: User ID
        db: Database session
        
    Returns:
        Extraction object with extracted data
        
    Raises:
        ExtractionError: If extraction fails
    """
    try:
        from app.services.openai_service import extract_fields_from_transcript
        
        # Get video
        # Allow any video for global access
        video = db.query(Video).filter(Video.id == video_id).first()
        
        if not video:
            raise ExtractionError("Video not found")
        
        # Check if video has transcript
        if not video.can_extract():
            raise ExtractionError("Video transcript not available")
        
        # Check extraction limit (exclude suggestion-only record 0)
        extraction_count = db.query(Extraction).filter(
            Extraction.video_id == video_id,
            Extraction.extraction_number > 0
        ).count()
        
        if extraction_count >= settings.MAX_EXTRACTIONS_PER_VIDEO:
            raise ExtractionError(
                f"Maximum {settings.MAX_EXTRACTIONS_PER_VIDEO} extractions reached for this video"
            )
        
        # Validate selected columns
        if not selected_columns or len(selected_columns) == 0:
            raise ExtractionError("No columns selected")
        
        if len(selected_columns) > 15:
            raise ExtractionError("Maximum 15 columns allowed")
        
        # Call OpenAI API to extract data
        extracted_data = await extract_fields_from_transcript(
            transcript=video.transcript,
            columns=selected_columns
        )
        
        # Combine data with ALL previous extractions to ensure nothing is lost
        all_previous_extractions = db.query(Extraction).filter(
            Extraction.video_id == video_id,
            Extraction.extraction_number > 0
        ).all()
        
        merged_data = {}
        for prev in all_previous_extractions:
            if prev.extracted_data:
                merged_data.update(prev.extracted_data)
        
        # Add the new ones (latest takes precedence)
        merged_data.update(extracted_data)
        
        if extraction_number is not None:
            # Update existing or create with specific number (usually for initial pass 0)
            extraction = db.query(Extraction).filter(
                Extraction.video_id == video_id,
                Extraction.extraction_number == extraction_number
            ).first()
            
            if extraction:
                extraction.selected_columns = selected_columns
                extraction.extracted_data = extracted_data
                db.commit()
                db.refresh(extraction)
                return extraction
            
            num_to_set = extraction_number
        else:
            num_to_set = extraction_count + 1

        # Create extraction record
        extraction = Extraction(
            video_id=video_id,
            user_id=user_id,
            selected_columns=selected_columns,
            extracted_data=extracted_data, # Store only what was requested this time in the record
            extraction_number=num_to_set
        )
        
        db.add(extraction)
        db.commit()
        db.refresh(extraction)
        
        logger.info(
            "Data extracted successfully",
            video_id=video_id,
            extraction_id=str(extraction.id),
            extraction_number=extraction.extraction_number
        )
        
        return extraction
        
    except ExtractionError:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Extraction failed", error=str(e), video_id=video_id)
        raise ExtractionError(f"Extraction failed: {str(e)}")


# ===================================
# EXTRACTION HISTORY
# ===================================

def get_extraction_history(
    video_id: str,
    user_id: Optional[str],
    db: Session
) -> List[Extraction]:
    """
    Get extraction history for a video.
    
    Args:
        video_id: Video ID
        user_id: User ID (optional)
        db: Database session
        
    Returns:
        List of extractions ordered by creation date
        
    Raises:
        ExtractionError: If video not found
    """
    try:
        # Verify video ownership
        video = db.query(Video).filter(Video.id == video_id).first()
        
        if not video:
            raise ExtractionError("Video not found")
        
        # Get extractions
        # For MVP Global View: Show all extractions
        extractions = db.query(Extraction).filter(
            Extraction.video_id == video_id
        ).order_by(Extraction.created_at.desc()).all()
        
        return extractions
        
    except ExtractionError:
        raise
    except Exception as e:
        logger.error("Failed to get extraction history", error=str(e))
        raise ExtractionError(f"Failed to get extraction history: {str(e)}")


def get_latest_extraction(
    video_id: str,
    user_id: Optional[str],
    db: Session
) -> Optional[Extraction]:
    """
    Get the latest extraction for a video.
    
    Args:
        video_id: Video ID
        user_id: User ID (optional)
        db: Database session
        
    Returns:
        Latest extraction or None
    """
    try:
        extraction = db.query(Extraction).filter(
            Extraction.video_id == video_id
        ).order_by(Extraction.created_at.desc()).first()
        
        return extraction
        
    except Exception as e:
        logger.error("Failed to get latest extraction", error=str(e))
        return None


# ===================================
# VALIDATION
# ===================================

def validate_extraction_limit(
    video_id: str,
    db: Session
) -> bool:
    """
    Check if video can be re-extracted.
    
    Args:
        video_id: Video ID
        db: Database session
        
    Returns:
        True if extraction is allowed, False otherwise
    """
    try:
        count = db.query(Extraction).filter(
            Extraction.video_id == video_id,
            Extraction.extraction_number > 0
        ).count()
        
        return count < settings.MAX_EXTRACTIONS_PER_VIDEO
        
    except Exception as e:
        logger.error("Failed to validate extraction limit", error=str(e))
        return False


def get_extractions_remaining(video_id: str, db: Session) -> int:
    """
    Get number of remaining extractions for a video.
    
    Args:
        video_id: Video ID
        db: Database session
        
    Returns:
        Number of remaining extractions (0-3)
    """
    try:
        count = db.query(Extraction).filter(
            Extraction.video_id == video_id,
            Extraction.extraction_number > 0
        ).count()
        
        remaining = max(0, settings.MAX_EXTRACTIONS_PER_VIDEO - count)
        return remaining
        
    except Exception as e:
        logger.error("Failed to get extractions remaining", error=str(e))
        return 0


# ===================================
# EXTRACTION QUALITY
# ===================================

def validate_extracted_data(extracted_data: Dict[str, Any]) -> bool:
    """
    Validate quality of extracted data.
    
    Args:
        extracted_data: Extracted data dictionary
        
    Returns:
        True if data is valid, False otherwise
    """
    try:
        if not extracted_data:
            return False
        
        # Check if at least some fields have values
        non_empty_fields = sum(
            1 for value in extracted_data.values()
            if value and str(value).strip() not in ["", "Not found", "N/A", "Unknown"]
        )
        
        # At least 30% of fields should have meaningful values
        total_fields = len(extracted_data)
        if total_fields == 0:
            return False
        
        success_rate = non_empty_fields / total_fields
        
        logger.info(
            "Extraction quality validated",
            total_fields=total_fields,
            non_empty_fields=non_empty_fields,
            success_rate=success_rate
        )
        
        return success_rate >= 0.3
        
    except Exception as e:
        logger.error("Failed to validate extracted data", error=str(e))
        return False


# ===================================
# BULK OPERATIONS
# ===================================

async def bulk_extract(
    video_ids: List[str],
    selected_columns: List[str],
    user_id: str,
    db: Session
) -> Dict[str, Any]:
    """
    Extract data from multiple videos with same columns.
    
    Args:
        video_ids: List of video IDs
        selected_columns: Columns to extract
        user_id: User ID
        db: Database session
        
    Returns:
        Results dictionary with success/failure counts
    """
    results = []
    success_count = 0
    failure_count = 0
    errors = []
    
    for video_id in video_ids:
        try:
            extraction = await extract_data(
                video_id=video_id,
                selected_columns=selected_columns,
                user_id=user_id,
                db=db
            )
            
            results.append({
                "video_id": video_id,
                "extraction_id": str(extraction.id),
                "success": True
            })
            success_count += 1
            
        except Exception as e:
            results.append({
                "video_id": video_id,
                "success": False,
                "error": str(e)
            })
            errors.append({
                "video_id": video_id,
                "error": str(e)
            })
            failure_count += 1
    
    logger.info(
        "Bulk extraction completed",
        total=len(video_ids),
        success=success_count,
        failed=failure_count
    )
    
    return {
        "success_count": success_count,
        "failure_count": failure_count,
        "total": len(video_ids),
        "results": results,
        "errors": errors if errors else None
    }