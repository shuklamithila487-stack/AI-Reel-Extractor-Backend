from typing import Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session

from app import models
from app.api import deps
from app.schemas import extraction as extraction_schemas
from app.services import extraction_service, video_service
from app.tasks import video_tasks

router = APIRouter()

@router.get("/suggest/{video_id}", response_model=extraction_schemas.ColumnSuggestion)
def get_column_suggestions(
    video_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Get AI-suggested columns for a video.
    Does not trigger new suggestion, just retrieves stored suggestions from the initial processing.
    """
    # 1. Check video access
    video = video_service.get_video_details(video_id, None, db)
    
    # 2. Retrieve suggestions
    # We stored them in an initial Extraction record with extraction_number = 0
    # Let's check get_latest_extraction first
    extraction = extraction_service.get_latest_extraction(video_id, None, db)
    
    if extraction and extraction.suggested_columns:
        return {
            "suggested_columns": extraction.suggested_columns,
            "confidence": 0.9 # Mock confidence
        }
        
    # If no extraction record, maybe check if it's still processing?
    if video.status in ["processing", "transcribing"]:
         raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Video is still processing, suggestions not ready yet"
        )
        
    return {
        "suggested_columns": [
            "Title", "Description", "Property Type", "BHK", 
            "Location", "Price", "Amenities"
        ], # Fallback defaults
        "confidence": 0.5
    }

@router.post("/suggest-more/{video_id}", response_model=extraction_schemas.ColumnSuggestion)
async def suggest_more_columns(
    video_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Dynamically trigger OpenAI to suggest MORE columns based on the transcript.
    """
    video = video_service.get_video_details(video_id, None, db)
    
    if video.suggestion_count >= 3:
        raise HTTPException(status_code=400, detail="Suggestion limit reached (3 max)")
         
    from app.services.openai_service import suggest_columns_from_transcript
    
    try:
        new_columns = await suggest_columns_from_transcript(video.transcript)
        
        # Increment suggestion count
        video.suggestion_count += 1
        
        # We append these new columns to the original extraction record 0
        from app.models import Extraction
        extraction = db.query(Extraction).filter(
            Extraction.video_id == video_id,
            Extraction.extraction_number == 0
        ).first()
        
        if extraction:
            existing = set(extraction.suggested_columns) if extraction.suggested_columns else set()
            merged = list(existing) + [c for c in new_columns if c not in existing]
            extraction.suggested_columns = merged
            db.commit()
            
            return {
                "suggested_columns": merged,
                "confidence": 0.8,
                "suggestions_remaining": max(0, 3 - video.suggestion_count)
            }
        else:
            # Create the record if it doesn't exist (unlikely but safe)
            extraction = Extraction(
                video_id=video_id,
                user_id=video.user_id,
                suggested_columns=new_columns,
                extraction_number=0
            )
            db.add(extraction)
            db.commit()
            
            return {
                "suggested_columns": new_columns,
                "confidence": 0.8,
                "suggestions_remaining": max(0, 3 - video.suggestion_count)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{video_id}", response_model=extraction_schemas.ExtractionHistory)
def get_extraction_history(
    video_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Get extraction history for a video.
    """
    # Verify video access inside service helper if reused, or here
    # get_extraction_history checks ownership
    extractions = extraction_service.get_extraction_history(video_id, None, db)
    
    # Filter out the "suggestion only" extraction (extraction_number=0) if appropriate
    # Or just return all
    visible_extractions = [e for e in extractions if e.extraction_number > 0]
    
    remaining = extraction_service.get_extractions_remaining(video_id, db)
    total = len(visible_extractions)
    
    return {
        "video_id": video_id,
        "extractions": visible_extractions,
        "total_extractions": total,
        "extractions_remaining": remaining
    }


@router.post("/extract/{video_id}", response_model=extraction_schemas.ExtractionStatus)
def request_extraction(
    video_id: str,
    request: extraction_schemas.ExtractionRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Trigger a new data extraction.
    """
    # 1. Verify eligibility (remaining extractions, status)
    video = video_service.get_video_details(video_id, None, db)
    
    if video.status == "processing":
         raise HTTPException(status_code=400, detail="Video is currently processing")
         
    if not extraction_service.validate_extraction_limit(video_id, db):
         raise HTTPException(status_code=400, detail="Extraction limit reached for this video")
         
    # Clear any previous extraction errors
    video.error_message = None
    db.commit()
         
    # 2. Trigger task
    try:
        video_tasks.extract_data_task(
            video_id, 
            request.selected_columns, 
            str(current_user.id)
        )
        
        remaining = extraction_service.get_extractions_remaining(video_id, db)
        count = 3 - remaining # Approximation
        
        return {
            "status": "processing",
            "message": "Extraction started",
            "extraction_count": count,
            "extractions_remaining": remaining
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
