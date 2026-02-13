"""
Authentication service.
Handles user registration, login, email verification, password reset.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import User, EmailVerification, PasswordReset, UsageStats
from app.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    generate_verification_token,
    generate_password_reset_token,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas import UserRegister, UserLogin, TokenResponse, UserResponse

logger = get_logger(__name__)


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass


class RegistrationError(Exception):
    """Custom exception for registration errors."""
    pass


# ===================================
# REGISTRATION
# ===================================

def register_user(
    data: UserRegister,
    db: Session
) -> Tuple[User, str]:
    """
    Register a new user.
    
    Args:
        data: User registration data
        db: Database session
        
    Returns:
        Tuple of (user, verification_token)
        
    Raises:
        RegistrationError: If registration fails
    """
    try:
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == data.email).first()
        if existing_user:
            logger.warning("Registration attempt with existing email", email=data.email)
            raise RegistrationError("Email already registered")
        
        # Validate password strength
        is_valid, error_msg = validate_password_strength(data.password)
        if not is_valid:
            raise RegistrationError(error_msg)
        
        # Hash password
        password_hash = hash_password(data.password)
        
        # Create user
        user = User(
            email=data.email,
            password_hash=password_hash,
            full_name=data.full_name,
            email_verified=False,
            account_status="active"
        )
        
        db.add(user)
        db.flush()  # Get user.id without committing
        
        # Create usage stats
        stats = UsageStats(user_id=user.id)
        db.add(stats)
        
        # Generate verification token
        token = generate_verification_token()
        expires_at = datetime.utcnow() + timedelta(
            hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS
        )
        
        verification = EmailVerification(
            user_id=user.id,
            token=token,
            email=data.email,
            expires_at=expires_at
        )
        
        db.add(verification)
        db.commit()
        db.refresh(user)
        
        logger.info("User registered successfully", user_id=str(user.id), email=user.email)
        
        return user, token
        
    except IntegrityError as e:
        db.rollback()
        logger.error("Database integrity error during registration", error=str(e))
        raise RegistrationError("Email already registered")
    except Exception as e:
        db.rollback()
        logger.error("Registration failed", error=str(e))
        raise RegistrationError(f"Registration failed: {str(e)}")


# ===================================
# EMAIL VERIFICATION
# ===================================

def verify_email(token: str, db: Session) -> User:
    """
    Verify user email with token.
    
    Args:
        token: Email verification token
        db: Database session
        
    Returns:
        Verified user
        
    Raises:
        AuthenticationError: If verification fails
    """
    try:
        # Find verification record
        verification = db.query(EmailVerification).filter(
            EmailVerification.token == token,
            EmailVerification.verified_at.is_(None)
        ).first()
        
        if not verification:
            logger.warning("Invalid verification token", token=token[:10])
            raise AuthenticationError("Invalid or expired verification token")
        
        # Check if expired
        if verification.expires_at < datetime.utcnow():
            logger.warning("Expired verification token", token=token[:10])
            raise AuthenticationError("Verification token has expired")
        
        # Get user
        user = db.query(User).filter(User.id == verification.user_id).first()
        if not user:
            raise AuthenticationError("User not found")
        
        # Mark email as verified
        user.verify_email()
        verification.verified_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        
        logger.info("Email verified successfully", user_id=str(user.id))
        
        return user
        
    except AuthenticationError:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Email verification failed", error=str(e))
        raise AuthenticationError(f"Verification failed: {str(e)}")


def resend_verification_email(email: str, db: Session) -> str:
    """
    Resend verification email.
    
    Args:
        email: User email
        db: Database session
        
    Returns:
        New verification token
        
    Raises:
        AuthenticationError: If user not found or already verified
    """
    try:
        # Find user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Don't reveal if email exists
            logger.warning("Verification resend for non-existent email", email=email)
            raise AuthenticationError("If the email exists, a verification link has been sent")
        
        if user.email_verified:
            raise AuthenticationError("Email already verified")
        
        # Generate new token
        token = generate_verification_token()
        expires_at = datetime.utcnow() + timedelta(
            hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS
        )
        
        # Create new verification record
        verification = EmailVerification(
            user_id=user.id,
            token=token,
            email=email,
            expires_at=expires_at
        )
        
        db.add(verification)
        db.commit()
        
        logger.info("Verification email resent", user_id=str(user.id))
        
        return token
        
    except AuthenticationError:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to resend verification", error=str(e))
        raise AuthenticationError("Failed to resend verification email")


# ===================================
# LOGIN
# ===================================

def login_user(
    data: UserLogin,
    db: Session
) -> Tuple[User, str]:
    """
    Authenticate user and generate token.
    
    Args:
        data: Login credentials
        db: Database session
        
    Returns:
        Tuple of (user, access_token)
        
    Raises:
        AuthenticationError: If login fails
    """
    try:
        # Find user by email
        user = db.query(User).filter(User.email == data.email).first()
        
        if not user:
            logger.warning("Login attempt with non-existent email", email=data.email)
            raise AuthenticationError("Invalid email or password")
        
        # Check if account is locked
        if user.is_locked():
            logger.warning("Login attempt on locked account", user_id=str(user.id))
            raise AuthenticationError("Account is temporarily locked. Please try again later.")
        
        # Verify password
        if not verify_password(data.password, user.password_hash):
            # Increment failed login attempts
            user.increment_failed_login(max_attempts=settings.MAX_LOGIN_ATTEMPTS)
            db.commit()
            
            logger.warning("Failed login attempt", user_id=str(user.id))
            raise AuthenticationError("Invalid email or password")
        
        # Check if email is verified
        if not user.email_verified:
            logger.warning("Login attempt with unverified email", user_id=str(user.id))
            raise AuthenticationError("Please verify your email before logging in")
        
        # Check if account is active
        if not user.is_active():
            logger.warning("Login attempt on inactive account", user_id=str(user.id))
            raise AuthenticationError("Account is not active")
        
        # Reset failed login attempts
        user.reset_failed_login()
        
        # Update last login
        user.update_last_login()
        
        db.commit()
        
        # Generate access token
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        if data.remember_me:
            # Extend token expiry for "remember me"
            expires_delta = timedelta(days=30)
        
        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=expires_delta
        )
        
        logger.info("User logged in successfully", user_id=str(user.id))
        
        return user, access_token
        
    except AuthenticationError:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Login failed", error=str(e))
        raise AuthenticationError("Login failed")


# ===================================
# PASSWORD RESET
# ===================================

def request_password_reset(email: str, db: Session) -> Optional[str]:
    """
    Request password reset.
    
    Args:
        email: User email
        db: Database session
        
    Returns:
        Reset token if user exists, None otherwise
    """
    try:
        # Find user
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Don't reveal if email exists
            logger.warning("Password reset requested for non-existent email", email=email)
            return None
        
        # Generate reset token
        token = generate_password_reset_token()
        expires_at = datetime.utcnow() + timedelta(
            hours=settings.PASSWORD_RESET_EXPIRE_HOURS
        )
        
        # Create reset record
        reset = PasswordReset(
            user_id=user.id,
            token=token,
            expires_at=expires_at
        )
        
        db.add(reset)
        db.commit()
        
        logger.info("Password reset requested", user_id=str(user.id))
        
        return token
        
    except Exception as e:
        db.rollback()
        logger.error("Failed to create password reset", error=str(e))
        return None


def reset_password(token: str, new_password: str, db: Session) -> User:
    """
    Reset password with token.
    
    Args:
        token: Password reset token
        new_password: New password
        db: Database session
        
    Returns:
        Updated user
        
    Raises:
        AuthenticationError: If reset fails
    """
    try:
        # Find reset record
        reset = db.query(PasswordReset).filter(
            PasswordReset.token == token,
            PasswordReset.used_at.is_(None)
        ).first()
        
        if not reset:
            logger.warning("Invalid password reset token", token=token[:10])
            raise AuthenticationError("Invalid or expired reset token")
        
        # Check if expired
        if reset.expires_at < datetime.utcnow():
            logger.warning("Expired password reset token", token=token[:10])
            raise AuthenticationError("Reset token has expired")
        
        # Validate new password
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            raise AuthenticationError(error_msg)
        
        # Get user
        user = db.query(User).filter(User.id == reset.user_id).first()
        if not user:
            raise AuthenticationError("User not found")
        
        # Update password
        user.password_hash = hash_password(new_password)
        
        # Mark reset as used
        reset.used_at = datetime.utcnow()
        
        # Reset failed login attempts
        user.reset_failed_login()
        
        db.commit()
        db.refresh(user)
        
        logger.info("Password reset successfully", user_id=str(user.id))
        
        return user
        
    except AuthenticationError:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Password reset failed", error=str(e))
        raise AuthenticationError("Password reset failed")


def change_password(
    user_id: str,
    current_password: str,
    new_password: str,
    db: Session
) -> User:
    """
    Change password for authenticated user.
    
    Args:
        user_id: User ID
        current_password: Current password
        new_password: New password
        db: Database session
        
    Returns:
        Updated user
        
    Raises:
        AuthenticationError: If password change fails
    """
    try:
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AuthenticationError("User not found")
        
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            logger.warning("Incorrect current password", user_id=user_id)
            raise AuthenticationError("Current password is incorrect")
        
        # Validate new password
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            raise AuthenticationError(error_msg)
        
        # Check if new password is same as current
        if verify_password(new_password, user.password_hash):
            raise AuthenticationError("New password must be different from current password")
        
        # Update password
        user.password_hash = hash_password(new_password)
        
        db.commit()
        db.refresh(user)
        
        logger.info("Password changed successfully", user_id=str(user.id))
        
        return user
        
    except AuthenticationError:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Password change failed", error=str(e))
        raise AuthenticationError("Password change failed")


# ===================================
# TOKEN VALIDATION
# ===================================

def get_current_user(user_id: str, db: Session) -> Optional[User]:
    """
    Get user by ID (for JWT authentication).
    
    Args:
        user_id: User ID from JWT token
        db: Database session
        
    Returns:
        User if found, None otherwise
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            logger.warning("User not found for token", user_id=user_id)
            return None
        
        if not user.can_login():
            logger.warning("User cannot login", user_id=user_id)
            return None
        
        return user
        
    except Exception as e:
        logger.error("Failed to get current user", error=str(e))
        return None