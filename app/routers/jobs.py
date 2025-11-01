"""Job management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.schemas import JobResponse, JobListResponse, JobNotifiedUpdate
from app.models import JobScore, JobStatus
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

