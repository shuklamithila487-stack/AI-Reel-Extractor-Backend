"""
Pydantic schemas for request/response validation.
Exports all schema models for easy importing.
"""

# Common schemas
from app.schemas.common import (
    PaginatedResponse,
    SuccessResponse,
    ErrorResponse,
    MessageResponse,
    StatusResponse,
    HealthResponse,
    BulkOperationResponse,
    ValidationError,
)

# Auth schemas
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    LoginResponse,
    EmailVerificationRequest,
    EmailVerification,
    PasswordResetRequest,
    PasswordReset,
    PasswordChange,
    RefreshTokenRequest,
    LogoutResponse,
)

# User schemas
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserProfileResponse,
    NotificationPreferences,
    UserStats,
    UserListItem,
    AccountStatusUpdate,
)

# Video schemas
from app.schemas.video import (
    VideoUploadURL,
    VideoProgress,
    VideoStatus,
    VideoResponse,
    VideoListItem,
    VideoListResponse,
    VideoFilterParams,
    VideoDeleteResponse,
    CloudinaryWebhook,
    TranscriptResponse,
)

# Extraction schemas
from app.schemas.extraction import (
    ColumnSuggestion,
    ExtractionRequest,
    ExtractionResponse,
    ExtractionHistoryItem,
    ExtractionHistory,
    ExtractionStatus,
    ReExtractionRequest,
    ColumnValidation,
    ExtractedField,
    DetailedExtractionResponse,
    ExtractionQualityMetrics,
    BulkExtractionRequest,
    BulkExtractionResponse,
)

__all__ = [
    # Common
    "PaginatedResponse",
    "SuccessResponse",
    "ErrorResponse",
    "MessageResponse",
    "StatusResponse",
    "HealthResponse",
    "BulkOperationResponse",
    "ValidationError",
    
    # Auth
    "UserRegister",
    "UserLogin",
    "TokenResponse",
    "LoginResponse",
    "EmailVerificationRequest",
    "EmailVerification",
    "PasswordResetRequest",
    "PasswordReset",
    "PasswordChange",
    "RefreshTokenRequest",
    "LogoutResponse",
    
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserProfileResponse",
    "NotificationPreferences",
    "UserStats",
    "UserListItem",
    "AccountStatusUpdate",
    
    # Video
    "VideoUploadURL",
    "VideoProgress",
    "VideoStatus",
    "VideoResponse",
    "VideoListItem",
    "VideoListResponse",
    "VideoFilterParams",
    "VideoDeleteResponse",
    "CloudinaryWebhook",
    "TranscriptResponse",
    
    # Extraction
    "ColumnSuggestion",
    "ExtractionRequest",
    "ExtractionResponse",
    "ExtractionHistoryItem",
    "ExtractionHistory",
    "ExtractionStatus",
    "ReExtractionRequest",
    "ColumnValidation",
    "ExtractedField",
    "DetailedExtractionResponse",
    "ExtractionQualityMetrics",
    "BulkExtractionRequest",
    "BulkExtractionResponse",
]