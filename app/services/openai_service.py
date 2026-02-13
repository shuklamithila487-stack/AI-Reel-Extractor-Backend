"""
OpenAI API service.
Handles AI-powered column suggestion and data extraction using OpenAI's GPT models.
"""

import json
from typing import List, Dict, Any
from openai import OpenAI, OpenAIError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


class OpenAIServiceError(Exception):
    """Custom exception for OpenAI API errors."""
    pass


# ===================================
# COLUMN SUGGESTION
# ===================================

async def suggest_columns_from_transcript(transcript: str) -> List[str]:
    """
    Suggest relevant columns based on transcript using OpenAI API.
    
    Args:
        transcript: Video transcript
        
    Returns:
        List of suggested column names
        
    Raises:
        OpenAIServiceError: If suggestion fails
    """
    try:
        prompt = f"""Analyze this real estate property video transcript and suggest relevant data fields to extract.

Transcript:
{truncate_transcript(transcript)}

Based on the content, suggest 8-12 column names that would be most useful for a real estate database. Consider what information is actually present in the transcript.

Return ONLY a JSON array of column names, nothing else. For example:
["Title", "Description", "BHK", "Location", "Price", "Amenities"]"""

        # Call OpenAI API
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured data from text."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=0.3
        )
        
        # Extract response
        response_text = response.choices[0].message.content.strip()
        
        # Parse JSON
        try:
            # Remove any markdown code blocks
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            suggested_columns = json.loads(response_text)
            
            # Validate response
            if not isinstance(suggested_columns, list):
                raise ValueError("Response is not a list")
            
            # Filter and clean column names
            suggested_columns = [
                str(col).strip()
                for col in suggested_columns
                if col and str(col).strip()
            ]
            
            # Limit to 12 columns
            suggested_columns = suggested_columns[:12]
            
            logger.info(
                "Columns suggested by OpenAI",
                column_count=len(suggested_columns),
                columns=suggested_columns
            )
            
            return suggested_columns
            
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse OpenAI response as JSON",
                response=response_text,
                error=str(e)
            )
            # Fallback to default columns
            return [
                "Title",
                "Description",
                "Property Type",
                "BHK",
                "Location",
                "Price",
                "Amenities",
                "Key Features"
            ]
        
    except OpenAIError as e:
        logger.error("OpenAI API error", error=str(e))
        raise OpenAIServiceError(f"OpenAI API error: {str(e)}")
    except Exception as e:
        logger.error("Column suggestion failed", error=str(e))
        raise OpenAIServiceError(f"Column suggestion failed: {str(e)}")


# ===================================
# DATA EXTRACTION
# ===================================

async def extract_fields_from_transcript(
    transcript: str,
    columns: List[str]
) -> Dict[str, Any]:
    """
    Extract specific fields from transcript using OpenAI API.
    
    Args:
        transcript: Video transcript
        columns: Column names to extract
        
    Returns:
        Dictionary with extracted data
        
    Raises:
        OpenAIServiceError: If extraction fails
    """
    try:
        # Build prompt
        columns_list = "\n".join([f"- {col}" for col in columns])
        
        prompt = f"""Extract the following information from this real estate property video transcript:

Columns to extract:
{columns_list}

Transcript:
{truncate_transcript(transcript)}

Extract the requested information and return it as a JSON object. For each field:
- If the information is present, extract it accurately
- If not found, use "Not mentioned" as the value
- Keep values concise but informative

Return ONLY a JSON object with the extracted values, nothing else. For example:
{{"Title": "2BHK Flat in Koregaon Park", "Location": "Pune", "Price": "85 Lakhs"}}"""

        # Call OpenAI API
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured data from text."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=0.1
        )
        
        # Extract response
        response_text = response.choices[0].message.content.strip()
        
        # Parse JSON
        try:
            # Remove any markdown code blocks
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            extracted_data = json.loads(response_text)
            
            # Ensure all requested columns are present
            for col in columns:
                if col not in extracted_data:
                    extracted_data[col] = "Not mentioned"
            
            logger.info(
                "Data extracted by OpenAI",
                fields_count=len(extracted_data),
                fields=list(extracted_data.keys())
            )
            
            return extracted_data
            
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse OpenAI extraction response",
                response=response_text,
                error=str(e)
            )
            # Return fallback response
            return {col: "Extraction failed" for col in columns}
        
    except OpenAIError as e:
        logger.error("OpenAI API error during extraction", error=str(e))
        raise OpenAIServiceError(f"OpenAI API error: {str(e)}")
    except Exception as e:
        logger.error("Data extraction failed", error=str(e))
        raise OpenAIServiceError(f"Data extraction failed: {str(e)}")


# ===================================
# VALIDATION
# ===================================

def validate_extraction_quality(extracted_data: Dict[str, Any]) -> float:
    """
    Validate quality of extracted data.
    
    Args:
        extracted_data: Extracted data dictionary
        
    Returns:
        Quality score (0.0 to 1.0)
    """
    try:
        if not extracted_data:
            return 0.0
        
        total_fields = len(extracted_data)
        
        # Count successfully extracted fields
        success_indicators = [
            "Not mentioned",
            "Not found",
            "N/A",
            "Unknown",
            "Extraction failed",
            ""
        ]
        
        successful_fields = sum(
            1 for value in extracted_data.values()
            if value and str(value).strip() not in success_indicators
        )
        
        quality_score = successful_fields / total_fields if total_fields > 0 else 0.0
        
        logger.info(
            "Extraction quality assessed",
            total_fields=total_fields,
            successful_fields=successful_fields,
            quality_score=quality_score
        )
        
        return quality_score
        
    except Exception as e:
        logger.error("Failed to validate extraction quality", error=str(e))
        return 0.0


# ===================================
# HELPER FUNCTIONS
# ===================================

async def test_openai_connection() -> bool:
    """
    Test OpenAI API connection.
    
    Returns:
        True if connection successful
    """
    try:
        client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "user", "content": "Hello"}
            ],
            max_tokens=10
        )
        logger.info("OpenAI API test successful")
        return True
        
    except Exception as e:
        logger.error("OpenAI API test failed", error=str(e))
        return False


def truncate_transcript(transcript: str, max_length: int = 15000) -> str:
    """
    Truncate transcript to fit within token limits.
    
    Args:
        transcript: Full transcript
        max_length: Maximum character length (approx 4000 tokens)
        
    Returns:
        Truncated transcript
    """
    if len(transcript) <= max_length:
        return transcript
    
    # Truncate and add indicator
    truncated = transcript[:max_length] + "... [transcript truncated]"
    
    logger.warning(
        "Transcript truncated",
        original_length=len(transcript),
        truncated_length=len(truncated)
    )
    
    return truncated
