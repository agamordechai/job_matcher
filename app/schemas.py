"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from typing import Optional, List, Literal, Any
from enum import Enum

from app.models import JobScore, JobStatus


# ============================================================================
# Enums for constrained string fields
# ============================================================================

class JobTypeEnum(str, Enum):
    """Valid job type values"""
    FULL_TIME = "full-time"
    PART_TIME = "part-time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"


class ExperienceLevelEnum(str, Enum):
    """Valid experience level values"""
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"


class AnalysisScoreEnum(str, Enum):
    """Score values from AI analysis"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PrefilterReasonEnum(str, Enum):
    """Reasons for job pre-filtering"""
    EXCLUDED_KEYWORD = "excluded_keyword"
    MISSING_INCLUDE_KEYWORD = "missing_include_keyword"
    NO_REQUIREMENTS = "no_requirements"
    EXPERIENCE_MISMATCH = "experience_mismatch"
    INSUFFICIENT_SKILLS = "insufficient_skills"
    EARLY_STOP = "early_stop"


class NotificationStatusEnum(str, Enum):
    """Notification status values"""
    SUCCESS = "success"
    SKIPPED = "skipped"
    ERROR = "error"


# ============================================================================
# CV Schemas
# ============================================================================

class CVUpload(BaseModel):
    """Schema for CV upload"""
    pass  # File will be handled separately


class CVResponse(BaseModel):
    """Schema for CV response"""
    id: int
    filename: str
    content: str
    summary: Optional[str] = None
    uploaded_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CVSummaryUpdate(BaseModel):
    """Schema for updating CV summary"""
    summary: str = Field(..., min_length=10, max_length=1000)

    @field_validator('summary')
    @classmethod
    def validate_summary_content(cls, v: str) -> str:
        """Ensure summary is not just whitespace"""
        if not v.strip():
            raise ValueError("Summary cannot be empty or whitespace only")
        return v.strip()


# ============================================================================
# Search Filter Schemas
# ============================================================================

class SearchFilterCreate(BaseModel):
    """Schema for creating search filter"""
    name: str = Field(..., min_length=1, max_length=255)
    keywords: List[str] = Field(..., min_length=1, max_length=20)
    location: Optional[str] = Field(None, max_length=255)
    job_type: Optional[str] = Field(None, pattern=r'^(full-time|part-time|contract|internship)?$')
    experience_level: Optional[str] = Field(None, pattern=r'^(entry|mid|senior)?$')
    remote: bool = False

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate filter name"""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Filter name cannot be empty")
        return cleaned

    @field_validator('keywords')
    @classmethod
    def validate_keywords(cls, v: List[str]) -> List[str]:
        """Validate each keyword in the list"""
        validated = []
        for keyword in v:
            clean = keyword.strip()
            if len(clean) < 2:
                raise ValueError(f"Keyword '{keyword}' too short (min 2 chars)")
            if len(clean) > 100:
                raise ValueError(f"Keyword '{keyword}' too long (max 100 chars)")
            validated.append(clean)
        if not validated:
            raise ValueError("At least one valid keyword is required")
        return validated


class SearchFilterUpdate(BaseModel):
    """Schema for updating search filter"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    keywords: Optional[List[str]] = Field(None, min_length=1)
    location: Optional[str] = Field(None, max_length=255)
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    remote: Optional[bool] = None
    is_active: Optional[bool] = None

    @field_validator('keywords')
    @classmethod
    def validate_keywords(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate keywords if provided"""
        if v is None:
            return v
        validated = [k.strip() for k in v if k.strip()]
        if not validated:
            raise ValueError("Keywords list cannot be empty")
        return validated


class SearchFilterResponse(BaseModel):
    """Schema for search filter response"""
    id: int
    name: str
    keywords: List[str]
    location: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    remote: bool
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Job Schemas
# ============================================================================

