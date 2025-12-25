"""Unit tests for API Routers"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.models import CV, Job, SearchFilter, JobScore, JobStatus
from app.database import Base
from app.schemas import JobAnalysisResult


# Create a test FastAPI app
def create_test_app(db_session):
    """Create test FastAPI app with dependency override"""
    from app.routers import cv, jobs, filters, system, scheduler, notifications

    app = FastAPI()

    # Override database dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    from app.database import get_db
    app.dependency_overrides[get_db] = override_get_db

    # Include routers
    app.include_router(cv.router, prefix="/api/cv")
    app.include_router(jobs.router, prefix="/api/jobs")
    app.include_router(filters.router, prefix="/api/filters")
    app.include_router(system.router, prefix="/api")
    app.include_router(scheduler.router, prefix="/api/scheduler")
    app.include_router(notifications.router, prefix="/api/notifications")

    return app


class TestCVRouter:
    """Tests for CV router endpoints"""

    def test_get_current_cv_success(self, db_session, sample_cv):
        """Test getting current active CV"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.get("/api/cv/")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_cv.id
        assert data["filename"] == sample_cv.filename

    def test_get_current_cv_not_found(self, db_session):
        """Test getting CV when none exists"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.get("/api/cv/")
        assert response.status_code == 404
        assert "No active CV found" in response.json()["detail"]

    def test_get_all_cvs(self, db_session, sample_cv):
        """Test getting all CVs"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.get("/api/cv/all")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_update_summary_success(self, db_session, sample_cv):
        """Test updating CV summary"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.put(
            "/api/cv/summary",
            json={"summary": "Updated professional summary for testing purposes."}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Updated professional" in data["summary"]

    def test_update_summary_not_found(self, db_session):
        """Test updating summary when no CV exists"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.put(
            "/api/cv/summary",
            json={"summary": "This should fail because no CV exists."}
        )
        assert response.status_code == 404

    def test_update_summary_too_short(self, db_session, sample_cv):
        """Test updating summary with too short text"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.put(
            "/api/cv/summary",
            json={"summary": "Short"}
        )
        assert response.status_code == 422  # Validation error

    def test_delete_cv_success(self, db_session, sample_cv):
        """Test deleting CV"""
        app = create_test_app(db_session)
        client = TestClient(app)

        with patch('os.path.exists', return_value=True), \
             patch('os.remove'):
            response = client.delete(f"/api/cv/{sample_cv.id}")
            assert response.status_code == 204

    def test_delete_cv_not_found(self, db_session):
        """Test deleting non-existent CV"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.delete("/api/cv/9999")
        assert response.status_code == 404


class TestJobsRouter:
    """Tests for Jobs router endpoints"""

    def test_list_jobs(self, db_session, sample_job):
        """Test listing jobs"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.get("/api/jobs/")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "jobs" in data
        assert data["total"] >= 1

    def test_list_jobs_with_filters(self, db_session, sample_job):
        """Test listing jobs with filters"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.get("/api/jobs/", params={"score": "pending"})
        assert response.status_code == 200

    def test_list_jobs_pagination(self, db_session, sample_cv):
        """Test job listing pagination"""
        # Create multiple jobs
        for i in range(5):
            job = Job(
                cv_id=sample_cv.id,
                external_job_id=f"pagination_job_{i}",
                title=f"Job {i}",
                company="Test Corp",
                description="Test"
            )
            db_session.add(job)
        db_session.commit()

        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.get("/api/jobs/", params={"limit": 2, "offset": 0})
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 2

    def test_get_job_success(self, db_session, sample_job):
        """Test getting specific job"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.get(f"/api/jobs/{sample_job.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_job.id

    def test_get_job_not_found(self, db_session):
        """Test getting non-existent job"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.get("/api/jobs/9999")
        assert response.status_code == 404

    def test_mark_job_notified(self, db_session, sample_job):
        """Test marking job as notified"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.put(
            f"/api/jobs/{sample_job.id}/notified",
            json={"notified": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == JobStatus.NOTIFIED.value

    def test_delete_job(self, db_session, sample_job):
        """Test deleting (archiving) job"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.delete(f"/api/jobs/{sample_job.id}")
        assert response.status_code == 204

    def test_get_job_statistics(self, db_session, sample_job):
        """Test getting job statistics"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.get("/api/jobs/stats/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_jobs" in data
        assert "by_score" in data
        assert "by_status" in data

    def test_get_top_matches(self, db_session, sample_cv):
        """Test getting top matches"""
        # Create a high-scoring job
        job = Job(
            cv_id=sample_cv.id,
            external_job_id="high_match_job",
            title="Perfect Match",
            company="Dream Corp",
            description="Perfect job",
            score=JobScore.HIGH,
            compatibility_percentage=90,
            status=JobStatus.ANALYZED
        )
        db_session.add(job)
        db_session.commit()

        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.get("/api/jobs/top/matches")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data

    def test_get_recent_fetched(self, db_session, sample_job):
        """Test getting recently fetched jobs"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.get("/api/jobs/recent/fetched")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data

    def test_get_ai_status(self, db_session):
        """Test getting AI status"""
        app = create_test_app(db_session)
        client = TestClient(app)

        with patch('app.routers.jobs.AIMatchingService') as mock_ai:
            mock_instance = MagicMock()
            mock_instance.is_configured.return_value = True
            mock_instance.model = "test-model"
            mock_ai.return_value = mock_instance

            response = client.get("/api/jobs/ai/status")
            assert response.status_code == 200
            data = response.json()
            assert "ai_configured" in data
            assert "capabilities" in data


