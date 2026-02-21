"""
Airtable Integration Service.
Handles pushing extracted property data to Airtable.
"""

import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class AirtableError(Exception):
    """Custom exception for Airtable errors."""
    pass

async def sync_to_airtable(data: Dict[str, Any], video_id: str) -> bool:
    """
    Sync extracted data to Airtable.
    
    Args:
        data: dictionary of extracted fields and values
        video_id: The ID of the video for reference
        
    Returns:
        bool: True if successful
    """
    if not settings.AIRTABLE_API_KEY or not settings.AIRTABLE_BASE_ID:
        logger.warning("Airtable sync skipped: API Key or Base ID missing")
        return False

    url = f"https://api.airtable.com/v0/{settings.AIRTABLE_BASE_ID}/{settings.AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {settings.AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }

    # Prepare fields
    # We add the video_id as a reference if possible
    fields = data.copy()
    fields["Video ID"] = video_id
    
    payload = {
        "fields": fields
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            
            if response.status_code != 200:
                logger.error(
                    "Airtable sync failed",
                    status_code=response.status_code,
                    response=response.text,
                    video_id=video_id
                )
                return False
                
            logger.info("Airtable sync successful", video_id=video_id)
            return True
            
    except Exception as e:
        logger.error("Airtable sync exception", error=str(e), video_id=video_id)
        return False
