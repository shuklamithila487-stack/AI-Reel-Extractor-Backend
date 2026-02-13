"""
Core configuration settings for the application.
Uses Pydantic BaseSettings for environment variable validation.
"""

from typing import List, Optional
from pydantic import Field, field_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
import secrets


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )
    
    # ===================================
    # APPLICATION
    # ===================================
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=False, description="Debug mode")
    APP_NAME: str = Field(default="Reel Intelligence", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    
    BACKEND_URL: str = Field(default="http://localhost:5000", description="Backend URL")
    FRONTEND_URL: str = Field(default="http://localhost:3000", description="Frontend URL")
    
    # ===================================
    # DATABASE
    # ===================================
    DATABASE_URL: str = Field(
        default="postgresql://arunshukla@localhost:5432/reelData",
        description="PostgreSQL connection string"
    )
    
    # Connection pool settings
    DB_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Max overflow connections")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Pool timeout in seconds")
    DB_POOL_RECYCLE: int = Field(default=3600, description="Connection recycle time")
    
    # ===================================
    # AUTHENTICATION & SECURITY
    # ===================================
    JWT_SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="JWT secret key - MUST be set in production"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=10080, description="Token expiry (7 days)")
    
    # Password requirements
    PASSWORD_MIN_LENGTH: int = Field(default=8, description="Minimum password length")
    
    # Account lockout
    MAX_LOGIN_ATTEMPTS: int = Field(default=5, description="Max failed login attempts")
    LOCKOUT_DURATION_MINUTES: int = Field(default=15, description="Account lockout duration")
    
    # ===================================
    # CLOUDINARY
    # ===================================
    CLOUDINARY_CLOUD_NAME: str = Field(..., description="Cloudinary cloud name (required)")
    CLOUDINARY_API_KEY: str = Field(..., description="Cloudinary API key (required)")
    CLOUDINARY_API_SECRET: str = Field(..., description="Cloudinary API secret (required)")
    
    # ===================================
    # SARVAM API
    # ===================================
    SARVAM_API_KEY: str = Field(..., description="Sarvam API key (required)")
    SARVAM_API_ENDPOINT: str = Field(
        default="https://api.sarvam.ai/speech-to-text",
        description="Sarvam API endpoint"
    )
    SARVAM_MODEL: str = Field(default="saarika:v2.5", description="Sarvam model version")
    SARVAM_LANGUAGE_CODE: str = Field(default="unknown", description="Language code (unknown = auto-detect)")
    
    # ===================================
    # CLAUDE API
    # ===================================
    # ANTHROPIC_API_KEY: str = Field(..., description="Anthropic API key (required)")
    # CLAUDE_MODEL: str = Field(default="claude-3-sonnet-20240229", description="Claude model version")
    # CLAUDE_MAX_TOKENS: int = Field(default=4000, description="Max tokens for Claude API")
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key (required)")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="OpenAI model version")
    OPENAI_MAX_TOKENS: int = Field(default=4000, description="Max tokens for OpenAI API")
    
    # ===================================
    # SENDGRID
    # ===================================
    SENDGRID_API_KEY: str = Field(..., description="SendGrid API key (required)")
    SENDGRID_FROM_EMAIL: str = Field(..., description="From email address (required)")
    SENDGRID_FROM_NAME: str = Field(default="Reel Intelligence", description="From name")
    
    # Email expiration
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = Field(default=24, description="Email verification link expiry")
    PASSWORD_RESET_EXPIRE_HOURS: int = Field(default=1, description="Password reset link expiry")
    
    # ===================================
    # HUEY (Background Jobs)
    # ===================================
    HUEY_BACKEND: str = Field(default="postgresql", description="Huey backend: postgresql or redis")
    HUEY_NAME: str = Field(default="reel_intelligence_queue", description="Huey queue name")
    REDIS_URL: Optional[str] = Field(default=None, description="Redis URL (if using Redis backend)")
    
    # Worker settings
    HUEY_WORKERS: int = Field(default=2, description="Number of Huey worker processes")
    HUEY_IMMEDIATE: bool = Field(default=False, description="Run tasks immediately (for testing)")
    
    # ===================================
    # VIDEO PROCESSING
    # ===================================
    MAX_VIDEO_SIZE_MB: int = Field(default=100, description="Max video upload size in MB")
    MAX_VIDEO_DURATION_SECONDS: int = Field(default=180, description="Max video duration (3 minutes)")
    ALLOWED_VIDEO_EXTENSIONS: str = Field(default="mp4,mov,avi,mkv", description="Allowed video extensions")
    
    # Audio processing
    AUDIO_CHUNK_DURATION_SECONDS: int = Field(default=30, description="Audio chunk duration for transcription")
    
    # Extraction limits
    MAX_EXTRACTIONS_PER_VIDEO: int = Field(default=3, description="Max re-extractions per video")
    
    # ===================================
    # RATE LIMITING
    # ===================================
    RATE_LIMIT_PER_MINUTE: int = Field(default=100, description="API rate limit per minute")
    RATE_LIMIT_BURST: int = Field(default=20, description="Rate limit burst allowance")
    
    # ===================================
    # MONITORING
    # ===================================
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    SENTRY_ENVIRONMENT: str = Field(default="development", description="Sentry environment")
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.1, description="Sentry traces sample rate")
    
    # ===================================
    # CORS
    # ===================================
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="Comma-separated list of allowed origins"
    )
    
    # ===================================
    # LOGGING
    # ===================================
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # ===================================
    # COMPUTED PROPERTIES
    # ===================================
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def allowed_video_extensions_list(self) -> List[str]:
        """Parse allowed extensions string into list."""
        return [ext.strip().lower() for ext in self.ALLOWED_VIDEO_EXTENSIONS.split(",")]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.ENVIRONMENT.lower() == "development"
    
    # ===================================
    # VALIDATORS
    # ===================================
    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """Validate JWT secret is secure in production."""
        environment = info.data.get("ENVIRONMENT", "development")
        if environment.lower() == "production" and len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 characters in production. "
                "Generate with: openssl rand -hex 32"
            )
        return v
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(allowed_levels)}")
        return v_upper
    
    # ===================================
    # CLOUDINARY WEBHOOK VALIDATION
    # ===================================
    def get_cloudinary_webhook_url(self) -> str:
        """Get full Cloudinary webhook URL."""
        return f"{self.BACKEND_URL}/api/v1/webhooks/cloudinary"


# ===================================
# GLOBAL SETTINGS INSTANCE
# ===================================
settings = Settings()


# ===================================
# HELPER FUNCTIONS
# ===================================
def get_settings() -> Settings:
    """
    Dependency function to get settings instance.
    Useful for testing with dependency overrides.
    """
    return settings


def print_settings_summary():
    """Print settings summary (for debugging)."""
    print("\n" + "="*60)
    print("APPLICATION SETTINGS")
    print("="*60)
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Debug Mode: {settings.DEBUG}")
    print(f"Backend URL: {settings.BACKEND_URL}")
    print(f"Frontend URL: {settings.FRONTEND_URL}")
    print(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Not set'}")
    print(f"Log Level: {settings.LOG_LEVEL}")
    print(f"CORS Origins: {len(settings.cors_origins_list)} origins")
    print(f"Huey Workers: {settings.HUEY_WORKERS}")
    print(f"Max Video Size: {settings.MAX_VIDEO_SIZE_MB}MB")
    print(f"Sentry Enabled: {bool(settings.SENTRY_DSN)}")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Test settings loading
    print_settings_summary()