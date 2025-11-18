"""Job management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.database import get_db
from app.schemas import JobResponse, JobListResponse, JobNotifiedUpdate
from app.models import JobScore, JobStatus, Job
from app.services.job_service import JobService

router = APIRouter()


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    score: Optional[JobScore] = Query(None, description="Filter by match score"),
    status_filter: Optional[JobStatus] = Query(None, alias="status", description="Filter by status"),
    notified: Optional[bool] = Query(None, description="Filter by notification status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List all jobs with optional filters"""
    job_service = JobService(db)
    jobs, total = job_service.list_jobs(
        score=score,
        status=status_filter,
        notified=notified,
        limit=limit,
        offset=offset
    )
    return JobListResponse(total=total, jobs=jobs)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get specific job details"""
    job_service = JobService(db)
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return job


@router.put("/{job_id}/notified", response_model=JobResponse)
async def mark_job_notified(
    job_id: int,
    update: JobNotifiedUpdate,
    db: Session = Depends(get_db)
):
    """Mark job as seen/notified"""
    job_service = JobService(db)
    job = job_service.mark_as_notified(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: int, db: Session = Depends(get_db)):
    """Delete a job (archive)"""
    job_service = JobService(db)
    success = job_service.delete_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return None


@router.get("/stats/summary", response_model=Dict[str, Any])
async def get_job_statistics(db: Session = Depends(get_db)):
    """
    Get job statistics summary

    Returns counts by score, status, and other metrics
    """
    job_service = JobService(db)

    # Get all jobs
    all_jobs, total = job_service.list_jobs(limit=10000, offset=0)

    # Calculate statistics
    stats = {
        "total_jobs": total,
        "by_score": {
            "high": len([j for j in all_jobs if j.score == JobScore.HIGH]),
            "medium": len([j for j in all_jobs if j.score == JobScore.MEDIUM]),
            "low": len([j for j in all_jobs if j.score == JobScore.LOW]),
            "pending": len([j for j in all_jobs if j.score == JobScore.PENDING]),
        },
        "by_status": {
            "pending": len([j for j in all_jobs if j.status == JobStatus.PENDING]),
            "analyzed": len([j for j in all_jobs if j.status == JobStatus.ANALYZED]),
            "notified": len([j for j in all_jobs if j.status == JobStatus.NOTIFIED]),
            "archived": len([j for j in all_jobs if j.status == JobStatus.ARCHIVED]),
        },
        "analyzed_count": len([j for j in all_jobs if j.analyzed_at is not None]),
        "notified_count": len([j for j in all_jobs if j.notified_at is not None]),
        "avg_compatibility": sum([j.compatibility_percentage for j in all_jobs if j.compatibility_percentage]) / len([j for j in all_jobs if j.compatibility_percentage]) if any(j.compatibility_percentage for j in all_jobs) else 0,
    }

    return stats


@router.get("/recent/fetched", response_model=JobListResponse)
async def get_recent_fetched_jobs(
    hours: int = Query(24, ge=1, le=168, description="Jobs fetched in the last N hours"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get recently fetched jobs

    Returns jobs fetched within the specified time period (default: last 24 hours)
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    jobs = db.query(Job).filter(
        Job.fetched_at >= cutoff_time
    ).order_by(
        Job.fetched_at.desc()
    ).limit(limit).all()

    total = db.query(Job).filter(Job.fetched_at >= cutoff_time).count()

    return JobListResponse(total=total, jobs=jobs)


@router.get("/top/matches", response_model=JobListResponse)
async def get_top_matches(
    limit: int = Query(20, ge=1, le=100, description="Number of top matches to return"),
    min_compatibility: int = Query(70, ge=0, le=100, description="Minimum compatibility percentage"),
    db: Session = Depends(get_db)
):
    """
    Get top job matches based on compatibility score

    Returns high-scoring jobs sorted by compatibility percentage
    """
    jobs = db.query(Job).filter(
        Job.score == JobScore.HIGH,
        Job.compatibility_percentage >= min_compatibility
    ).order_by(
        Job.compatibility_percentage.desc(),
        Job.fetched_at.desc()
    ).limit(limit).all()

    total = db.query(Job).filter(
        Job.score == JobScore.HIGH,
        Job.compatibility_percentage >= min_compatibility
    ).count()

    return JobListResponse(total=total, jobs=jobs)


