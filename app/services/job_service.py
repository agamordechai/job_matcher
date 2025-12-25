"""Job management service"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, Tuple, List
from datetime import datetime
from app.models import Job, JobScore, JobStatus


class JobService:
    """Service for job management operations"""

    def __init__(self, db: Session):
        self.db = db

    def list_jobs(
        self,
        score: Optional[JobScore] = None,
        status: Optional[JobStatus] = None,
        notified: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Job], int]:
        """List jobs with filters"""
        query = self.db.query(Job)

        # Apply filters
        if score:
            query = query.filter(Job.score == score)
        if status:
            query = query.filter(Job.status == status)
        if notified is not None:
            if notified:
                query = query.filter(Job.notified_at.isnot(None))
            else:
                query = query.filter(Job.notified_at.is_(None))

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        jobs = query.order_by(Job.fetched_at.desc()).limit(limit).offset(offset).all()

        return jobs, total

    def get_job(self, job_id: int) -> Optional[Job]:
        """Get specific job by ID"""
        return self.db.query(Job).filter(Job.id == job_id).first()

    def get_job_by_external_id(self, external_id: str) -> Optional[Job]:
        """Get job by external job ID"""
        return self.db.query(Job).filter(Job.external_job_id == external_id).first()

    def mark_as_notified(self, job_id: int) -> Optional[Job]:
        """Mark job as notified"""
        job = self.get_job(job_id)
        if job:
            job.notified_at = datetime.utcnow()
            job.status = JobStatus.NOTIFIED
            self.db.commit()
            self.db.refresh(job)
        return job

    def delete_job(self, job_id: int) -> bool:
        """Archive a job"""
        job = self.get_job(job_id)
        if job:
            job.status = JobStatus.ARCHIVED
            self.db.commit()
            return True
        return False

    def create_job(self, job_data: dict) -> Job:
        """Create a new job"""
        job = Job(**job_data)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def update_job_analysis(
        self,
        job_id: int,
        score: JobScore,
        compatibility_percentage: int,
        missing_requirements: List[str],
        suggested_summary: Optional[str],
        needs_summary_change: bool,
        must_notify: bool = False
    ) -> Optional[Job]:
        """Update job with analysis results"""
        job = self.get_job(job_id)
        if job:
            job.score = score
            job.compatibility_percentage = compatibility_percentage
            job.missing_requirements = missing_requirements
            job.suggested_summary = suggested_summary
            job.needs_summary_change = needs_summary_change
            job.must_notify = must_notify
            job.status = JobStatus.ANALYZED
            job.analyzed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(job)
        return job

