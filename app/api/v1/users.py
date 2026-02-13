from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from uuid import UUID

from app import models
from app.api import deps
from app.schemas import user as user_schemas
from app.core import security
from app.core.config import settings

router = APIRouter()

@router.get("/me", response_model=user_schemas.UserProfileResponse)
def read_user_me(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Get current user profile (with additional details).
    """
    # Calculate stats if needed or use stored values
    # For now, return basic user object which matches the schema via from_attributes
    # If stats fields are missing on user model, we might need to compute them
    
    # Let's mock stats for now or query them
    # from app.models import Video, Extraction
    # total_videos = db.query(Video).filter(Video.user_id == current_user.id).count()
    # total_extractions = db.query(Extraction).filter(Extraction.user_id == current_user.id).count()
    
    # We can attach them dynamically
    # current_user.total_videos = total_videos
    # current_user.total_extractions = total_extractions
    
    return current_user

@router.put("/me", response_model=user_schemas.UserResponse)
def update_user_me(
    *,
    db: Session = Depends(deps.get_db),
    user_in: user_schemas.UserUpdate,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Update own user profile.
    """
    user_data = user_in.model_dump(exclude_unset=True)
    
    for field, value in user_data.items():
        setattr(current_user, field, value)
    
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.put("/me/notifications", response_model=user_schemas.NotificationPreferences)
def update_notification_preferences(
    *,
    db: Session = Depends(deps.get_db),
    prefs_in: user_schemas.NotificationPreferences,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Update notification preferences.
    """
    prefs_data = prefs_in.model_dump(exclude_unset=True)
    
    for field, value in prefs_data.items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)
            
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

# Admin routes could go here (e.g., list all users) but restricting for MVP
# @router.get("/", response_model=List[user_schemas.UserListItem], dependencies=[Depends(deps.get_current_active_superuser)])
# ...
