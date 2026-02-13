"""
Security utilities for authentication and authorization.
Handles JWT tokens, password hashing, and security helpers.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import hashlib

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# ===================================
# PASSWORD HASHING
# ===================================

# Bcrypt context for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password meets minimum requirements.
    
    Requirements:
    - Minimum length (from settings)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    return True, None


# ===================================
# JWT TOKEN HANDLING
# ===================================

def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: Subject of the token (usually user_id)
        expires_delta: Token expiration time delta
        additional_claims: Additional claims to include in token
        
    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "exp": expire,
        "iat": datetime.utcnow(),
        "sub": str(subject)
    }
    
    # Add additional claims if provided
    if additional_claims:
        to_encode.update(additional_claims)
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token to decode
        
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def get_user_id_from_token(token: str) -> Optional[str]:
    """
    Extract user_id from JWT token.
    
    Args:
        token: JWT token
        
    Returns:
        User ID or None if token is invalid
    """
    payload = decode_access_token(token)
    if payload is None:
        return None
    return payload.get("sub")


# ===================================
# TOKEN GENERATION
# ===================================

def generate_verification_token() -> str:
    """
    Generate a secure random token for email verification.
    
    Returns:
        64-character hex token
    """
    return secrets.token_urlsafe(48)  # 48 bytes = 64 characters in base64


def generate_password_reset_token() -> str:
    """
    Generate a secure random token for password reset.
    
    Returns:
        64-character hex token
    """
    return secrets.token_urlsafe(48)


# ===================================
# CLOUDINARY SIGNATURE
# ===================================

def generate_cloudinary_signature(
    params: Dict[str, Any],
    api_secret: Optional[str] = None
) -> str:
    """
    Generate Cloudinary API signature.
    
    Args:
        params: Parameters to sign (timestamp, folder, etc.)
        api_secret: Cloudinary API secret (uses settings if not provided)
        
    Returns:
        SHA-256 signature
    """
    if api_secret is None:
        api_secret = settings.CLOUDINARY_API_SECRET
    
    # Sort parameters by key
    sorted_params = sorted(params.items())
    
    # Create string to sign: key1=value1&key2=value2
    params_str = "&".join([f"{k}={v}" for k, v in sorted_params])
    
    # Append API secret
    to_sign = f"{params_str}{api_secret}"
    
    # Generate SHA-256 hash
    signature = hashlib.sha256(to_sign.encode()).hexdigest()
    
    return signature


def verify_cloudinary_signature(
    params: Dict[str, Any],
    signature: str,
    api_secret: Optional[str] = None
) -> bool:
    """
    Verify Cloudinary webhook signature.
    
    Args:
        params: Webhook parameters
        signature: Signature to verify
        api_secret: Cloudinary API secret (uses settings if not provided)
        
    Returns:
        True if signature is valid, False otherwise
    """
    expected_signature = generate_cloudinary_signature(params, api_secret)
    return secrets.compare_digest(signature, expected_signature)


# ===================================
# SECURITY HELPERS
# ===================================

def is_safe_url(url: str, allowed_hosts: Optional[list] = None) -> bool:
    """
    Check if a URL is safe for redirects.
    
    Args:
        url: URL to check
        allowed_hosts: List of allowed hosts
        
    Returns:
        True if URL is safe, False otherwise
    """
    if allowed_hosts is None:
        allowed_hosts = [settings.FRONTEND_URL, settings.BACKEND_URL]
    
    # Simple check: URL should start with one of the allowed hosts
    return any(url.startswith(host) for host in allowed_hosts)


def generate_correlation_id() -> str:
    """
    Generate a unique correlation ID for request tracing.
    
    Returns:
        UUID-style correlation ID
    """
    return secrets.token_urlsafe(16)


def constant_time_compare(val1: str, val2: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks.
    
    Args:
        val1: First string
        val2: Second string
        
    Returns:
        True if strings are equal, False otherwise
    """
    return secrets.compare_digest(val1, val2)


# ===================================
# RATE LIMITING HELPERS
# ===================================

def generate_rate_limit_key(identifier: str, resource: str) -> str:
    """
    Generate a key for rate limiting.
    
    Args:
        identifier: User ID, IP address, etc.
        resource: Resource being accessed (e.g., 'login', 'upload')
        
    Returns:
        Rate limit key
    """
    return f"rate_limit:{resource}:{identifier}"


# ===================================
# EMAIL VERIFICATION HELPERS
# ===================================

def create_email_verification_link(token: str) -> str:
    """
    Create email verification link.
    
    Args:
        token: Verification token
        
    Returns:
        Full verification URL
    """
    return f"{settings.FRONTEND_URL}/verify-email?token={token}"


def create_password_reset_link(token: str) -> str:
    """
    Create password reset link.
    
    Args:
        token: Reset token
        
    Returns:
        Full reset URL
    """
    return f"{settings.FRONTEND_URL}/reset-password?token={token}"


# ===================================
# TESTING HELPERS
# ===================================

def create_test_token(user_id: str, expires_minutes: int = 60) -> str:
    """
    Create a test JWT token (for testing only).
    
    Args:
        user_id: User ID
        expires_minutes: Token expiry in minutes
        
    Returns:
        JWT token
    """
    return create_access_token(
        subject=user_id,
        expires_delta=timedelta(minutes=expires_minutes)
    )


# ===================================
# EXAMPLE USAGE
# ===================================

if __name__ == "__main__":
    # Test password hashing
    password = "Test123Password"
    hashed = hash_password(password)
    print(f"Hashed password: {hashed}")
    print(f"Verification: {verify_password(password, hashed)}")
    
    # Test password strength validation
    is_valid, error = validate_password_strength("weak")
    print(f"\nPassword 'weak' validation: {is_valid}, {error}")
    
    is_valid, error = validate_password_strength("StrongPass123")
    print(f"Password 'StrongPass123' validation: {is_valid}, {error}")
    
    # Test JWT token
    token = create_access_token(subject="user_123")
    print(f"\nGenerated JWT: {token[:50]}...")
    
    decoded = decode_access_token(token)
    print(f"Decoded payload: {decoded}")
    
    # Test token generation
    verification_token = generate_verification_token()
    print(f"\nVerification token: {verification_token}")
    
    # Test Cloudinary signature
    params = {"timestamp": 1234567890, "folder": "test"}
    signature = generate_cloudinary_signature(params)
    print(f"\nCloudinary signature: {signature}")