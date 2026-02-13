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
    video = video_service.get_video_details(video_id, str(current_user.id), db)
    
    # 2. Retrieve suggestions
    # We stored them in an initial Extraction record with extraction_number = 0
    # Let's check get_latest_extraction first
    extraction = extraction_service.get_latest_extraction(video_id, str(current_user.id), db)
    
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
    extractions = extraction_service.get_extraction_history(video_id, str(current_user.id), db)
    
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
    video = video_service.get_video_details(video_id, str(current_user.id), db)
    
    if video.status == "processing":
         raise HTTPException(status_code=400, detail="Video is currently processing")
         
    if not extraction_service.validate_extraction_limit(video_id, db):
         raise HTTPException(status_code=400, detail="Extraction limit reached for this video")
         
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
