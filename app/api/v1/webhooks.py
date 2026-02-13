from typing import Any, Dict
from fastapi import APIRouter, Header, HTTPException, Request, Depends
from sqlalchemy.orm import Session
import json

from app.api import deps
from app.services import cloudinary_service, video_service
from app.tasks import video_tasks
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/cloudinary", status_code=200)
async def cloudinary_webhook(
    request: Request,
    x_cld_signature: str = Header(None),
    x_cld_timestamp: str = Header(None),
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Handle Cloudinary upload notifications.
    """
    try:
        body_bytes = await request.body()
        try:
            data = await request.json()
        except json.JSONDecodeError:
            logger.warning("Webhook received invalid JSON", body_length=len(body_bytes))
            return {"result": "error", "message": "Invalid JSON"}
        
        # Verify signature properly (using timestamp + body if needed, or Cloudinary's method)
        # simplistic verification:
        # if not cloudinary_service.verify_webhook_signature(data, x_cld_signature):
        #     raise HTTPException(status_code=400, detail="Invalid signature")
        
        notification_type = data.get("notification_type")
        
        if notification_type == "upload":
            public_id = data.get("public_id")
            
            if not public_id:
                logger.warning("Webhook missing public_id", data=str(data)[:100])
                return {"result": "error", "message": "Missing public_id"}

            # video_id is usually part of the folder or public_id structure if we set it up that way
            # In video_service.generate_upload_url, we set folder=pipeline/{video_id}
            # So public_id might look like "pipeline/UUID/filename" or just "pipeline/UUID" if ID was used as public_id
            
            # Extract video_id from public_id or context
            # Strategy: Split by '/' and look for 'pipeline' prefix
            parts = public_id.split("/")
            
            video_id = None
            if len(parts) >= 2 and parts[0] == "pipeline":
                # pipeline/{video_id}/{filename} OR pipeline/{video_id}
                video_id = parts[1]
            
            # Alternative: check context if available
            context = data.get("context", {})
            if not video_id and context and "custom" in context:
                 video_id = context["custom"].get("video_id")
            
            if video_id:
                # Update video record with URL and metadata
                video_url = data.get("secure_url")
                duration = data.get("duration")
                
                # Update DB
                try:
                    video = video_service.update_video_status(
                        video_id, 
                        "uploaded", 
                        db,
                        video_url=video_url,
                        duration_seconds=int(duration) if duration else None,
                        original_filename=data.get("original_filename")
                    )
                    
                    # Trigger processing task
                    # Correct task name is process_video_pipeline
                    video_tasks.process_video_pipeline(video_id)
                    
                    logger.info(f"Video upload confirmed via webhook for video_id={video_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to update video from webhook: {str(e)}", video_id=video_id)
                    # We still return 200 to Cloudinary
            else:
                logger.warning(f"Could not extract video_id from public_id: {public_id}")
                
        return {"result": "ok"}
        
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}")
        # Return 200 to Cloudinary to prevent retries on our internal logic errors,
        # unless we want them to retry.
        return {"result": "error", "message": str(e)}
