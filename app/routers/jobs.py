"""Job management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.database import get_db
from app.schemas import JobResponse, JobListResponse, JobNotifiedUpdate
from app.models import JobScore, JobStatus, Job
from app.services.job_service import JobService
from app.services.cv_service import CVService
from app.services.ai_matching_service import AIMatchingService

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


@router.post("/{job_id}/analyze", response_model=Dict[str, Any])
async def analyze_job(
    job_id: int,
    force: bool = Query(False, description="Force re-analysis even if already analyzed"),
    db: Session = Depends(get_db)
):
    """
    Analyze a job against the active CV using AI.

    Uses Claude AI for intelligent matching with fallback to keyword matching.
    Set force=true to re-analyze a previously analyzed job.
    """
    job_service = JobService(db)
    cv_service = CVService(db)
    ai_service = AIMatchingService()

    # Get the job
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Check if already analyzed
    if job.analyzed_at and not force:
        return {
            "status": "skipped",
            "reason": "already_analyzed",
            "job_id": job_id,
            "analyzed_at": job.analyzed_at.isoformat(),
            "score": job.score.value if job.score else None,
            "compatibility": job.compatibility_percentage,
            "hint": "Use ?force=true to re-analyze"
        }

    # Get active CV
    cv = cv_service.get_active_cv()
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active CV found. Please upload a CV first."
        )

    # Perform AI analysis
    analysis = ai_service.analyze_job_match(
        cv_content=cv.content,
        cv_summary=cv.summary,
        job_title=job.title,
        job_company=job.company,
        job_description=job.description or "",
        job_requirements=job.requirements,
        job_location=job.location
    )

    # Map score
    score_map = {
        "high": JobScore.HIGH,
        "medium": JobScore.MEDIUM,
        "low": JobScore.LOW
    }
    score = score_map.get(analysis.score, JobScore.MEDIUM)

    # Update job
    job_service.update_job_analysis(
        job_id=job_id,
        score=score,
        compatibility_percentage=analysis.compatibility_percentage,
        missing_requirements=analysis.missing_requirements,
        suggested_summary=analysis.suggested_summary,
        needs_summary_change=analysis.needs_summary_change,
        must_notify=analysis.must_notify
    )

    return {
        "status": "success",
        "job_id": job_id,
        "ai_powered": ai_service.is_configured(),
        "score": analysis.score,
        "compatibility_percentage": analysis.compatibility_percentage,
        "matching_skills": analysis.matching_skills,
        "missing_requirements": analysis.missing_requirements,
        "needs_summary_change": analysis.needs_summary_change,
        "suggested_summary": analysis.suggested_summary,
        "analysis_reasoning": analysis.analysis_reasoning
    }


@router.post("/analyze/batch", response_model=Dict[str, Any])
async def analyze_jobs_batch(
    job_ids: List[int] = Query(None, description="Specific job IDs to analyze"),
    pending_only: bool = Query(True, description="Only analyze pending jobs"),
    limit: int = Query(10, ge=1, le=50, description="Max jobs to analyze"),
    db: Session = Depends(get_db)
):
    """
    Batch analyze multiple jobs against the active CV.

    If job_ids provided, analyzes those specific jobs.
    Otherwise, analyzes pending jobs up to the limit.
    """
    job_service = JobService(db)
    cv_service = CVService(db)
    ai_service = AIMatchingService()

    # Get active CV
    cv = cv_service.get_active_cv()
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active CV found. Please upload a CV first."
        )

    # Get jobs to analyze
    if job_ids:
        jobs = [job_service.get_job(jid) for jid in job_ids]
        jobs = [j for j in jobs if j is not None]
    else:
        # Get pending jobs
        query = db.query(Job)
        if pending_only:
            query = query.filter(Job.score == JobScore.PENDING)
        jobs = query.order_by(Job.fetched_at.desc()).limit(limit).all()

    if not jobs:
        return {
            "status": "skipped",
            "reason": "no_jobs_to_analyze",
            "analyzed_count": 0
        }

    # Analyze each job
    results = []
    for job in jobs:
        try:
            analysis = ai_service.analyze_job_match(
                cv_content=cv.content,
                cv_summary=cv.summary,
                job_title=job.title,
                job_company=job.company,
                job_description=job.description or "",
                job_requirements=job.requirements,
                job_location=job.location
            )

            score_map = {"high": JobScore.HIGH, "medium": JobScore.MEDIUM, "low": JobScore.LOW}
            score = score_map.get(analysis.score, JobScore.MEDIUM)

            job_service.update_job_analysis(
                job_id=job.id,
                score=score,
                compatibility_percentage=analysis.compatibility_percentage,
                missing_requirements=analysis.missing_requirements,
                suggested_summary=analysis.suggested_summary,
                needs_summary_change=analysis.needs_summary_change,
                must_notify=analysis.must_notify
            )

            results.append({
                "job_id": job.id,
                "title": job.title,
                "company": job.company,
                "status": "success",
                "score": analysis.score,
                "compatibility": analysis.compatibility_percentage
            })
        except Exception as e:
            results.append({
                "job_id": job.id,
                "title": job.title,
                "status": "error",
                "error": str(e)
            })

    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "error"]

    return {
        "status": "completed",
        "ai_powered": ai_service.is_configured(),
        "total_jobs": len(jobs),
        "analyzed_count": len(successful),
        "failed_count": len(failed),
        "results": results
    }


@router.get("/ai/status", response_model=Dict[str, Any])
async def get_ai_status():
    """
    Check if AI matching is properly configured.

    Returns configuration status and capabilities.
    """
    ai_service = AIMatchingService()

    return {
        "ai_configured": ai_service.is_configured(),
        "model": ai_service.model if ai_service.is_configured() else None,
        "capabilities": {
            "job_matching": True,
            "compatibility_scoring": True,
            "missing_requirements_detection": True,
            "summary_generation": ai_service.is_configured(),
            "analysis_reasoning": ai_service.is_configured()
        },
        "fallback_available": True,
        "fallback_method": "keyword_matching"
    }


