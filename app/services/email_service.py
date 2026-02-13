"""
Email service.
Handles email sending using SendGrid with Jinja2 templates.
"""

from typing import Dict, Any, Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from jinja2 import Template
import os

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import (
    create_email_verification_link,
    create_password_reset_link
)

logger = get_logger(__name__)

# Initialize SendGrid client
sg = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)


class EmailError(Exception):
    """Custom exception for email errors."""
    pass


# ===================================
# EMAIL TEMPLATES
# ===================================

def load_template(template_name: str) -> str:
    """
    Load email template from file.
    
    Args:
        template_name: Template filename (without .html)
        
    Returns:
        Template content
    """
    try:
        template_path = os.path.join("app", "templates", f"{template_name}.html")
        
        # If template file doesn't exist, use inline template
        if not os.path.exists(template_path):
            return get_inline_template(template_name)
        
        with open(template_path, 'r') as f:
            return f.read()
            
    except Exception as e:
        logger.error(f"Failed to load template {template_name}", error=str(e))
        return get_inline_template(template_name)


def get_inline_template(template_name: str) -> str:
    """
    Get inline email template (fallback).
    
    Args:
        template_name: Template name
        
    Returns:
        HTML template string
    """
    templates = {
        "email_verification": """
<!DOCTYPE html>
<html>
<head><style>body{font-family:Arial,sans-serif;}.button{background-color:#4F46E5;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;display:inline-block;}</style></head>
<body>
<h2>Welcome to Reel Intelligence! 🎉</h2>
<p>Hi {{user_name}},</p>
<p>Please verify your email address by clicking the button below:</p>
<p><a href="{{verification_link}}" class="button">Verify Email</a></p>
<p>Or copy this link: {{verification_link}}</p>
<p><small>This link expires in 24 hours.</small></p>
</body>
</html>
""",
        "password_reset": """
<!DOCTYPE html>
<html>
<head><style>body{font-family:Arial,sans-serif;}.button{background-color:#4F46E5;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;display:inline-block;}</style></head>
<body>
<h2>Reset Your Password</h2>
<p>Hi {{user_name}},</p>
<p>You requested to reset your password. Click the button below:</p>
<p><a href="{{reset_link}}" class="button">Reset Password</a></p>
<p>Or copy this link: {{reset_link}}</p>
<p><small>This link expires in 1 hour. If you didn't request this, ignore this email.</small></p>
</body>
</html>
""",
        "processing_complete": """
<!DOCTYPE html>
<html>
<head><style>body{font-family:Arial,sans-serif;}.button{background-color:#4F46E5;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;display:inline-block;}</style></head>
<body>
<h2>Your property video is ready! ✅</h2>
<p>Hi {{user_name}},</p>
<p>Your video <strong>{{video_title}}</strong> has been processed successfully.</p>
<p><strong>Extracted Information:</strong></p>
<ul>
{% for key, value in extracted_data.items() %}
<li><strong>{{key}}:</strong> {{value}}</li>
{% endfor %}
</ul>
<p><a href="{{video_url}}" class="button">View Full Details</a></p>
<p><small>You can re-extract with different columns up to {{extractions_remaining}} more times.</small></p>
</body>
</html>
""",
        "processing_failed": """
<!DOCTYPE html>
<html>
<head><style>body{font-family:Arial,sans-serif;}.button{background-color:#4F46E5;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;display:inline-block;}</style></head>
<body>
<h2>We couldn't process your video</h2>
<p>Hi {{user_name}},</p>
<p>Unfortunately, we encountered an issue processing your video.</p>
<p><strong>Error:</strong> {{error_message}}</p>
<p>{{suggested_fix}}</p>
<p><a href="{{retry_url}}" class="button">Retry Processing</a></p>
</body>
</html>
""",
        "weekly_summary": """
<!DOCTYPE html>
<html>
<head><style>body{font-family:Arial,sans-serif;}.stat-box{background:#f9fafb;padding:15px;margin:10px 0;border-radius:6px;}</style></head>
<body>
<h2>Your week in review 📊</h2>
<p>Hi {{user_name}},</p>
<p>Here's what you accomplished this week:</p>
<div class="stat-box"><strong>{{videos_uploaded}}</strong> videos uploaded</div>
<div class="stat-box"><strong>{{total_videos}}</strong> total videos in library</div>
<p><strong>Most common property type:</strong> {{top_property_type}}</p>
</body>
</html>
"""
    }
    
    return templates.get(template_name, "<html><body>{{message}}</body></html>")


def render_template(template_name: str, context: Dict[str, Any]) -> str:
    """
    Render email template with context.
    
    Args:
        template_name: Template name
        context: Template context variables
        
    Returns:
        Rendered HTML
    """
    try:
        template_content = load_template(template_name)
        template = Template(template_content)
        return template.render(**context)
    except Exception as e:
        logger.error("Failed to render template", error=str(e))
        return f"<html><body><p>Error rendering email template.</p></body></html>"


# ===================================
# EMAIL SENDING
# ===================================

