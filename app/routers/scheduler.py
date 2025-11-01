"""Scheduler control endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import SchedulerTriggerResponse, SchedulerStatusResponse, SchedulerConfigUpdate
from app.services.scheduler_service import SchedulerService

router = APIRouter()


@router.post("/trigger", response_model=SchedulerTriggerResponse)
async def trigger_job_fetch(db: Session = Depends(get_db)):
    """Manually trigger job fetch and analysis"""
    scheduler_service = SchedulerService(db)
    task_id = scheduler_service.trigger_job_fetch()
    return SchedulerTriggerResponse(
        message="Job fetch and analysis triggered successfully",
        task_id=task_id
    )


@router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status(db: Session = Depends(get_db)):
    """Get scheduler status"""
    scheduler_service = SchedulerService(db)
    return scheduler_service.get_status()


@router.put("/config", response_model=dict)
async def update_scheduler_config(
    config: SchedulerConfigUpdate,
    db: Session = Depends(get_db)
):
    """Update scheduler configuration"""
    scheduler_service = SchedulerService(db)
    scheduler_service.update_interval(config.interval_minutes)
    return {
        "message": "Scheduler configuration updated successfully",
        "interval_minutes": config.interval_minutes
    }

