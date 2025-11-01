"""Scheduler control service"""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.schemas import SchedulerStatusResponse
from app.celery_worker import fetch_and_analyze_jobs


class SchedulerService:
    """Service for scheduler control"""

    def __init__(self, db: Session):
        self.db = db

    def trigger_job_fetch(self) -> str:
        """Manually trigger job fetch and analysis"""
        # Queue the task using Celery
        task = fetch_and_analyze_jobs.delay()
        return task.id

    def get_status(self) -> SchedulerStatusResponse:
        """Get scheduler status"""
        # TODO: Implement actual status tracking
        # For now, return a basic response
        return SchedulerStatusResponse(
            is_running=True,
            last_run=None,
            next_run=None,
            interval_minutes=60
        )

    def update_interval(self, interval_minutes: int) -> None:
        """Update scheduler interval"""
        # TODO: Implement dynamic interval update
        # This would require updating Celery Beat schedule
        pass

