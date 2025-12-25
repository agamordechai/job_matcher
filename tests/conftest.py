"""Pytest configuration and fixtures for job_matcher tests"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import CV, Job, SearchFilter, NotificationLog, JobScore, JobStatus
from app.schemas import JSearchAPIResponse, JSearchJobResponse, JobAnalysisResult


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def engine():
    """Create a test database engine"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine):
    """Create a test database session"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_cv_content():
    """Sample CV content for testing"""
    return """
    John Doe
    Software Engineer

    Professional Summary:
    Experienced software engineer with 5 years of experience in Python and JavaScript development.
    Strong background in backend development, API design, and cloud infrastructure.

    Technical Skills:
    - Programming Languages: Python, JavaScript, TypeScript, SQL
    - Frameworks: FastAPI, Django, React, Node.js
    - Databases: PostgreSQL, MongoDB, Redis
    - Cloud: AWS, Docker, Kubernetes
    - Tools: Git, Jenkins, Terraform

    Experience:
    Senior Software Engineer at TechCorp (2020-Present)
    - Developed RESTful APIs using FastAPI
    - Implemented microservices architecture
    - Managed AWS infrastructure with Terraform

    Software Developer at StartupXYZ (2018-2020)
    - Built web applications using React and Django
    - Designed and optimized PostgreSQL databases

    Education:
    B.S. Computer Science, State University, 2018
    """


@pytest.fixture
def sample_cv(db_session, sample_cv_content):
    """Create a sample CV in the database"""
    cv = CV(
        filename="test_cv.pdf",
        file_path="/tmp/test_cv.pdf",
        content=sample_cv_content,
        summary="Experienced software engineer with Python and JavaScript expertise.",
        is_active=True
    )
    db_session.add(cv)
    db_session.commit()
    db_session.refresh(cv)
    return cv


@pytest.fixture
def sample_job_data():
    """Sample job data dictionary"""
    return {
        "external_job_id": "job_123456",
        "title": "Software Engineer",
        "company": "TechCorp",
        "location": "San Francisco, CA",
        "job_type": "full-time",
        "experience_level": "mid",
        "description": "We are looking for a Software Engineer to join our team...",
        "requirements": "3+ years of Python experience, AWS knowledge, PostgreSQL",
        "url": "https://example.com/job/123",
        "salary_range": "USD 100,000 - 150,000 per year",
    }


@pytest.fixture
def sample_job(db_session, sample_cv, sample_job_data):
    """Create a sample job in the database"""
    job = Job(
        cv_id=sample_cv.id,
        external_job_id=sample_job_data["external_job_id"],
        title=sample_job_data["title"],
        company=sample_job_data["company"],
        location=sample_job_data["location"],
        job_type=sample_job_data["job_type"],
        experience_level=sample_job_data["experience_level"],
        description=sample_job_data["description"],
        requirements=sample_job_data["requirements"],
        url=sample_job_data["url"],
        salary_range=sample_job_data["salary_range"],
        score=JobScore.PENDING,
        status=JobStatus.PENDING,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def sample_search_filter(db_session):
    """Create a sample search filter in the database"""
    filter_obj = SearchFilter(
        name="Test Filter",
        keywords=["Software Engineer", "Backend Developer"],
        location="United States",
        job_type="full-time",
        experience_level="mid",
        remote=True,
        is_active=True
    )
    db_session.add(filter_obj)
    db_session.commit()
    db_session.refresh(filter_obj)
    return filter_obj


@pytest.fixture
def jsearch_api_response():
    """Sample JSearch API response as Pydantic model"""
    return JSearchAPIResponse(
        status="OK",
        request_id="test-request-id",
        data=[
            JSearchJobResponse(
                job_id="jsearch_job_1",
                job_title="Senior Python Developer",
                employer_name="Innovation Labs",
                job_city="Austin",
                job_state="TX",
                job_country="US",
                job_employment_type="FULLTIME",
                job_description="We are seeking a talented Python developer...",
                job_highlights={
                    "Qualifications": [
                        "5+ years Python experience",
                        "Strong knowledge of Django or FastAPI"
                    ],
                    "Responsibilities": [
                        "Design and implement backend services",
                        "Collaborate with frontend team"
                    ]
                },
                job_apply_link="https://jobs.example.com/apply/123",
                job_min_salary=120000,
                job_max_salary=180000,
                job_salary_currency="USD",
                job_salary_period="YEAR",
                job_posted_at_timestamp=1700000000,
            ),
            JSearchJobResponse(
                job_id="jsearch_job_2",
                job_title="Junior Software Engineer",
                employer_name="Startup Inc",
                job_city="Remote",
                job_employment_type="FULLTIME",
                job_description="Entry-level position for recent graduates...",
                job_apply_link="https://jobs.example.com/apply/456",
            )
        ]
    )


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    with patch('app.config.get_settings') as mock:
        settings = MagicMock()
        settings.database_url = "sqlite:///:memory:"
        settings.redis_url = "redis://localhost:6379/0"
        settings.anthropic_api_key = "test-api-key"
        settings.rapidapi_key = "test-rapidapi-key"
        settings.rapidapi_host = "jsearch.p.rapidapi.com"
        settings.smtp_host = "smtp.gmail.com"
        settings.smtp_port = 587
        settings.smtp_user = "test@example.com"
        settings.smtp_pass = "test_password"
        settings.notification_email = "notify@example.com"
        settings.cv_storage_path = "/tmp/cvs"
        settings.temp_storage_path = "/tmp/temp"
        settings.job_prefilter_enabled = True
        settings.job_title_exclude_keywords = "senior,sr.,experienced,architect,staff,team lead,manager"
        settings.job_title_include_keywords = ""
        settings.job_title_must_notify_keywords = "junior,entry-level,intern,graduate"
        settings.search_max_pages = 2
        settings.search_date_posted = "month"
        settings.get_exclude_keywords = lambda: ["senior", "sr.", "experienced", "architect", "staff", "team lead", "manager"]
        settings.get_include_keywords = lambda: []
        settings.get_must_notify_keywords = lambda: ["junior", "entry-level", "intern", "graduate"]
        mock.return_value = settings
        yield settings


@pytest.fixture
def mock_upload_file():
    """Mock FastAPI UploadFile"""
    mock_file = MagicMock()
    mock_file.filename = "test_cv.pdf"
    mock_file.read = AsyncMock(return_value=b"PDF content here")
    return mock_file


@pytest.fixture
def ai_analysis_response():
    """Sample AI analysis response as Pydantic model"""
    return JobAnalysisResult(
        score="high",
        compatibility_percentage=85,
        matching_skills=["python", "fastapi", "postgresql", "aws", "docker"],
        missing_requirements=["kubernetes"],
        needs_summary_change=False,
        suggested_summary=None,
        analysis_reasoning="Strong match with relevant experience in Python and backend development.",
        prefiltered=False,
        must_notify=False
    )


# Async test support
@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