class TestFiltersRouter:
    """Tests for Filters router endpoints"""

    def test_get_all_filters(self, db_session, sample_search_filter):
        """Test getting all filters"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.get("/api/filters/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_filter_by_id(self, db_session, sample_search_filter):
        """Test getting filter by ID"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.get(f"/api/filters/{sample_search_filter.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_search_filter.id

    def test_get_filter_not_found(self, db_session):
        """Test getting non-existent filter"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.get("/api/filters/9999")
        assert response.status_code == 404

    def test_create_filter(self, db_session):
        """Test creating new filter"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.post(
            "/api/filters/",
            json={
                "name": "New Test Filter",
                "keywords": ["Python", "Django"],
                "location": "New York",
                "remote": True
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Test Filter"

    def test_create_filter_validation_error(self, db_session):
        """Test filter creation with invalid data"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.post(
            "/api/filters/",
            json={
                "name": "",  # Empty name
                "keywords": []  # Empty keywords
            }
        )
        assert response.status_code == 422

    def test_update_filter(self, db_session, sample_search_filter):
        """Test updating filter"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.put(
            f"/api/filters/{sample_search_filter.id}",
            json={"name": "Updated Filter Name"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Filter Name"

    def test_delete_filter(self, db_session, sample_search_filter):
        """Test deleting filter"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.delete(f"/api/filters/{sample_search_filter.id}")
        assert response.status_code == 204


class TestSystemRouter:
    """Tests for System router endpoints"""

    def test_health_check_healthy(self, db_session):
        """Test health check when system is healthy"""
        app = create_test_app(db_session)
        client = TestClient(app)

        with patch('app.routers.system.redis') as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis.from_url.return_value = mock_client

            response = client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"] == "connected"

    def test_health_check_database_error(self, db_session):
        """Test health check when database has error"""
        app = create_test_app(db_session)
        client = TestClient(app)

        with patch.object(db_session, 'execute', side_effect=Exception("DB Error")), \
             patch('app.routers.system.redis') as mock_redis:
            mock_client = MagicMock()
            mock_redis.from_url.return_value = mock_client

            response = client.get("/api/health")
            data = response.json()
            assert "error" in data["database"]


class TestJobAnalysisRouter:
    """Tests for job analysis endpoints"""

    def test_analyze_job_success(self, db_session, sample_cv, sample_job):
        """Test analyzing single job"""
        app = create_test_app(db_session)
        client = TestClient(app)

        with patch('app.routers.jobs.AIMatchingService') as mock_ai:
            mock_instance = MagicMock()
            mock_instance.is_configured.return_value = True
            mock_instance.analyze_job_match.return_value = JobAnalysisResult(
                score="high",
                compatibility_percentage=85,
                matching_skills=["python", "fastapi"],
                missing_requirements=[],
                needs_summary_change=False,
                suggested_summary=None,
                analysis_reasoning="Good match"
            )
            mock_ai.return_value = mock_instance

            response = client.post(f"/api/jobs/{sample_job.id}/analyze")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_analyze_job_already_analyzed(self, db_session, sample_cv, sample_job):
        """Test analyzing already analyzed job without force"""
        sample_job.analyzed_at = datetime.utcnow()
        sample_job.score = JobScore.HIGH
        sample_job.compatibility_percentage = 90
        db_session.commit()

        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.post(f"/api/jobs/{sample_job.id}/analyze")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert data["reason"] == "already_analyzed"

    def test_analyze_job_no_cv(self, db_session, sample_job):
        """Test analyzing job without active CV"""
        # Remove CV association
        sample_job.cv_id = None
        db_session.commit()

        # Make sure no active CV exists
        db_session.query(CV).update({"is_active": False})
        db_session.commit()

        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.post(f"/api/jobs/{sample_job.id}/analyze")
        assert response.status_code == 400
        assert "No active CV" in response.json()["detail"]

    def test_analyze_batch_success(self, db_session, sample_cv, sample_job):
        """Test batch analysis"""
        app = create_test_app(db_session)
        client = TestClient(app)

        with patch('app.routers.jobs.AIMatchingService') as mock_ai:
            mock_instance = MagicMock()
            mock_instance.is_configured.return_value = True
            mock_instance.analyze_job_match.return_value = JobAnalysisResult(
                score="high",
                compatibility_percentage=85,
                matching_skills=["python"],
                missing_requirements=[],
                needs_summary_change=False,
                suggested_summary=None,
                analysis_reasoning="Good match"
            )
            mock_ai.return_value = mock_instance

            response = client.post("/api/jobs/analyze/batch")
            assert response.status_code == 200
            data = response.json()
            assert "analyzed_count" in data


class TestRouterEdgeCases:
    """Edge case tests for routers"""

    def test_jobs_list_invalid_limit(self, db_session):
        """Test job listing with invalid limit"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.get("/api/jobs/", params={"limit": 500})  # Above max
        assert response.status_code == 422

    def test_jobs_list_invalid_offset(self, db_session):
        """Test job listing with negative offset"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.get("/api/jobs/", params={"offset": -1})
        assert response.status_code == 422

    def test_filter_create_duplicate_keywords(self, db_session):
        """Test creating filter with duplicate keywords"""
        app = create_test_app(db_session)
        client = TestClient(app)

        response = client.post(
            "/api/filters/",
            json={
                "name": "Duplicate Keywords",
                "keywords": ["Python", "Python", "Django"]
            }
        )
        # Should still work (duplicates allowed at API level)
        assert response.status_code == 201
