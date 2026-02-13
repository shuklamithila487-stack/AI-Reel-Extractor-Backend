from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session

from app import models
from app.api import deps
from app.schemas import video as video_schemas
from app.schemas import extraction as extraction_schemas
from app.schemas import common
from app.services import video_service
from app.tasks import video_tasks

router = APIRouter()

@router.post("/upload-authorization", response_model=video_schemas.VideoUploadURL)
def get_upload_authorization(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Generate a signed upload URL for Cloudinary.
    """
    return video_service.generate_upload_url(user_id=str(current_user.id), db=db)


@router.post("/upload", response_model=video_schemas.VideoStatus)
def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Upload a video file directly via backend proxy.
    """
    # Upload to Cloudinary and create DB record
    video = video_service.upload_video_from_file(
        file=file,
        user_id=str(current_user.id),
        db=db,
        filename=file.filename
    )
    
    # Trigger processing pipeline
    video_tasks.process_video_pipeline(str(video.id))
    
    return video_service.get_video_status(
        video_id=str(video.id),
        user_id=str(current_user.id),
        db=db
    )


@router.get("", response_model=common.PaginatedResponse[video_schemas.VideoListItem])
def list_videos(
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search term"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", description="Sort by field"),
    sort_order: str = Query("desc", description="asc or desc"),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    List user's videos.
    """
    filters = video_schemas.VideoFilterParams(
        status=status,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    videos, total = video_service.list_user_videos(
        user_id=str(current_user.id),
        filters=filters,
        db=db
    )
    
    # Map models to schema
    video_items = [video_schemas.VideoListItem.model_validate(v) for v in videos]
    
    return common.PaginatedResponse[video_schemas.VideoListItem](
        items=video_items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
        has_prev=page > 1
    )


@router.get("/{video_id}", response_model=video_schemas.VideoStatus)
def get_video_status(
    video_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Get video status and details.
    """
    return video_service.get_video_status(video_id, str(current_user.id), db)


@router.delete("/{video_id}", response_model=video_schemas.VideoDeleteResponse)
def delete_video(
    video_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Delete a video.
    """
    video_service.delete_video(video_id, str(current_user.id), db)
    return {"success": True, "message": "Video deleted successfully", "video_id": video_id}


@router.post("/{video_id}/extract", response_model=common.MessageResponse)
def trigger_extraction(
    video_id: str,
    extraction_request: extraction_schemas.ExtractionRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Trigger data extraction for a video.
    """
    # Verify video exists and belongs to user
    video = video_service.get_video_details(video_id, str(current_user.id), db)
    
    # Trigger background task
    video_tasks.extract_data_task(
        video_id, 
        str(current_user.id), 
        extraction_request.selected_columns
    )
    
    return {"message": "Extraction started"}
