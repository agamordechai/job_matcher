"""Notification management endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import NotificationLog

router = APIRouter()


@router.post("/trigger", tags=["notifications"])
def trigger_batch_notification(db: Session = Depends(get_db)):
    """
    Manually trigger batch email notification for new jobs

    Sends email with list of all jobs that haven't been notified yet
    """
    from app.celery_worker import send_batch_job_notification

    # Trigger the celery task
    task = send_batch_job_notification.delay()

    return {
        "message": "Batch notification triggered",
        "task_id": task.id,
        "status": "processing"
    }


@router.get("/history", tags=["notifications"])
def get_notification_history(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get notification history

    Args:
        limit: Maximum number of notifications to return (default: 20)
    """
    notifications = db.query(NotificationLog)\
        .order_by(NotificationLog.sent_at.desc())\
        .limit(limit)\
        .all()

    return {
        "total": len(notifications),
        "notifications": [
            {
                "id": notif.id,
                "job_id": notif.job_id,
                "recipient": notif.recipient_email,
                "subject": notif.subject,
                "sent_at": notif.sent_at,
                "success": notif.success,
                "error_message": notif.error_message
            }
            for notif in notifications
        ]
    }


@router.get("/status", tags=["notifications"])
def get_notification_status(db: Session = Depends(get_db)):
    """
    Get notification system status

    Shows whether email is configured and recent activity
    """
    from app.config import get_settings

    settings = get_settings()

    # Check if email is configured
    is_configured = bool(
        settings.smtp_user and
        settings.smtp_pass and
        settings.notification_email
    )

    # Get recent notification stats
    total_notifications = db.query(NotificationLog).count()
    successful_notifications = db.query(NotificationLog)\
        .filter(NotificationLog.success == True)\
        .count()

    # Get last notification
    last_notification = db.query(NotificationLog)\
        .order_by(NotificationLog.sent_at.desc())\
        .first()

    return {
        "email_configured": is_configured,
        "smtp_host": settings.smtp_host if is_configured else None,
        "smtp_port": settings.smtp_port if is_configured else None,
        "notification_email": settings.notification_email if is_configured else None,
        "statistics": {
            "total_sent": total_notifications,
            "successful": successful_notifications,
            "failed": total_notifications - successful_notifications,
            "last_sent_at": last_notification.sent_at if last_notification else None,
            "last_status": "success" if (last_notification and last_notification.success) else "failed"
        }
    }

