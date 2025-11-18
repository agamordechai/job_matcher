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
# Fetch jobs Sunday-Thursday during specific time windows every 30 minutes
# Time windows: 9:00-11:00, 14:00-15:00, 17:30-18:00 (Israel timezone)
celery_app.conf.beat_schedule = {
    # Morning window: 9:00-11:00 (every 30 minutes: 9:00, 9:30, 10:00, 10:30, 11:00)
    "fetch-jobs-morning-window": {
        "task": "app.celery_worker.fetch_and_analyze_jobs",
        "schedule": crontab(
            minute="0,30",
            hour="9-11",
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

                    print(f"  Created job: {new_job.title} at {new_job.company}")

                    # Trigger async analysis of this job against CV
                    analyze_job.delay(new_job.id)

            except Exception as e:
                print(f"Error fetching jobs for filter {search_filter.name}: {str(e)}")
                continue

        print(f"Job fetch completed: {jobs_fetched} fetched, {jobs_created} new, {jobs_duplicate} duplicates")

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
    Analyze a single job against the active CV
    Compares job requirements with CV content and calculates compatibility
    """
    from app.database import SessionLocal
    from app.services.job_service import JobService
    from app.services.cv_service import CVService
    from app.models import JobScore
    import re

    db = SessionLocal()

    try:
        job_service = JobService(db)
        cv_service = CVService(db)

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

        # Combine job text for analysis
        job_text = f"{job.title} {job.description or ''} {job.requirements or ''}".lower()
        cv_text = cv.content.lower()

        # Extract keywords from job (simple implementation)
        # TODO: Replace with AI-based analysis using Anthropic API
        job_keywords = set(re.findall(r'\b[a-z]{3,}\b', job_text))
        cv_keywords = set(re.findall(r'\b[a-z]{3,}\b', cv_text))

        # Common tech skills and keywords to look for
        important_keywords = {
            'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
            'node', 'django', 'flask', 'fastapi', 'spring', 'docker', 'kubernetes',
            'aws', 'azure', 'gcp', 'sql', 'postgresql', 'mongodb', 'redis',
            'git', 'cicd', 'devops', 'machine', 'learning', 'data', 'engineer',
            'backend', 'frontend', 'fullstack', 'api', 'rest', 'graphql',
            'agile', 'scrum', 'testing', 'security', 'cloud', 'microservices'
        }

        # Find matching keywords
        job_important = job_keywords & important_keywords
        cv_important = cv_keywords & important_keywords
        matching_keywords = job_important & cv_important
        missing_keywords = job_important - cv_important

        # Calculate compatibility percentage
        if len(job_important) > 0:
            compatibility = int((len(matching_keywords) / len(job_important)) * 100)
        else:
            compatibility = 50  # Default if no important keywords found

        # Determine score based on compatibility
        if compatibility >= 70:
            score = JobScore.HIGH
        elif compatibility >= 40:
            score = JobScore.MEDIUM
        else:
            score = JobScore.LOW

        # Format missing requirements
        missing_requirements = list(missing_keywords)[:10]  # Limit to top 10

        print(f"  Compatibility: {compatibility}% | Score: {score.value} | Missing: {len(missing_requirements)}")

        # Update job with analysis results
        job_service.update_job_analysis(
            job_id=job_id,
            score=score,
            compatibility_percentage=compatibility,
            missing_requirements=missing_requirements,
            suggested_summary=None,  # TODO: Implement with AI
            needs_summary_change=len(missing_requirements) > 0
        )

        return {
            "status": "success",
            "job_id": job_id,
            "score": score.value,
            "compatibility": compatibility,
            "missing_count": len(missing_requirements)
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

