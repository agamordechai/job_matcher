"""Celery worker for background tasks"""
from celery import Celery, chord, group
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
# Fetch jobs Sunday-Thursday during specific time windows every 30 minutes
# Time windows: 9:00-11:00, 14:00-15:00, 17:30-18:00 (Israel timezone)
celery_app.conf.beat_schedule = {
    # Morning window: 9:00-11:00 (every 30 minutes: 9:00, 9:30, 10:00, 10:30, 11:00)
    "fetch-jobs-morning-window": {
        "task": "app.celery_worker.fetch_and_analyze_jobs",
        "schedule": crontab(
            minute="0,30",
            hour="10-11",
            day_of_week="0-4"  # Sunday=0 to Thursday=4
        ),
    },
    # Afternoon window: 14:00-15:00 (every 30 minutes: 14:00, 14:30, 15:00)
    "fetch-jobs-afternoon-window": {
        "task": "app.celery_worker.fetch_and_analyze_jobs",
        "schedule": crontab(
            minute="0,30",
            hour="14-15",
            day_of_week="0-4"  # Sunday=0 to Thursday=4
        ),
    },
    # Evening window: 17:30-18:00 (every 30 minutes: 17:30, 18:00)
    "fetch-jobs-evening-window": {
        "task": "app.celery_worker.fetch_and_analyze_jobs",
        "schedule": crontab(
            minute="0,30",
            hour="17-18",
            day_of_week="0-4"  # Sunday=0 to Thursday=4
        ),
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
    from app.services.jsearch_service import JSearchService
    import asyncio

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

        # Initialize services
        job_service = JobService(db)
        jsearch_service = JSearchService()

        jobs_fetched = 0
        jobs_created = 0
        jobs_duplicate = 0
        new_job_ids = []  # Track new job IDs for batch analysis

        print(f"Starting job fetch for {len(filters)} active filters...")

        # Fetch jobs for each filter
        for search_filter in filters:
            filter_dict = {
                "keywords": search_filter.keywords,
                "location": search_filter.location,
                "job_type": search_filter.job_type,
                "experience_level": search_filter.experience_level,
                "remote": search_filter.remote,
            }

            print(f"Fetching jobs for filter: {search_filter.name}")

            # Fetch jobs asynchronously
            try:
                jobs = asyncio.run(
                    jsearch_service.fetch_jobs_by_filter(
                        filter_dict,
                        max_pages=settings.search_max_pages
                    )
                )

                jobs_fetched += len(jobs)
                print(f"  Found {len(jobs)} jobs")

                # Save jobs to database
                for job_data in jobs:
                    # Check if job already exists
                    existing_job = job_service.get_job_by_external_id(
                        job_data["external_job_id"]
                    )

                    if existing_job:
                        jobs_duplicate += 1
                        continue

                    # Add CV ID to job data
                    job_data["cv_id"] = active_cv.id

                    # Create job in database
                    new_job = job_service.create_job(job_data)
                    jobs_created += 1
                    new_job_ids.append(new_job.id)

                    print(f"  Created job: {new_job.title} at {new_job.company}")

            except Exception as e:
                print(f"Error fetching jobs for filter {search_filter.name}: {str(e)}")
                continue

        print(f"Job fetch completed: {jobs_fetched} fetched, {jobs_created} new, {jobs_duplicate} duplicates")

        # Analyze all new jobs and send email when ALL analyses complete
        if new_job_ids:
            print(f"Starting batch analysis of {len(new_job_ids)} jobs...")

            # Use Celery chord: run all analyses in parallel, then trigger email when all complete
            analyze_tasks = [analyze_job.s(job_id) for job_id in new_job_ids]
            chord(analyze_tasks)(send_batch_job_notification.s())

            print(f"✅ Batch analysis queued. Email will be sent after all {len(new_job_ids)} jobs are analyzed.")

        return {
            "status": "success",
            "cv_id": active_cv.id,
            "filters_count": len(filters),
            "jobs_fetched": jobs_fetched,
            "jobs_created": jobs_created,
            "jobs_duplicate": jobs_duplicate,
        }

    except Exception as e:
        print(f"Error in fetch_and_analyze_jobs: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
        }

    finally:
        db.close()


@celery_app.task(name="app.celery_worker.analyze_job")
def analyze_job(job_id: int):
    """
    Analyze a single job against the active CV using AI.
    Uses AI API for intelligent matching, with fallback to keyword matching.
    """
    from app.database import SessionLocal
    from app.services.job_service import JobService
    from app.services.cv_service import CVService
    from app.services.ai_matching_service import AIMatchingService
    from app.models import JobScore

    db = SessionLocal()

    try:
        job_service = JobService(db)
        cv_service = CVService(db)
        ai_service = AIMatchingService()

        # Get the job
        job = job_service.get_job(job_id)
        if not job:
            print(f"Job {job_id} not found")
            return {"status": "error", "reason": "job_not_found"}

        # Get the CV
        cv = cv_service.get_cv(job.cv_id) if job.cv_id else None
        if not cv:
            print(f"CV not found for job {job_id}")
            return {"status": "error", "reason": "cv_not_found"}

        print(f"Analyzing job {job_id}: {job.title} at {job.company}")

        # Check if AI is configured
        if ai_service.is_configured():
            print(f"  Using Claude AI for analysis...")
        else:
            print(f"  Using fallback keyword matching (AI not configured)...")

        # Perform AI-powered analysis
        analysis = ai_service.analyze_job_match(
            cv_content=cv.content,
            cv_summary=cv.summary,
            job_title=job.title,
            job_company=job.company,
            job_description=job.description or "",
            job_requirements=job.requirements,
            job_location=job.location
        )

        # Map score string to enum
        score_map = {
            "high": JobScore.HIGH,
            "medium": JobScore.MEDIUM,
            "low": JobScore.LOW
        }
        score = score_map.get(analysis["score"], JobScore.MEDIUM)
        compatibility = analysis["compatibility_percentage"]
        missing_requirements = analysis["missing_requirements"]
        suggested_summary = analysis.get("suggested_summary")
        needs_summary_change = analysis.get("needs_summary_change", False)
        must_notify = analysis.get("must_notify", False)

        print(f"  Compatibility: {compatibility}% | Score: {score.value}")
        print(f"  Missing: {len(missing_requirements)} requirements")
        if analysis.get("analysis_reasoning"):
            print(f"  Reasoning: {analysis['analysis_reasoning']}")
        if must_notify:
            print(f"  🔔 Must Notify: {analysis.get('must_notify_keyword', 'yes')}")

        # Update job with analysis results
        job_service.update_job_analysis(
            job_id=job_id,
            score=score,
            compatibility_percentage=compatibility,
            missing_requirements=missing_requirements,
            suggested_summary=suggested_summary,
            needs_summary_change=needs_summary_change,
            must_notify=must_notify
        )

        return {
            "status": "success",
            "job_id": job_id,
            "score": score.value,
            "compatibility": compatibility,
            "missing_count": len(missing_requirements),
            "ai_powered": ai_service.is_configured(),
            "reasoning": analysis.get("analysis_reasoning", "")
        }

    except Exception as e:
        print(f"Error analyzing job {job_id}: {str(e)}")
        return {
            "status": "error",
            "job_id": job_id,
            "error": str(e)
        }

    finally:
        db.close()


@celery_app.task(name="app.celery_worker.send_batch_job_notification")
def send_batch_job_notification(analysis_results=None):
    """
    Send batch email notification after ALL job analyses are complete.
    This is triggered as a callback after chord completes.

    Args:
        analysis_results: List of results from analyze_job tasks (from chord)
    """
    from app.database import SessionLocal
    from app.services.email_service import EmailService
    from app.services.job_service import JobService
    from app.models import JobStatus, JobScore, Job
    from datetime import datetime

    db = SessionLocal()

    try:
        job_service = JobService(db)
        email_service = EmailService(db)

        # Get jobs that haven't been notified yet AND are analyzed
        # Include jobs that either have HIGH score OR have must_notify flag set
        jobs = db.query(Job).filter(
            Job.notified_at.is_(None),
            Job.status == JobStatus.ANALYZED,  # Only analyzed jobs
            ((Job.score == JobScore.HIGH) | (Job.must_notify == True))  # HIGH or must-notify
        ).order_by(Job.fetched_at.desc()).limit(50).all()  # Limit to 50 most recent

        if not jobs:
            print("No new HIGH/must-notify jobs to notify about")
            return {"status": "skipped", "reason": "no_qualifying_jobs"}

        print(f"📧 Sending batch notification for {len(jobs)} jobs (HIGH scores or must-notify)")

        # Send batch notification
        result = email_service.send_batch_notification(jobs)

        # Mark jobs as notified if email was sent successfully
        if result.get("status") == "success":
            for job in jobs:
                job.notified_at = datetime.utcnow()
                job.status = JobStatus.NOTIFIED
            db.commit()
            print(f"✅ Marked {len(jobs)} jobs as notified")

        return result

    except Exception as e:
        print(f"❌ Error in send_batch_job_notification: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return {
            "status": "error",
            "error": str(e)
        }

    finally:
        db.close()

