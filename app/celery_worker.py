"""Celery worker for background tasks"""
from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "job_matcher",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.timezone,
    enable_utc=True,
)

# Configure periodic tasks
celery_app.conf.beat_schedule = {
    "fetch-jobs-every-hour": {
        "task": "app.celery_worker.fetch_and_analyze_jobs",
        "schedule": crontab(minute=0),  # Run every hour at minute 0
    },
}


@celery_app.task(name="app.celery_worker.fetch_and_analyze_jobs")
def fetch_and_analyze_jobs():
    """
    Main task to fetch jobs and analyze them against CV
    This runs periodically based on the schedule
    """
    from app.database import SessionLocal
    from app.services.cv_service import CVService
    from app.services.filter_service import FilterService
    from app.services.job_service import JobService

    db = SessionLocal()

    try:
        # Get active CV
        cv_service = CVService(db)
        active_cv = cv_service.get_active_cv()

        if not active_cv:
            print("No active CV found. Skipping job fetch.")
            return {"status": "skipped", "reason": "no_active_cv"}

        # Get active filters
        filter_service = FilterService(db)
        filters = filter_service.get_all_filters(active_only=True)

        if not filters:
            print("No active search filters found. Skipping job fetch.")
            return {"status": "skipped", "reason": "no_active_filters"}

        # TODO: Implement job fetching logic
        # For now, return a placeholder
        print(f"Would fetch jobs for {len(filters)} filters")

        return {
            "status": "success",
            "cv_id": active_cv.id,
            "filters_count": len(filters),
            "jobs_fetched": 0,
            "jobs_analyzed": 0,
        }

    finally:
        db.close()


@celery_app.task(name="app.celery_worker.analyze_job")
def analyze_job(job_id: int):
    """
    Analyze a single job against the active CV
    """
    from app.database import SessionLocal

    db = SessionLocal()

    try:
        # TODO: Implement job analysis logic using AI
        print(f"Analyzing job {job_id}")
        return {"status": "success", "job_id": job_id}

    finally:
        db.close()


@celery_app.task(name="app.celery_worker.send_job_notification")
def send_job_notification(job_id: int):
    """
    Send email notification for a matched job
    """
    from app.database import SessionLocal

    db = SessionLocal()

    try:
        # TODO: Implement email notification logic
        print(f"Sending notification for job {job_id}")
        return {"status": "success", "job_id": job_id}

    finally:
        db.close()

