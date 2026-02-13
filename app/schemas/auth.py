"""
Authentication Pydantic schemas.
Handles registration, login, email verification, password reset.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    """
    User registration schema.
    """
    email: EmailStr
    password: str = Field(
        min_length=8,
        description="Password must be at least 8 characters"
    )
    full_name: str = Field(
        min_length=1,
        max_length=255,
        description="User's full name"
    )
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "email": "user@example.com",
                "password": "SecurePass123",
                "full_name": "John Doe"
            }]
        }
    }


class UserLogin(BaseModel):
    """
    User login schema.
    """
    email: EmailStr
    password: str
    remember_me: bool = False
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "email": "user@example.com",
                "password": "SecurePass123",
                "remember_me": False
            }]
        }
    }


class TokenResponse(BaseModel):
    """
    JWT token response.
    """
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 604800  # 7 days in seconds
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 604800
            }]
        }
    }


class TokenPayload(BaseModel):
    """
    JWT token payload schema.
    """
    sub: Optional[str] = None
    exp: Optional[int] = None


class LoginResponse(BaseModel):
    """
    Complete login response with user and token.
    """
    user: dict  # Will be UserResponse
    token: TokenResponse
    message: str = "Login successful"


class EmailVerificationRequest(BaseModel):
    """
    Request email verification (resend).
    """
    email: EmailStr


class EmailVerification(BaseModel):
    """
    Verify email with token.
    """
    token: str = Field(
        min_length=64,
        max_length=64,
        description="Email verification token"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2"
            }]
        }
    }


class PasswordResetRequest(BaseModel):
    """
    Request password reset.
    """
    email: EmailStr
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "email": "user@example.com"
            }]
        }
    }


class PasswordReset(BaseModel):
    """
    Reset password with token.
    """
    token: str = Field(
        min_length=64,
        max_length=64,
        description="Password reset token"
    )
    new_password: str = Field(
        min_length=8,
        description="New password"
    )
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2",
                "new_password": "NewSecurePass123"
            }]
        }
    }


class PasswordChange(BaseModel):
    """
    Change password (authenticated user).
    """
    current_password: str
    new_password: str = Field(min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class RefreshTokenRequest(BaseModel):
    """
    Refresh access token.
    """
    refresh_token: str


class LogoutResponse(BaseModel):
    """
    Logout response.
    """
    success: bool = True
    message: str = "Logged out successfully"


class Token(TokenResponse):
    """
    Token schema alias.
    """
    pass