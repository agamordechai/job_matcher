"""Unit tests for Pydantic Schemas"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas import (
    CVResponse,
    CVSummaryUpdate,
    SearchFilterCreate,
    SearchFilterUpdate,
    SearchFilterResponse,
    JobResponse,
    JobListResponse,
    JobNotifiedUpdate,
    SchedulerTriggerResponse,
    SchedulerStatusResponse,
    SchedulerConfigUpdate,
    HealthResponse,
)
from app.models import JobScore, JobStatus


class TestCVSchemas:
    """Tests for CV-related schemas"""

    def test_cv_response_valid(self):
        """Test valid CV response schema"""
        data = {
            "id": 1,
            "filename": "test.pdf",
            "content": "CV content here",
            "summary": "Professional summary",
            "uploaded_at": datetime.now(),
            "is_active": True
        }
        response = CVResponse(**data)
        assert response.id == 1
        assert response.filename == "test.pdf"

    def test_cv_response_without_summary(self):
        """Test CV response with optional summary as None"""
        data = {
            "id": 1,
            "filename": "test.pdf",
            "content": "CV content here",
            "summary": None,
            "uploaded_at": datetime.now(),
            "is_active": True
        }
        response = CVResponse(**data)
        assert response.summary is None

    def test_cv_summary_update_valid(self):
        """Test valid CV summary update"""
        data = {"summary": "This is a valid summary with enough characters."}
        update = CVSummaryUpdate(**data)
        assert update.summary == data["summary"]

    def test_cv_summary_update_too_short(self):
        """Test CV summary update with too short summary"""
        with pytest.raises(ValidationError) as exc_info:
            CVSummaryUpdate(summary="Short")
        assert "String should have at least 10 characters" in str(exc_info.value)

    def test_cv_summary_update_too_long(self):
        """Test CV summary update with too long summary"""
        with pytest.raises(ValidationError) as exc_info:
            CVSummaryUpdate(summary="x" * 1001)
        assert "String should have at most 1000 characters" in str(exc_info.value)


class TestSearchFilterSchemas:
    """Tests for SearchFilter-related schemas"""

    def test_search_filter_create_valid(self):
        """Test valid search filter creation"""
        data = {
            "name": "Test Filter",
            "keywords": ["Python", "Developer"],
            "location": "New York",
            "job_type": "full-time",
            "experience_level": "mid",
            "remote": True
        }
        filter_create = SearchFilterCreate(**data)
        assert filter_create.name == "Test Filter"
        assert len(filter_create.keywords) == 2

    def test_search_filter_create_minimal(self):
        """Test minimal search filter creation"""
        data = {
            "name": "Minimal",
            "keywords": ["Developer"]
        }
        filter_create = SearchFilterCreate(**data)
        assert filter_create.name == "Minimal"
        assert filter_create.location is None
        assert filter_create.remote is False

    def test_search_filter_create_empty_name(self):
        """Test search filter with empty name fails"""
        with pytest.raises(ValidationError) as exc_info:
            SearchFilterCreate(name="", keywords=["Test"])
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_search_filter_create_empty_keywords(self):
        """Test search filter with empty keywords fails"""
        with pytest.raises(ValidationError) as exc_info:
            SearchFilterCreate(name="Test", keywords=[])
        assert "List should have at least 1 item" in str(exc_info.value)

    def test_search_filter_create_name_too_long(self):
        """Test search filter with name too long fails"""
        with pytest.raises(ValidationError) as exc_info:
            SearchFilterCreate(name="x" * 256, keywords=["Test"])
        assert "String should have at most 255 characters" in str(exc_info.value)

    def test_search_filter_update_partial(self):
        """Test partial search filter update"""
        data = {"name": "Updated Name"}
        update = SearchFilterUpdate(**data)
        assert update.name == "Updated Name"
        assert update.keywords is None
        assert update.location is None

    def test_search_filter_update_all_fields(self):
        """Test full search filter update"""
        data = {
            "name": "New Name",
            "keywords": ["New", "Keywords"],
            "location": "San Francisco",
            "job_type": "contract",
            "experience_level": "senior",
            "remote": False,
            "is_active": False
        }
        update = SearchFilterUpdate(**data)
        assert update.is_active is False

    def test_search_filter_response_valid(self):
        """Test valid search filter response"""
        data = {
            "id": 1,
            "name": "Test Filter",
            "keywords": ["Python"],
            "location": "NYC",
            "job_type": "full-time",
            "experience_level": "mid",
            "remote": True,
            "is_active": True,
            "created_at": datetime.now()
        }
        response = SearchFilterResponse(**data)
        assert response.id == 1


class TestJobSchemas:
    """Tests for Job-related schemas"""

    def test_job_response_valid(self):
        """Test valid job response"""
        data = {
            "id": 1,
            "external_job_id": "job_123",
            "title": "Software Engineer",
            "company": "Tech Corp",
            "location": "Remote",
            "job_type": "full-time",
            "description": "Job description",
            "requirements": "Requirements",
            "url": "https://example.com/job",
            "salary_range": "100k-150k",
            "score": JobScore.HIGH,
            "compatibility_percentage": 85,
            "missing_requirements": ["skill1"],
            "suggested_summary": "Summary",
            "needs_summary_change": True,
            "status": JobStatus.ANALYZED,
            "notified_at": None,
            "fetched_at": datetime.now(),
            "analyzed_at": datetime.now(),
            "posted_at": datetime.now()
        }
        response = JobResponse(**data)
        assert response.id == 1
        assert response.score == JobScore.HIGH

    def test_job_response_minimal(self):
        """Test job response with minimal data"""
        data = {
            "id": 1,
            "external_job_id": "job_123",
            "title": "Developer",
            "company": "Corp",
            "location": None,
            "job_type": None,
            "description": "Desc",
            "requirements": None,
            "url": None,
            "salary_range": None,
            "score": JobScore.PENDING,
            "compatibility_percentage": None,
            "missing_requirements": None,
            "suggested_summary": None,
            "needs_summary_change": False,
            "status": JobStatus.PENDING,
            "notified_at": None,
            "fetched_at": datetime.now(),
            "analyzed_at": None,
            "posted_at": None
        }
        response = JobResponse(**data)
        assert response.location is None

    def test_job_list_response_valid(self):
        """Test valid job list response"""
        job_data = {
            "id": 1,
            "external_job_id": "job_123",
            "title": "Developer",
            "company": "Corp",
            "location": None,
            "job_type": None,
            "description": "Desc",
            "requirements": None,
            "url": None,
            "salary_range": None,
            "score": JobScore.PENDING,
            "compatibility_percentage": None,
            "missing_requirements": None,
            "suggested_summary": None,
            "needs_summary_change": False,
            "status": JobStatus.PENDING,
            "notified_at": None,
            "fetched_at": datetime.now(),
            "analyzed_at": None,
            "posted_at": None
        }
        data = {
            "total": 10,
            "jobs": [job_data]
        }
        response = JobListResponse(**data)
        assert response.total == 10
        assert len(response.jobs) == 1

    def test_job_list_response_empty(self):
        """Test job list response with no jobs"""
        data = {
            "total": 0,
            "jobs": []
        }
        response = JobListResponse(**data)
        assert response.total == 0
        assert len(response.jobs) == 0

    def test_job_notified_update_default(self):
        """Test job notified update default value"""
        update = JobNotifiedUpdate()
        assert update.notified is True

    def test_job_notified_update_explicit(self):
        """Test job notified update explicit value"""
        update = JobNotifiedUpdate(notified=False)
        assert update.notified is False


class TestSchedulerSchemas:
    """Tests for Scheduler-related schemas"""

    def test_scheduler_trigger_response(self):
        """Test scheduler trigger response"""
        data = {
            "message": "Task triggered",
            "task_id": "abc123"
        }
        response = SchedulerTriggerResponse(**data)
        assert response.message == "Task triggered"
        assert response.task_id == "abc123"

    def test_scheduler_status_response(self):
        """Test scheduler status response"""
        data = {
            "is_running": True,
            "last_run": datetime.now(),
            "next_run": datetime.now(),
            "interval_minutes": 30
        }
        response = SchedulerStatusResponse(**data)
        assert response.is_running is True
        assert response.interval_minutes == 30

    def test_scheduler_status_response_no_runs(self):
        """Test scheduler status with no runs"""
        data = {
            "is_running": False,
            "last_run": None,
            "next_run": None,
            "interval_minutes": 60
        }
        response = SchedulerStatusResponse(**data)
        assert response.last_run is None
        assert response.next_run is None

    def test_scheduler_config_update_valid(self):
        """Test valid scheduler config update"""
        update = SchedulerConfigUpdate(interval_minutes=60)
        assert update.interval_minutes == 60

    def test_scheduler_config_update_min_value(self):
        """Test scheduler config with minimum interval"""
        update = SchedulerConfigUpdate(interval_minutes=10)
        assert update.interval_minutes == 10

    def test_scheduler_config_update_max_value(self):
        """Test scheduler config with maximum interval"""
        update = SchedulerConfigUpdate(interval_minutes=1440)
        assert update.interval_minutes == 1440

    def test_scheduler_config_update_too_low(self):
        """Test scheduler config with interval too low"""
        with pytest.raises(ValidationError) as exc_info:
            SchedulerConfigUpdate(interval_minutes=5)
        assert "greater than or equal to 10" in str(exc_info.value)

    def test_scheduler_config_update_too_high(self):
        """Test scheduler config with interval too high"""
        with pytest.raises(ValidationError) as exc_info:
            SchedulerConfigUpdate(interval_minutes=1500)
        assert "less than or equal to 1440" in str(exc_info.value)


class TestHealthSchema:
    """Tests for Health check schema"""

    def test_health_response_valid(self):
        """Test valid health response"""
        data = {
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "timestamp": datetime.now()
        }
        response = HealthResponse(**data)
        assert response.status == "healthy"
        assert response.database == "connected"
        assert response.redis == "connected"

    def test_health_response_unhealthy(self):
        """Test unhealthy health response"""
        data = {
            "status": "unhealthy",
            "database": "disconnected",
            "redis": "error",
            "timestamp": datetime.now()
        }
        response = HealthResponse(**data)
        assert response.status == "unhealthy"


class TestSchemaEdgeCases:
    """Edge case tests for schemas"""

    def test_job_response_all_scores(self):
        """Test job response with all score types"""
        base_data = {
            "id": 1,
            "external_job_id": "job_123",
            "title": "Developer",
            "company": "Corp",
            "location": None,
            "job_type": None,
            "description": "Desc",
            "requirements": None,
            "url": None,
            "salary_range": None,
            "compatibility_percentage": None,
            "missing_requirements": None,
            "suggested_summary": None,
            "needs_summary_change": False,
            "status": JobStatus.PENDING,
            "notified_at": None,
            "fetched_at": datetime.now(),
            "analyzed_at": None,
            "posted_at": None
        }

        for score in JobScore:
            data = {**base_data, "score": score}
            response = JobResponse(**data)
            assert response.score == score

    def test_job_response_all_statuses(self):
        """Test job response with all status types"""
        base_data = {
            "id": 1,
            "external_job_id": "job_123",
            "title": "Developer",
            "company": "Corp",
            "location": None,
            "job_type": None,
            "description": "Desc",
            "requirements": None,
            "url": None,
            "salary_range": None,
            "compatibility_percentage": None,
            "missing_requirements": None,
            "suggested_summary": None,
            "needs_summary_change": False,
            "score": JobScore.PENDING,
            "notified_at": None,
            "fetched_at": datetime.now(),
            "analyzed_at": None,
            "posted_at": None
        }

        for status in JobStatus:
            data = {**base_data, "status": status}
            response = JobResponse(**data)
            assert response.status == status

    def test_search_filter_create_many_keywords(self):
        """Test search filter with many keywords (up to max 20)"""
        keywords = [f"keyword_{i}" for i in range(20)]
        filter_create = SearchFilterCreate(name="Many Keywords", keywords=keywords)
        assert len(filter_create.keywords) == 20

    def test_job_response_special_characters_in_title(self):
        """Test job response with special characters"""
        data = {
            "id": 1,
            "external_job_id": "job_123",
            "title": "Software Engineer (Senior) - C++ / Python",
            "company": "A & B Corp <Tech>",
            "location": None,
            "job_type": None,
            "description": "Description with 'quotes' and \"double quotes\"",
            "requirements": None,
            "url": None,
            "salary_range": None,
            "compatibility_percentage": None,
            "missing_requirements": None,
            "suggested_summary": None,
            "needs_summary_change": False,
            "score": JobScore.PENDING,
            "status": JobStatus.PENDING,
            "notified_at": None,
            "fetched_at": datetime.now(),
            "analyzed_at": None,
            "posted_at": None
        }
        response = JobResponse(**data)
        assert "C++" in response.title
        assert "&" in response.company
