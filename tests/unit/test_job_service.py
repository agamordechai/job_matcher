"""Unit tests for Job Service"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from app.services.job_service import JobService
from app.models import Job, JobScore, JobStatus


class TestJobService:
    """Tests for JobService class"""

    def test_init(self, db_session):
        """Test service initialization"""
        service = JobService(db_session)
        assert service.db == db_session

    def test_get_job_by_id(self, db_session, sample_job):
        """Test getting job by ID"""
        service = JobService(db_session)
        result = service.get_job(sample_job.id)
        assert result is not None
        assert result.id == sample_job.id
        assert result.title == sample_job.title

    def test_get_job_by_id_not_found(self, db_session):
        """Test returns None for non-existent job"""
        service = JobService(db_session)
        result = service.get_job(9999)
        assert result is None

    def test_get_job_by_external_id(self, db_session, sample_job):
        """Test getting job by external ID"""
        service = JobService(db_session)
        result = service.get_job_by_external_id(sample_job.external_job_id)
        assert result is not None
        assert result.external_job_id == sample_job.external_job_id

    def test_get_job_by_external_id_not_found(self, db_session):
        """Test returns None for non-existent external ID"""
        service = JobService(db_session)
        result = service.get_job_by_external_id("non_existent_id")
        assert result is None


class TestJobServiceList:
    """Tests for job listing functionality"""

    def test_list_jobs_no_filters(self, db_session, sample_job):
        """Test listing jobs without filters"""
        service = JobService(db_session)
        jobs, total = service.list_jobs()
        assert total >= 1
        assert len(jobs) >= 1

    def test_list_jobs_filter_by_score(self, db_session, sample_job, sample_cv):
        """Test filtering jobs by score"""
        # Create a job with HIGH score
        high_job = Job(
            cv_id=sample_cv.id,
            external_job_id="high_score_job",
            title="High Score Job",
            company="Test Corp",
            description="Test description",
            score=JobScore.HIGH,
            status=JobStatus.ANALYZED
        )
        db_session.add(high_job)
        db_session.commit()

        service = JobService(db_session)
        jobs, total = service.list_jobs(score=JobScore.HIGH)
        assert total == 1
        assert jobs[0].score == JobScore.HIGH

    def test_list_jobs_filter_by_status(self, db_session, sample_job, sample_cv):
        """Test filtering jobs by status"""
        # Create a job with NOTIFIED status
        notified_job = Job(
            cv_id=sample_cv.id,
            external_job_id="notified_job",
            title="Notified Job",
            company="Test Corp",
            description="Test description",
            status=JobStatus.NOTIFIED,
            notified_at=datetime.utcnow()
        )
        db_session.add(notified_job)
        db_session.commit()

        service = JobService(db_session)
        jobs, total = service.list_jobs(status=JobStatus.NOTIFIED)
        assert total == 1
        assert jobs[0].status == JobStatus.NOTIFIED

    def test_list_jobs_filter_by_notified_true(self, db_session, sample_job, sample_cv):
        """Test filtering for notified jobs"""
        # Set sample_job as notified
        sample_job.notified_at = datetime.utcnow()
        db_session.commit()

        service = JobService(db_session)
        jobs, total = service.list_jobs(notified=True)
        assert total == 1
        assert jobs[0].notified_at is not None

    def test_list_jobs_filter_by_notified_false(self, db_session, sample_job):
        """Test filtering for non-notified jobs"""
        service = JobService(db_session)
        jobs, total = service.list_jobs(notified=False)
        assert total >= 1
        for job in jobs:
            assert job.notified_at is None

    def test_list_jobs_pagination(self, db_session, sample_cv):
        """Test job listing pagination"""
        # Create multiple jobs
        for i in range(5):
            job = Job(
                cv_id=sample_cv.id,
                external_job_id=f"job_{i}",
                title=f"Job {i}",
                company="Test Corp",
                description="Test description"
            )
            db_session.add(job)
        db_session.commit()

        service = JobService(db_session)

        # Test limit
        jobs, total = service.list_jobs(limit=2)
        assert len(jobs) == 2
        assert total == 5

        # Test offset
        jobs, total = service.list_jobs(limit=2, offset=2)
        assert len(jobs) == 2
        assert total == 5


class TestJobServiceCreate:
    """Tests for job creation"""

    def test_create_job(self, db_session, sample_cv):
        """Test creating a new job"""
        service = JobService(db_session)
        job_data = {
            "cv_id": sample_cv.id,
            "external_job_id": "new_job_123",
            "title": "New Software Engineer Position",
            "company": "New Tech Corp",
            "description": "Looking for talented engineers",
            "location": "Remote",
            "job_type": "full-time"
        }

        result = service.create_job(job_data)
        assert result is not None
        assert result.id is not None
        assert result.external_job_id == "new_job_123"
        assert result.title == "New Software Engineer Position"
        assert result.status == JobStatus.PENDING
        assert result.score == JobScore.PENDING


class TestJobServiceUpdate:
    """Tests for job update operations"""

    def test_mark_as_notified(self, db_session, sample_job):
        """Test marking job as notified"""
        service = JobService(db_session)
        result = service.mark_as_notified(sample_job.id)

        assert result is not None
        assert result.status == JobStatus.NOTIFIED
        assert result.notified_at is not None

    def test_mark_as_notified_not_found(self, db_session):
        """Test marking non-existent job as notified"""
        service = JobService(db_session)
        result = service.mark_as_notified(9999)
        assert result is None

    def test_update_job_analysis(self, db_session, sample_job):
        """Test updating job with analysis results"""
        service = JobService(db_session)

        result = service.update_job_analysis(
            job_id=sample_job.id,
            score=JobScore.HIGH,
            compatibility_percentage=85,
            missing_requirements=["kubernetes", "terraform"],
            suggested_summary="Tailored summary for this role.",
            needs_summary_change=True,
            must_notify=True
        )

        assert result is not None
        assert result.score == JobScore.HIGH
        assert result.compatibility_percentage == 85
        assert result.missing_requirements == ["kubernetes", "terraform"]
        assert result.suggested_summary == "Tailored summary for this role."
        assert result.needs_summary_change is True
        assert result.must_notify is True
        assert result.status == JobStatus.ANALYZED
        assert result.analyzed_at is not None

    def test_update_job_analysis_not_found(self, db_session):
        """Test updating non-existent job"""
        service = JobService(db_session)
        result = service.update_job_analysis(
            job_id=9999,
            score=JobScore.HIGH,
            compatibility_percentage=85,
            missing_requirements=[],
            suggested_summary=None,
            needs_summary_change=False
        )
        assert result is None


class TestJobServiceDelete:
    """Tests for job deletion"""

    def test_delete_job_archives(self, db_session, sample_job):
        """Test that delete actually archives job"""
        service = JobService(db_session)
        result = service.delete_job(sample_job.id)

        assert result is True
        db_session.refresh(sample_job)
        assert sample_job.status == JobStatus.ARCHIVED

    def test_delete_job_not_found(self, db_session):
        """Test deleting non-existent job returns False"""
        service = JobService(db_session)
        result = service.delete_job(9999)
        assert result is False


class TestJobServiceEdgeCases:
    """Edge case tests for Job Service"""

    def test_list_jobs_empty_database(self, db_session):
        """Test listing jobs when database is empty"""
        service = JobService(db_session)
        jobs, total = service.list_jobs()
        assert total == 0
        assert len(jobs) == 0

    def test_create_job_minimal_data(self, db_session):
        """Test creating job with minimal required data"""
        service = JobService(db_session)
        job_data = {
            "external_job_id": "minimal_job",
            "title": "Minimal Job",
            "company": "Test Corp",
            "description": "Description"
        }
        result = service.create_job(job_data)
        assert result is not None
        assert result.location is None
        assert result.salary_range is None

    def test_multiple_filters_combined(self, db_session, sample_cv):
        """Test combining multiple filters"""
        # Create a job that matches all filters
        job = Job(
            cv_id=sample_cv.id,
            external_job_id="multi_filter_job",
            title="Multi Filter Job",
            company="Test Corp",
            description="Test description",
            score=JobScore.HIGH,
            status=JobStatus.ANALYZED
        )
        db_session.add(job)
        db_session.commit()

        service = JobService(db_session)
        jobs, total = service.list_jobs(
            score=JobScore.HIGH,
            status=JobStatus.ANALYZED,
            notified=False
        )
        assert total == 1
        assert jobs[0].external_job_id == "multi_filter_job"
