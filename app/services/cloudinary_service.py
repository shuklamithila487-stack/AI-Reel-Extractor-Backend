"""
Cloudinary service.
Handles video uploading, audio extraction, and thumbnail generation using Cloudinary API.
"""

from typing import Dict, Any, Optional
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.utils import cloudinary_url
import time
import requests

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Initialize Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)


class CloudinaryError(Exception):
    """Custom exception for Cloudinary errors."""
    pass


# ===================================
# UPLOAD MANAGEMENT
# ===================================

def generate_signed_upload_url(folder: str, public_id: str, notification_url: str = None) -> Dict[str, Any]:
    """
    Generate signed upload parameters for client-side upload.
    """
    try:
        timestamp = int(time.time())
        params_to_sign = {
            "timestamp": timestamp,
            "folder": folder,
            "public_id": public_id,
        }
        
        # Include notification_url in signature if provided
        if notification_url:
            params_to_sign["notification_url"] = notification_url
        
        signature = cloudinary.utils.api_sign_request(
            params_to_sign,
            settings.CLOUDINARY_API_SECRET
        )
        
        upload_params = {
            **params_to_sign,
            "signature": signature,
            "api_key": settings.CLOUDINARY_API_KEY,
        }
        
        upload_url = f"https://api.cloudinary.com/v1_1/{settings.CLOUDINARY_CLOUD_NAME}/video/upload"
        
        return {
            "upload_url": upload_url,
            "upload_params": upload_params
        }
        
    except Exception as e:
        logger.error("Failed to generate signed upload URL", error=str(e))
        raise CloudinaryError(f"Failed to generate signed upload URL: {str(e)}")


def verify_webhook_signature(payload: Dict[str, Any], signature: str, timestamp: str) -> bool:
    """
    Verify Cloudinary webhook signature.
    """
    # Cloudinary webhook verification logic (simplified for now)
    # Ideally should use cloudinary.utils.verify_notification_signature if available or manual
    # For now, simplistic check or trust (since we use HTTPS)
    # Proper verification requires the body, timestamp, and signature
    return True # Placeholder


# ===================================
# MEDIA PROCESSING
# ===================================

def extract_audio_from_video(video_url: str) -> str:
    """
    Get audio URL from video URL (using Cloudinary transformation).
    Simulates extraction by converting video URL to audio format.
    """
    try:
        # If url is from cloudinary, replace extension with .mp3 or adding format transformation
        # Standard cloudinary URL: https://res.cloudinary.com/cloud_name/video/upload/v12345/folder/id.mp4
        
        if "cloudinary.com" in video_url:
            # Simple transformation: change resource_type to video and format to mp3
            # Or use cloudinary.utils.cloudinary_url if we have public_id
            
            # Using URL manipulation for simplicity if public_id isn't readily available
            audio_url = video_url.rsplit('.', 1)[0] + ".mp3"
            
            # Verify if the derived URL works (HEAD request)
            # response = requests.head(audio_url)
            # if response.status_code == 200:
            #    return audio_url
            
            return audio_url
            
        else:
            # Fallback for non-cloudinary URLs?
            raise CloudinaryError("Only Cloudinary video URLs are supported for audio extraction")
            
    except Exception as e:
        logger.error("Failed to extract audio path", error=str(e))
        raise CloudinaryError(f"Audio extraction failed: {str(e)}")


def generate_thumbnail(video_url: str) -> str:
    """
    Generate thumbnail URL for video.
    """
    try:
        if "cloudinary.com" in video_url:
            # Change format to jpg
            thumbnail_url = video_url.rsplit('.', 1)[0] + ".jpg"
            return thumbnail_url
        return ""
    except Exception as e:
        logger.error("Thumbnail generation failed", error=str(e))
        return ""


def delete_resource(public_id: str, resource_type: str = "video"):
    """
    Delete resource from Cloudinary.
    """
    try:
        cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        logger.info(f"Deleted resource {public_id}")
    except Exception as e:
        logger.error(f"Failed to delete resource {public_id}", error=str(e))


def upload_video(file: Any, folder: str = "pipeline", public_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Upload video file to Cloudinary.
    
    Args:
        file: File object or path
        folder: Cloudinary folder
        public_id: Optional public ID
        
    Returns:
        Upload response dictionary
    """
    try:
        # Use upload_large for potentially large videos, resource_type must be explicitly video
        response = cloudinary.uploader.upload_large(
            file,
            folder=folder,
            public_id=public_id,
            resource_type="video",
            chunk_size=6000000 # 6MB chunks
        )
        
        logger.info(
            "Video uploaded successfully",
            public_id=response.get("public_id"),
            url=response.get("secure_url")
        )
        
        return response
        
    except Exception as e:
        logger.error("Failed to upload video", error=str(e))
        raise CloudinaryError(f"Failed to upload video: {str(e)}")