def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None
) -> bool:
    """
    Send email using SendGrid.
    
    Args:
        to_email: Recipient email
        subject: Email subject
        html_content: HTML content
        from_email: Sender email (default from settings)
        from_name: Sender name (default from settings)
        
    Returns:
        True if sent successfully
        
    Raises:
        EmailError: If sending fails
    """
    try:
        if from_email is None:
            from_email = settings.SENDGRID_FROM_EMAIL
        if from_name is None:
            from_name = settings.SENDGRID_FROM_NAME
        
        message = Mail(
            from_email=Email(from_email, from_name),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content)
        )
        
        response = sg.send(message)
        
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(
                "Email sent successfully",
                to=to_email,
                subject=subject
            )
            return True
        else:
            logger.error(
                "SendGrid error",
                status_code=response.status_code,
                body=response.body
            )
            raise EmailError(f"SendGrid returned status {response.status_code}")
            
    except Exception as e:
        logger.error("Failed to send email", error=str(e))
        raise EmailError(f"Failed to send email: {str(e)}")


# ===================================
# SPECIFIC EMAIL TYPES
# ===================================

def send_verification_email(user_email: str, user_name: str, token: str) -> bool:
    """
    Send email verification email.
    
    Args:
        user_email: User email
        user_name: User name
        token: Verification token
        
    Returns:
        True if sent successfully
    """
    try:
        verification_link = create_email_verification_link(token)
        
        context = {
            "user_name": user_name,
            "verification_link": verification_link
        }
        
        html_content = render_template("email_verification", context)
        
        return send_email(
            to_email=user_email,
            subject="Verify your email - Reel Intelligence",
            html_content=html_content
        )
        
    except Exception as e:
        logger.error("Failed to send verification email", error=str(e))
        return False


def send_password_reset_email(user_email: str, user_name: str, token: str) -> bool:
    """
    Send password reset email.
    
    Args:
        user_email: User email
        user_name: User name
        token: Reset token
        
    Returns:
        True if sent successfully
    """
    try:
        reset_link = create_password_reset_link(token)
        
        context = {
            "user_name": user_name,
            "reset_link": reset_link
        }
        
        html_content = render_template("password_reset", context)
        
        return send_email(
            to_email=user_email,
            subject="Reset your password - Reel Intelligence",
            html_content=html_content
        )
        
    except Exception as e:
        logger.error("Failed to send password reset email", error=str(e))
        return False


def send_processing_complete_email(
    user_email: str,
    user_name: str,
    video_title: str,
    extracted_data: Dict[str, Any],
    video_url: str,
    extractions_remaining: int
) -> bool:
    """
    Send processing complete notification.
    
    Args:
        user_email: User email
        user_name: User name
        video_title: Video title
        extracted_data: Extracted data
        video_url: Video URL
        extractions_remaining: Remaining extractions
        
    Returns:
        True if sent successfully
    """
    try:
        # Take only first 3 fields for email
        display_data = dict(list(extracted_data.items())[:3])
        
        context = {
            "user_name": user_name,
            "video_title": video_title or "Your video",
            "extracted_data": display_data,
            "video_url": video_url,
            "extractions_remaining": extractions_remaining
        }
        
        html_content = render_template("processing_complete", context)
        
        return send_email(
            to_email=user_email,
            subject=f"Your property video is ready - {video_title}",
            html_content=html_content
        )
        
    except Exception as e:
        logger.error("Failed to send processing complete email", error=str(e))
        return False


def send_processing_failed_email(
    user_email: str,
    user_name: str,
    video_id: str,
    error_message: str
) -> bool:
    """
    Send processing failed notification.
    
    Args:
        user_email: User email
        user_name: User name
        video_id: Video ID
        error_message: Error message
        
    Returns:
        True if sent successfully
    """
    try:
        retry_url = f"{settings.FRONTEND_URL}/videos/{video_id}"
        
        # Provide helpful suggestions based on error
        suggested_fix = "Please try uploading again."
        if "audio" in error_message.lower():
            suggested_fix = "Make sure your video has an audio track."
        elif "timeout" in error_message.lower():
            suggested_fix = "The video might be too long. Try a shorter video."
        
        context = {
            "user_name": user_name,
            "error_message": error_message,
            "suggested_fix": suggested_fix,
            "retry_url": retry_url
        }
        
        html_content = render_template("processing_failed", context)
        
        return send_email(
            to_email=user_email,
            subject="We couldn't process your video",
            html_content=html_content
        )
        
    except Exception as e:
        logger.error("Failed to send processing failed email", error=str(e))
        return False


def send_weekly_summary_email(
    user_email: str,
    user_name: str,
    stats: Dict[str, Any]
) -> bool:
    """
    Send weekly summary email.
    
    Args:
        user_email: User email
        user_name: User name
        stats: Statistics dictionary
        
    Returns:
        True if sent successfully
    """
    try:
        context = {
            "user_name": user_name,
            "videos_uploaded": stats.get("videos_uploaded", 0),
            "total_videos": stats.get("total_videos", 0),
            "top_property_type": stats.get("top_property_type", "N/A")
        }
        
        html_content = render_template("weekly_summary", context)
        
        return send_email(
            to_email=user_email,
            subject=f"Your week in review - {stats.get('videos_uploaded', 0)} videos processed",
            html_content=html_content
        )
        
    except Exception as e:
        logger.error("Failed to send weekly summary email", error=str(e))
        return False