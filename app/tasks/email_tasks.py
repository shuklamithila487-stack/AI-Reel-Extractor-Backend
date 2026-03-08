"""
Email sending background tasks.
Handles asynchronous email notifications.
"""

from typing import Dict, Any
from sqlalchemy.orm import Session

from app.tasks.huey_config import task, periodic_task
from huey import crontab
from app.db.database import SessionLocal
from app.models import User, Video, Extraction, Notification
from app.services import email_service
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


# ===================================
# AUTHENTICATION EMAILS
# ===================================

@task(retries=3, retry_delay=30)
def send_verification_email_task(user_id: str, token: str, **kwargs):
    """
    Send email verification email.
    
    Args:
        user_id: User ID
        token: Verification token
    """
    db = SessionLocal()
    
    try:
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            logger.error("User not found for verification email", user_id=user_id)
            return
        
        # Check notification preferences
        if not user.notify_product_updates:
            logger.info("User disabled product update emails", user_id=user_id)
            # Still send verification email - it's required
        
        # Send email
        success = email_service.send_verification_email(
            user_email=user.email,
            user_name=user.full_name or "User",
            token=token
        )
        
        if success:
            logger.info("Verification email sent", user_id=user_id)
        else:
            logger.error("Failed to send verification email", user_id=user_id)
        
    except Exception as e:
        logger.error(
            "Verification email task failed",
            user_id=user_id,
            error=str(e)
        )
    
    finally:
        db.close()


@task(retries=3, retry_delay=30)
def send_password_reset_email_task(user_id: str, token: str, **kwargs):
    """
    Send password reset email.
    
    Args:
        user_id: User ID
        token: Reset token
    """
    db = SessionLocal()
    
    try:
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            logger.error("User not found for password reset", user_id=user_id)
            return
        
        # Send email
        success = email_service.send_password_reset_email(
            user_email=user.email,
            user_name=user.full_name or "User",
            token=token
        )
        
        if success:
            logger.info("Password reset email sent", user_id=user_id)
        else:
            logger.error("Failed to send password reset email", user_id=user_id)
        
    except Exception as e:
        logger.error(
            "Password reset email task failed",
            user_id=user_id,
            error=str(e)
        )
    
    finally:
        db.close()


# ===================================
# PROCESSING NOTIFICATIONS
# ===================================

@task(retries=3, retry_delay=30)
def send_processing_complete_email_task(video_id: str, extraction_id: str, **kwargs):
    """
    Send processing complete notification.
    
    Args:
        video_id: Video ID
        extraction_id: Extraction ID
    """
    db = SessionLocal()
    
    try:
        # Get video and extraction
        video = db.query(Video).filter(Video.id == video_id).first()
        extraction = db.query(Extraction).filter(Extraction.id == extraction_id).first()
        
        if not video or not extraction:
            logger.error(
                "Video or extraction not found",
                video_id=video_id,
                extraction_id=extraction_id
            )
            return
        
        # Get user
        user = db.query(User).filter(User.id == video.user_id).first()
        
        if not user:
            logger.error("User not found", user_id=str(video.user_id))
            return
        
        # Check notification preferences
        if not user.notify_processing_complete:
            logger.info(
                "User disabled processing complete emails",
                user_id=str(user.id)
            )
            return
        
        # Get video title from extracted data
        video_title = "Your video"
        if extraction.extracted_data and "Title" in extraction.extracted_data:
            video_title = extraction.extracted_data["Title"]
        
        # Get remaining extractions
        from app.services import extraction_service
        extractions_remaining = extraction_service.get_extractions_remaining(
            video_id, db
        )
        
        # Send email
        success = email_service.send_processing_complete_email(
            user_email=user.email,
            user_name=user.full_name or "User",
            video_title=video_title,
            extracted_data=extraction.extracted_data or {},
            video_url=f"{settings.FRONTEND_URL}/videos/{video_id}",
            extractions_remaining=extractions_remaining
        )
        
        if success:
            # Create notification record
            notification = Notification(
                user_id=user.id,
                type="processing_complete",
                title="Video processed successfully",
                message=f"Your video '{video_title}' is ready",
                video_id=video.id,
                email_sent=True
            )
            notification.mark_email_sent()
            
            db.add(notification)
            db.commit()
            
            logger.info("Processing complete email sent", video_id=video_id)
        else:
            logger.error("Failed to send processing complete email", video_id=video_id)
        
    except Exception as e:
        logger.error(
            "Processing complete email task failed",
            video_id=video_id,
            error=str(e)
        )
    
    finally:
        db.close()


