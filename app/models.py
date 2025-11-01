"""Database models"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.database import Base


class JobScore(str, enum.Enum):
    """Job matching score levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    PENDING = "pending"


class JobStatus(str, enum.Enum):
    """Job processing status"""
    PENDING = "pending"
    ANALYZED = "analyzed"
    NOTIFIED = "notified"
    ARCHIVED = "archived"


class CV(Base):
    """CV/Resume storage"""
    __tablename__ = "cvs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    content = Column(Text, nullable=False)  # Parsed text content
    summary = Column(Text, nullable=True)  # Current optimized summary
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    jobs = relationship("Job", back_populates="cv")


class SearchFilter(Base):
    """Job search filters configuration"""
    __tablename__ = "search_filters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    keywords = Column(JSON, nullable=False)  # List of keywords
    location = Column(String(255), nullable=True)
    job_type = Column(String(100), nullable=True)  # full-time, part-time, contract, etc.
    experience_level = Column(String(100), nullable=True)  # entry, mid, senior
    remote = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Job(Base):
    """Job postings storage"""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    cv_id = Column(Integer, ForeignKey("cvs.id"), nullable=True)

    # Job details
    external_job_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(512), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    job_type = Column(String(100), nullable=True)
    experience_level = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    url = Column(String(1024), nullable=True)
    salary_range = Column(String(255), nullable=True)

    # Matching results
    score = Column(Enum(JobScore), default=JobScore.PENDING)
    compatibility_percentage = Column(Integer, nullable=True)
    missing_requirements = Column(JSON, nullable=True)  # List of missing skills/requirements
    suggested_summary = Column(Text, nullable=True)
    needs_summary_change = Column(Boolean, default=False)

    # Status tracking
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, index=True)
    notified_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    analyzed_at = Column(DateTime(timezone=True), nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    cv = relationship("CV", back_populates="jobs")


class SchedulerConfig(Base):
    """Scheduler configuration"""
    __tablename__ = "scheduler_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class NotificationLog(Base):
    """Email notification history"""
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(512), nullable=False)
    body = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