class JobResponse(BaseModel):
    """Schema for job response"""
    id: int
    external_job_id: str
    title: str
    company: str
    location: Optional[str] = None
    job_type: Optional[str] = None
    description: str
    requirements: Optional[str] = None
    url: Optional[str] = None
    salary_range: Optional[str] = None
    score: JobScore
    compatibility_percentage: Optional[int] = Field(None, ge=0, le=100)
    missing_requirements: Optional[List[str]] = None
    suggested_summary: Optional[str] = None
    needs_summary_change: bool
    must_notify: Optional[bool] = False
    status: JobStatus
    notified_at: Optional[datetime] = None
    fetched_at: datetime
    analyzed_at: Optional[datetime] = None
    posted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    """Schema for job list response"""
    total: int = Field(..., ge=0)
    jobs: List[JobResponse]


class JobNotifiedUpdate(BaseModel):
    """Schema for marking job as notified"""
    notified: bool = True


class JobCreateRequest(BaseModel):
    """Schema for creating a job (used internally)"""
    external_job_id: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=512)
    company: str = Field(..., min_length=1, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    description: str = Field(..., min_length=10)
    requirements: Optional[str] = None
    url: Optional[str] = Field(None, max_length=1024)
    salary_range: Optional[str] = Field(None, max_length=255)
    posted_at: Optional[datetime] = None

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format"""
        if v is None:
            return v
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v


# ============================================================================
# AI Analysis Schemas
# ============================================================================

class JobAnalysisResult(BaseModel):
    """Validated job analysis result from AI service"""
    score: AnalysisScoreEnum
    compatibility_percentage: int = Field(..., ge=0, le=100)
    matching_skills: List[str] = Field(default_factory=list, max_length=15)
    missing_requirements: List[str] = Field(default_factory=list, max_length=15)
    needs_summary_change: bool = False
    suggested_summary: Optional[str] = Field(None, max_length=2000)
    analysis_reasoning: str = Field("", max_length=1000)
    prefiltered: bool = False
    prefilter_reason: Optional[str] = None
    matched_keyword: Optional[str] = None
    must_notify: bool = False
    must_notify_keyword: Optional[str] = None
    job_id: Optional[int] = None

    @field_validator('matching_skills', 'missing_requirements')
    @classmethod
    def validate_skills_list(cls, v: List[str]) -> List[str]:
        """Ensure skills are non-empty strings"""
        return [s.strip() for s in v if s and s.strip()]

    @field_validator('score', mode='before')
    @classmethod
    def normalize_score(cls, v: Any) -> str:
        """Normalize score to lowercase"""
        if isinstance(v, str):
            return v.lower()
        return v


class CVSkillsProfile(BaseModel):
    """Extracted skills profile from CV"""
    skills: List[str] = Field(default_factory=list)
    years_experience: Optional[int] = Field(None, ge=0, le=50)
    recent_roles: List[str] = Field(default_factory=list, max_length=5)
    skill_count: int = Field(0, ge=0)


class PrefilterResult(BaseModel):
    """Result of job pre-filtering"""
    should_analyze: bool
    result: Optional[JobAnalysisResult] = None
    reason: Optional[PrefilterReasonEnum] = None


# ============================================================================
# JSearch API Schemas
# ============================================================================

class JSearchJobHighlights(BaseModel):
    """Job highlights from JSearch API"""
    Qualifications: Optional[List[str]] = None
    Responsibilities: Optional[List[str]] = None
    Benefits: Optional[List[str]] = None

    model_config = ConfigDict(extra='allow')


class JSearchExperienceRequirement(BaseModel):
    """Experience requirements from JSearch"""
    required_experience_in_months: Optional[int] = None
    experience_mentioned: Optional[bool] = None
    experience_preferred: Optional[bool] = None

    model_config = ConfigDict(extra='allow')


class JSearchJobResponse(BaseModel):
    """Pydantic model for individual job from JSearch API"""
    job_id: str
    job_title: str
    employer_name: Optional[str] = "Unknown Company"
    job_city: Optional[str] = None
    job_state: Optional[str] = None
    job_country: Optional[str] = None
    job_description: str = ""
    job_employment_type: Optional[str] = None
    job_highlights: Optional[JSearchJobHighlights] = None
    job_required_experience: Optional[JSearchExperienceRequirement] = None
    job_apply_link: Optional[str] = None
    job_google_link: Optional[str] = None
    job_min_salary: Optional[float] = None
    job_max_salary: Optional[float] = None
    job_salary_currency: Optional[str] = "USD"
    job_salary_period: Optional[str] = "YEAR"
    job_posted_at_timestamp: Optional[int] = None
    job_posted_at_datetime_utc: Optional[str] = None

    model_config = ConfigDict(extra='allow')


class JSearchAPIResponse(BaseModel):
    """Full response from JSearch API"""
    status: str
    request_id: Optional[str] = None
    data: List[JSearchJobResponse] = Field(default_factory=list)

    model_config = ConfigDict(extra='allow')


class ParsedJobData(BaseModel):
    """Validated parsed job data ready for database insertion"""
    external_job_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=512)
    company: str = Field(..., min_length=1, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    description: str = Field(..., min_length=1)
    requirements: Optional[str] = None
    url: Optional[str] = Field(None, max_length=1024)
    salary_range: Optional[str] = Field(None, max_length=255)
    posted_at: Optional[datetime] = None
    fetched_at: datetime

    @field_validator('title', 'company')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip whitespace from string fields"""
        return v.strip() if v else v


# ============================================================================
# Notification Schemas
# ============================================================================

class NotificationRequest(BaseModel):
    """Request to trigger notifications"""
    job_ids: Optional[List[int]] = Field(None, min_length=1)
    force: bool = False


class NotificationResponse(BaseModel):
    """Response from notification send"""
    status: NotificationStatusEnum
    jobs_count: Optional[int] = Field(None, ge=0)
    recipient: Optional[str] = None
    reason: Optional[str] = None
    error: Optional[str] = None


class NotificationHistoryItem(BaseModel):
    """Individual notification history entry"""
    id: int
    job_id: Optional[int] = None
    recipient_email: str
    subject: str
    sent_at: datetime
    success: bool
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationHistoryResponse(BaseModel):
    """Response for notification history"""
    total: int = Field(..., ge=0)
    notifications: List[NotificationHistoryItem]


# ============================================================================
# Scheduler Schemas
# ============================================================================

class SchedulerTriggerResponse(BaseModel):
    """Schema for scheduler trigger response"""
    message: str
    task_id: str


class SchedulerStatusResponse(BaseModel):
    """Schema for scheduler status response"""
    is_running: bool
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    interval_minutes: int = Field(..., ge=1)


class SchedulerConfigUpdate(BaseModel):
    """Schema for scheduler config update"""
    interval_minutes: int = Field(..., ge=10, le=1440)

    @field_validator('interval_minutes')
    @classmethod
    def validate_interval(cls, v: int) -> int:
        """Validate interval is a reasonable value"""
        if v < 10:
            raise ValueError("Interval must be at least 10 minutes")
        if v > 1440:
            raise ValueError("Interval cannot exceed 24 hours (1440 minutes)")
        return v


# ============================================================================
# System Schemas
# ============================================================================

class HealthResponse(BaseModel):
    """Schema for health check response"""
    status: Literal["healthy", "unhealthy"]
    database: str
    redis: str
    timestamp: datetime


class AIStatusResponse(BaseModel):
    """Schema for AI service status"""
    ai_configured: bool
    model: Optional[str] = None
    capabilities: dict = Field(default_factory=dict)
    fallback_available: bool = True
    fallback_method: str = "keyword_matching"


class FilterConfigResponse(BaseModel):
    """Schema for filter configuration"""
    prefilter_enabled: bool
    exclude_keywords: List[str] = Field(default_factory=list)
    include_keywords: List[str] = Field(default_factory=list)
    must_notify_keywords: List[str] = Field(default_factory=list)
    exclude_count: int = Field(0, ge=0)
    include_count: int = Field(0, ge=0)
    must_notify_count: int = Field(0, ge=0)