@task(retries=3, retry_delay=30)
def send_processing_failed_email_task(video_id: str, error_message: str, **kwargs):
    """
    Send processing failed notification.
    
    Args:
        video_id: Video ID
        error_message: Error message
    """
    db = SessionLocal()
    
    try:
        # Get video
        video = db.query(Video).filter(Video.id == video_id).first()
        
        if not video:
            logger.error("Video not found", video_id=video_id)
            return
        
        # Get user
        user = db.query(User).filter(User.id == video.user_id).first()
        
        if not user:
            logger.error("User not found", user_id=str(video.user_id))
            return
        
        # Check notification preferences
        if not user.notify_processing_failed:
            logger.info(
                "User disabled processing failed emails",
                user_id=str(user.id)
            )
            return
        
        # Send email
        success = email_service.send_processing_failed_email(
            user_email=user.email,
            user_name=user.full_name or "User",
            video_id=video_id,
            error_message=error_message
        )
        
        if success:
            # Create notification record
            notification = Notification(
                user_id=user.id,
                type="processing_failed",
                title="Video processing failed",
                message=f"Error: {error_message}",
                video_id=video.id,
                email_sent=True
            )
            notification.mark_email_sent()
            
            db.add(notification)
            db.commit()
            
            logger.info("Processing failed email sent", video_id=video_id)
        else:
            logger.error("Failed to send processing failed email", video_id=video_id)
        
    except Exception as e:
        logger.error(
            "Processing failed email task failed",
            video_id=video_id,
            error=str(e)
        )
    
    finally:
        db.close()


# ===================================
# WEEKLY SUMMARY
# ===================================

@periodic_task(crontab(day_of_week='0', hour='9', minute='0'))  # Every Sunday at 9 AM
def send_weekly_summaries(**kwargs):
    """
    Send weekly summary emails to all users who have enabled them.
    Runs every Sunday at 9 AM.
    """
    db = SessionLocal()
    
    try:
        logger.info("Starting weekly summary email batch")
        
        # Get all users with weekly summary enabled
        users = db.query(User).filter(
            User.notify_weekly_summary == True,
            User.email_verified == True,
            User.account_status == "active"
        ).all()
        
        logger.info(f"Sending weekly summaries to {len(users)} users")
        
        for user in users:
            try:
                # Queue individual summary email
                send_weekly_summary_email_task(str(user.id))
                
            except Exception as e:
                logger.error(
                    "Failed to queue weekly summary",
                    user_id=str(user.id),
                    error=str(e)
                )
        
        logger.info("Weekly summary batch completed")
        
    except Exception as e:
        logger.error("Weekly summary batch failed", error=str(e))
    
    finally:
        db.close()


@task(retries=2, retry_delay=60)
def send_weekly_summary_email_task(user_id: str, **kwargs):
    """
    Send weekly summary to individual user.
    
    Args:
        user_id: User ID
    """
    db = SessionLocal()
    
    try:
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user or not user.notify_weekly_summary:
            return
        
        # Get user's stats for the week
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # Videos uploaded this week
        videos_uploaded = db.query(Video).filter(
            Video.user_id == user_id,
            Video.created_at >= week_ago
        ).count()
        
        # Total videos
        total_videos = db.query(Video).filter(
            Video.user_id == user_id
        ).count()
        
        # Most common property type (from extracted data)
        # This is a simplified version - in production, you'd query extracted_data JSONB
        top_property_type = "2BHK"  # Placeholder
        
        stats = {
            "videos_uploaded": videos_uploaded,
            "total_videos": total_videos,
            "top_property_type": top_property_type
        }
        
        # Send email
        success = email_service.send_weekly_summary_email(
            user_email=user.email,
            user_name=user.full_name or "User",
            stats=stats
        )
        
        if success:
            logger.info("Weekly summary sent", user_id=user_id)
        else:
            logger.error("Failed to send weekly summary", user_id=user_id)
        
    except Exception as e:
        logger.error(
            "Weekly summary email task failed",
            user_id=user_id,
            error=str(e)
        )
    
    finally:
        db.close()


# ===================================
# BULK EMAIL OPERATIONS
# ===================================

@task()
def send_bulk_email_task(
    user_ids: list,
    subject: str,
    template_name: str,
    context: Dict[str, Any],
    **kwargs
):
    """
    Send bulk email to multiple users.
    
    Args:
        user_ids: List of user IDs
        subject: Email subject
        template_name: Template name
        context: Template context
    """
    db = SessionLocal()
    
    try:
        logger.info(f"Sending bulk email to {len(user_ids)} users")
        
        for user_id in user_ids:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                
                if not user or not user.email_verified:
                    continue
                
                # Personalize context
                user_context = {
                    **context,
                    "user_name": user.full_name or "User"
                }
                
                # Render and send
                html_content = email_service.render_template(
                    template_name,
                    user_context
                )
                
                email_service.send_email(
                    to_email=user.email,
                    subject=subject,
                    html_content=html_content
                )
                
            except Exception as e:
                logger.error(
                    "Failed to send bulk email to user",
                    user_id=user_id,
                    error=str(e)
                )
        
        logger.info("Bulk email completed")
        
    except Exception as e:
        logger.error("Bulk email task failed", error=str(e))
    
    finally:
        db.close()


# ===================================
# HELPER FUNCTIONS
# ===================================
