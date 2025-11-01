"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from app.models import JobScore, JobStatus


# CV Schemas
class CVUpload(BaseModel):
    """Schema for CV upload"""
    pass  # File will be handled separately


class CVResponse(BaseModel):
    """Schema for CV response"""
    id: int
    filename: str
    content: str
    summary: Optional[str]
    uploaded_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class CVSummaryUpdate(BaseModel):
    """Schema for updating CV summary"""
    summary: str = Field(..., min_length=10, max_length=1000)


# Search Filter Schemas
class SearchFilterCreate(BaseModel):
    """Schema for creating search filter"""
    name: str = Field(..., min_length=1, max_length=255)
    keywords: List[str] = Field(..., min_items=1)
    location: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    remote: bool = False


class SearchFilterUpdate(BaseModel):
    """Schema for updating search filter"""
    name: Optional[str] = None
    keywords: Optional[List[str]] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    remote: Optional[bool] = None
    is_active: Optional[bool] = None


class SearchFilterResponse(BaseModel):
    """Schema for search filter response"""
    id: int
    name: str
    keywords: List[str]
    location: Optional[str]
    job_type: Optional[str]
    experience_level: Optional[str]
    remote: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Job Schemas
class JobResponse(BaseModel):
    """Schema for job response"""
    id: int
    external_job_id: str
    title: str
    company: str
    location: Optional[str]
    job_type: Optional[str]
    description: str
    requirements: Optional[str]
    url: Optional[str]
    salary_range: Optional[str]
    score: JobScore
    compatibility_percentage: Optional[int]
    missing_requirements: Optional[List[str]]
    suggested_summary: Optional[str]
    needs_summary_change: bool
    status: JobStatus
    notified_at: Optional[datetime]
    fetched_at: datetime
    analyzed_at: Optional[datetime]
    posted_at: Optional[datetime]

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Schema for job list response"""
    total: int
    jobs: List[JobResponse]


class JobNotifiedUpdate(BaseModel):
    """Schema for marking job as notified"""
    notified: bool = True


# Scheduler Schemas
class SchedulerTriggerResponse(BaseModel):
    """Schema for scheduler trigger response"""
    message: str
    task_id: str


class SchedulerStatusResponse(BaseModel):
    """Schema for scheduler status response"""
    is_running: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    interval_minutes: int


class SchedulerConfigUpdate(BaseModel):
    """Schema for scheduler config update"""
    interval_minutes: int = Field(..., ge=10, le=1440)  # Between 10 minutes and 24 hours


# System Schemas
class HealthResponse(BaseModel):
    """Schema for health check response"""
    status: str
    database: str
    redis: str
    timestamp: datetime

