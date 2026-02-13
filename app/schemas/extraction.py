"""
Data extraction Pydantic schemas.
"""

from pydantic import BaseModel, Field,field_validator
from typing import List, Dict, Any, Optional
from datetime import datetime


class ColumnSuggestion(BaseModel):
    """
    AI-suggested columns for extraction.
    """
    suggested_columns: List[str] = Field(
        description="List of suggested column names"
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score for suggestions"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "suggested_columns": [
                    "Title",
                    "Description",
                    "BHK",
                    "Property Type",
                    "Location",
                    "Price",
                    "Amenities",
                    "Key Features"
                ],
                "confidence": 0.95
            }]
        }
    }


class ExtractionRequest(BaseModel):
    """
    Request to extract data with selected columns.
    """
    selected_columns: List[str] = Field(
        min_length=1,
        max_length=15,
        description="User-selected columns to extract"
    )
    
    @field_validator('selected_columns')
    @classmethod
    def validate_columns(cls, v: List[str]) -> List[str]:
        """Validate column names."""
        if not v:
            raise ValueError('At least one column must be selected')
        if len(v) > 15:
            raise ValueError('Maximum 15 columns allowed')
        
        # Remove duplicates
        unique_columns = list(dict.fromkeys(v))
        
        # Validate column names (basic validation)
        for col in unique_columns:
            if not col or not col.strip():
                raise ValueError('Column names cannot be empty')
            if len(col) > 100:
                raise ValueError('Column names must be under 100 characters')
        
        return unique_columns
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "selected_columns": [
                    "Title",
                    "BHK",
                    "Location",
                    "Price",
                    "Amenities"
                ]
            }]
        }
    }


class ExtractionResponse(BaseModel):
    """
    Extraction result response.
    """
    id: str
    video_id: str
    extracted_data: Dict[str, Any]
    extraction_number: int
    selected_columns: List[str]
    created_at: datetime
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "ext-123",
                "video_id": "550e8400-e29b-41d4-a716-446655440000",
                "extracted_data": {
                    "Title": "Spacious 2BHK in Shivaji Park",
                    "BHK": "2BHK",
                    "Location": "Chhatrapati Shivaji Park, Kolhapur",
                    "Price": "Negotiable",
                    "Amenities": "Lift, Parking, Private Terrace"
                },
                "extraction_number": 1,
                "selected_columns": ["Title", "BHK", "Location", "Price", "Amenities"],
                "created_at": "2026-02-13T00:00:00Z"
            }]
        }
    }


class ExtractionHistoryItem(BaseModel):
    """
    Single extraction in history.
    """
    id: str
    extraction_number: int
    selected_columns: List[str]
    extracted_data: Dict[str, Any]
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class ExtractionHistory(BaseModel):
    """
    Complete extraction history for a video.
    """
    video_id: str
    extractions: List[ExtractionHistoryItem]
    total_extractions: int
    extractions_remaining: int
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "video_id": "550e8400-e29b-41d4-a716-446655440000",
                "extractions": [
                    {
                        "id": "ext-1",
                        "extraction_number": 1,
                        "selected_columns": ["Title", "Location"],
                        "extracted_data": {
                            "Title": "2BHK Flat",
                            "Location": "Kolhapur"
                        },
                        "created_at": "2026-02-13T00:00:00Z"
                    }
                ],
                "total_extractions": 1,
                "extractions_remaining": 2
            }]
        }
    }


class ExtractionStatus(BaseModel):
    """
    Status of extraction process.
    """
    status: str  # pending, processing, completed, failed
    message: str
    extraction_count: int
    extractions_remaining: int
    
    # If failed
    error: Optional[str] = None
    
    # If completed
    extraction_id: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None


class ReExtractionRequest(BaseModel):
    """
    Request to re-extract with different columns.
    """
    selected_columns: List[str] = Field(
        min_length=1,
        max_length=15
    )
    replace_latest: bool = Field(
        default=False,
        description="Replace the latest extraction instead of creating new one"
    )


class ColumnValidation(BaseModel):
    """
    Validation result for column selection.
    """
    is_valid: bool
    message: str
    suggested_alternatives: Optional[List[str]] = None


class ExtractedField(BaseModel):
    """
    Single extracted field with metadata.
    """
    column_name: str
    value: Any
    confidence: Optional[float] = None
    source_location: Optional[str] = None  # Position in transcript


class DetailedExtractionResponse(BaseModel):
    """
    Extraction response with field-level details.
    """
    id: str
    video_id: str
    extraction_number: int
    fields: List[ExtractedField]
    overall_confidence: float
    processing_time_seconds: float
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class ExtractionQualityMetrics(BaseModel):
    """
    Quality metrics for extraction.
    """
    completeness: float  # Percentage of fields successfully extracted
    confidence_average: float  # Average confidence across all fields
    fields_extracted: int
    fields_failed: int
    processing_time_seconds: float


class BulkExtractionRequest(BaseModel):
    """
    Extract multiple videos with same columns.
    """
    video_ids: List[str] = Field(min_length=1, max_length=10)
    selected_columns: List[str] = Field(min_length=1, max_length=15)


class BulkExtractionResponse(BaseModel):
    """
    Response for bulk extraction.
    """
    success_count: int
    failure_count: int
    total: int
    results: List[Dict[str, Any]]
    errors: Optional[List[Dict[str, str]]] = None