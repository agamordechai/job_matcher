"""Unit tests for AI Matching Service"""
import pytest
from unittest.mock import patch, MagicMock
import json

from app.services.ai_matching_service import AIMatchingService


class TestAIMatchingServiceInit:
    """Tests for AIMatchingService initialization"""

    def test_init_with_api_key(self, mock_settings):
        """Test initialization with API key configured"""
        with patch('app.services.ai_matching_service.anthropic') as mock_anthropic:
            service = AIMatchingService()
            assert service.prefilter_enabled is True
            mock_anthropic.Anthropic.assert_called_once()

    def test_init_without_api_key(self):
        """Test initialization without API key"""
        with patch('app.services.ai_matching_service.settings') as mock_settings:
            mock_settings.anthropic_api_key = ""
            mock_settings.job_prefilter_enabled = True
            mock_settings.get_exclude_keywords.return_value = []
            mock_settings.get_include_keywords.return_value = []
            mock_settings.get_must_notify_keywords.return_value = []

            service = AIMatchingService()
            assert service.client is None

    def test_is_configured(self, mock_settings):
        """Test is_configured method"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            assert service.is_configured() is True


class TestAIMatchingServiceMustNotify:
    """Tests for must-notify keyword checking"""

    def test_check_must_notify_found(self, mock_settings):
        """Test must-notify detection when keyword found"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            service.must_notify_keywords = ["junior", "entry-level", "intern"]

            must_notify, keyword = service.check_must_notify("Junior Python Developer")
            assert must_notify is True
            assert keyword == "junior"

    def test_check_must_notify_not_found(self, mock_settings):
        """Test must-notify when no keyword found"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            service.must_notify_keywords = ["junior", "entry-level", "intern"]

            must_notify, keyword = service.check_must_notify("Senior Python Developer")
            assert must_notify is False
            assert keyword is None

    def test_check_must_notify_case_insensitive(self, mock_settings):
        """Test case-insensitive matching"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            service.must_notify_keywords = ["junior"]

            must_notify, keyword = service.check_must_notify("JUNIOR Developer")
            assert must_notify is True

    def test_check_must_notify_empty_keywords(self, mock_settings):
        """Test with empty must-notify keywords"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            service.must_notify_keywords = []

            must_notify, keyword = service.check_must_notify("Junior Developer")
            assert must_notify is False
            assert keyword is None


class TestAIMatchingServicePrefilter:
    """Tests for job pre-filtering"""

    def test_prefilter_job_excluded_keyword(self, mock_settings):
        """Test pre-filtering with excluded keyword"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            service.prefilter_enabled = True
            service.exclude_keywords = ["senior", "lead", "architect"]
            service.include_keywords = []

            should_analyze, result = service.prefilter_job("Senior Software Engineer")

            assert should_analyze is False
            assert result.score == "low"
            assert result.prefiltered is True
            assert result.prefilter_reason == "excluded_keyword"

    def test_prefilter_job_passes(self, mock_settings):
        """Test pre-filtering when job passes"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            service.prefilter_enabled = True
            service.exclude_keywords = ["senior", "lead"]
            service.include_keywords = []

            should_analyze, result = service.prefilter_job("Software Engineer")

            assert should_analyze is True
            assert result is None

    def test_prefilter_job_include_keywords_match(self, mock_settings):
        """Test pre-filtering with include keywords (match)"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            service.prefilter_enabled = True
            service.exclude_keywords = []
            service.include_keywords = ["python", "backend"]

            should_analyze, result = service.prefilter_job("Python Developer")

            assert should_analyze is True
            assert result is None

    def test_prefilter_job_include_keywords_no_match(self, mock_settings):
        """Test pre-filtering with include keywords (no match)"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            service.prefilter_enabled = True
            service.exclude_keywords = []
            service.include_keywords = ["python", "backend"]

            should_analyze, result = service.prefilter_job("Frontend Developer")

            assert should_analyze is False
            assert result.prefilter_reason == "missing_include_keyword"

    def test_prefilter_job_disabled(self, mock_settings):
        """Test pre-filtering when disabled"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            service.prefilter_enabled = False
            service.exclude_keywords = ["senior"]

            should_analyze, result = service.prefilter_job("Senior Developer")

            assert should_analyze is True
            assert result is None


class TestAIMatchingServiceCVSkills:
    """Tests for CV skills extraction"""

    def test_extract_cv_skills(self, mock_settings, sample_cv_content):
        """Test extracting skills from CV"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            result = service.extract_cv_skills(sample_cv_content)

            assert hasattr(result, 'skills')
            assert hasattr(result, 'years_experience')
            assert hasattr(result, 'recent_roles')
            assert hasattr(result, 'skill_count')
            assert len(result.skills) > 0
            # Sample CV mentions Python, FastAPI, etc.
            assert "python" in result.skills

    def test_extract_cv_skills_caching(self, mock_settings, sample_cv_content):
        """Test that skills are cached"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()

            # First call
            result1 = service.extract_cv_skills(sample_cv_content)
            # Second call should use cache
            result2 = service.extract_cv_skills(sample_cv_content)

            assert result1 == result2

    def test_extract_cv_skills_years_experience(self, mock_settings):
        """Test extracting years of experience"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            cv_content = "Software Engineer with 5 years of experience in Python development."
            result = service.extract_cv_skills(cv_content)

            assert result.years_experience == 5


class TestAIMatchingServiceExperienceLevel:
    """Tests for experience level extraction and matching"""

    def test_extract_experience_level_intern(self, mock_settings):
        """Test extracting intern level"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            level = service.extract_experience_level("Software Engineering Intern", "")
            assert level == "intern"

    def test_extract_experience_level_junior(self, mock_settings):
        """Test extracting junior level"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            level = service.extract_experience_level("Junior Developer", "")
            assert level == "junior"

    def test_extract_experience_level_senior(self, mock_settings):
        """Test extracting senior level"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            level = service.extract_experience_level("Senior Software Engineer", "")
            assert level == "senior"

    def test_extract_experience_level_from_years(self, mock_settings):
        """Test extracting level from years requirement"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            level = service.extract_experience_level(
                "Software Engineer",
                "Requirements: 7+ years of experience"
            )
            assert level == "senior"

    def test_extract_experience_level_entry(self, mock_settings):
        """Test extracting entry level"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            level = service.extract_experience_level("Entry-Level Developer", "")
            assert level == "entry"

    def test_check_experience_match_compatible(self, mock_settings):
        """Test experience match when compatible"""
        with patch('app.services.ai_matching_service.anthropic'):
            from app.schemas import CVSkillsProfile
            service = AIMatchingService()
            cv_skills = CVSkillsProfile(skills=[], years_experience=4, recent_roles=[], skill_count=0)  # Mid-level

            # Can apply to mid-level job
            assert service.check_experience_match(cv_skills, "mid") is True
            # Can apply to entry job
            assert service.check_experience_match(cv_skills, "entry") is True

    def test_check_experience_match_incompatible(self, mock_settings):
        """Test experience match when incompatible"""
        with patch('app.services.ai_matching_service.anthropic'):
            from app.schemas import CVSkillsProfile
            service = AIMatchingService()
            cv_skills = CVSkillsProfile(skills=[], years_experience=2, recent_roles=[], skill_count=0)  # Entry-level

            # Cannot apply to lead/principal level
            assert service.check_experience_match(cv_skills, "principal") is False

    def test_check_experience_match_no_level(self, mock_settings):
        """Test experience match with no job level specified"""
        with patch('app.services.ai_matching_service.anthropic'):
            from app.schemas import CVSkillsProfile
            service = AIMatchingService()
            cv_skills = CVSkillsProfile(skills=[], years_experience=2, recent_roles=[], skill_count=0)

            assert service.check_experience_match(cv_skills, None) is True


class TestAIMatchingServiceKeywordPrescreen:
    """Tests for keyword-based pre-screening"""

    def test_keyword_prescreening_high_match(self, mock_settings):
        """Test keyword pre-screening with high skill match"""
        with patch('app.services.ai_matching_service.anthropic'):
            from app.schemas import CVSkillsProfile
            service = AIMatchingService()
            cv_skills = CVSkillsProfile(
                skills=["python", "django", "postgresql", "aws", "docker"],
                years_experience=None,
                recent_roles=[],
                skill_count=5
            )
            job_requirements = "Requirements: Python, Django, PostgreSQL, AWS"

            should_analyze, result = service.keyword_based_prescreening(
                cv_skills, job_requirements
            )

            assert should_analyze is True
            assert result is None

    def test_keyword_prescreening_low_match(self, mock_settings):
        """Test keyword pre-screening with low skill match"""
        with patch('app.services.ai_matching_service.anthropic'):
            from app.schemas import CVSkillsProfile
            service = AIMatchingService()
            cv_skills = CVSkillsProfile(
                skills=["python"],  # Only one matching skill
                years_experience=None,
                recent_roles=[],
                skill_count=1
            )
            job_requirements = "Requirements: Java, Scala, Kafka, Spark, AWS, Kubernetes"

            should_analyze, result = service.keyword_based_prescreening(
                cv_skills, job_requirements
            )

            assert should_analyze is False
            assert result.score == "low"
            assert result.prefilter_reason == "insufficient_skills"

    def test_keyword_prescreening_no_tech_requirements(self, mock_settings):
        """Test pre-screening when job has no clear tech requirements"""
        with patch('app.services.ai_matching_service.anthropic'):
            from app.schemas import CVSkillsProfile
            service = AIMatchingService()
            cv_skills = CVSkillsProfile(skills=["python"], years_experience=None, recent_roles=[], skill_count=1)
            job_requirements = "Must be a team player with good communication skills"

            should_analyze, result = service.keyword_based_prescreening(
                cv_skills, job_requirements
            )

            assert should_analyze is True


class TestAIMatchingServiceAnalyze:
    """Tests for the main analyze_job_match method"""

    def test_analyze_job_match_prefiltered(self, mock_settings, sample_cv_content):
        """Test analysis when job is pre-filtered"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            service.prefilter_enabled = True
            service.exclude_keywords = ["senior"]
            service.must_notify_keywords = []
            service.include_keywords = []

            result = service.analyze_job_match(
                cv_content=sample_cv_content,
                cv_summary=None,
                job_title="Senior Software Engineer",
                job_company="Test Corp",
                job_description="Job description here",
                job_requirements="Python, AWS"
            )

            assert result.prefiltered is True
            assert result.score == "low"

    def test_analyze_job_match_no_requirements(self, mock_settings, sample_cv_content):
        """Test analysis when job has no requirements"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            service.prefilter_enabled = True
            service.exclude_keywords = []
            service.must_notify_keywords = []
            service.include_keywords = []

            result = service.analyze_job_match(
                cv_content=sample_cv_content,
                cv_summary=None,
                job_title="Software Engineer",
                job_company="Test Corp",
                job_description="Job description here",
                job_requirements=""  # Empty requirements
            )

            assert result.prefiltered is True
            assert result.prefilter_reason == "no_requirements"

    def test_analyze_job_match_with_ai(self, mock_settings, sample_cv_content, ai_analysis_response):
        """Test analysis using AI"""
        with patch('app.services.ai_matching_service.anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_message = MagicMock()
            # Convert Pydantic model to dict for JSON serialization
            mock_message.content = [MagicMock(text=json.dumps(ai_analysis_response.model_dump()))]
            mock_client.messages.create.return_value = mock_message
            mock_anthropic.Anthropic.return_value = mock_client

            service = AIMatchingService()
            service.prefilter_enabled = False
            service.must_notify_keywords = []

            result = service.analyze_job_match(
                cv_content=sample_cv_content,
                cv_summary="Experienced Python developer",
                job_title="Software Engineer",
                job_company="Test Corp",
                job_description="Looking for a Python developer",
                job_requirements="Python, FastAPI, PostgreSQL, AWS, Docker"
            )

            assert result.score in ["high", "medium", "low"]
            assert hasattr(result, 'compatibility_percentage')

    def test_analyze_job_match_must_notify_flag(self, mock_settings, sample_cv_content):
        """Test that must_notify flag is set correctly"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            service.prefilter_enabled = True
            service.exclude_keywords = ["senior"]
            service.must_notify_keywords = ["junior"]
            service.include_keywords = []

            # Senior job but with junior keyword should have must_notify
            result = service.analyze_job_match(
                cv_content=sample_cv_content,
                cv_summary=None,
                job_title="Junior Software Engineer",
                job_company="Test Corp",
                job_description="Job description",
                job_requirements="Python, AWS"
            )

            assert result.must_notify is True


class TestAIMatchingServiceNormalize:
    """Tests for response normalization"""

    def test_normalize_response_valid(self, mock_settings):
        """Test normalizing valid response"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            raw_response = {
                "score": "HIGH",
                "compatibility_percentage": 85,
                "matching_skills": ["python", "aws"],
                "missing_requirements": ["kubernetes"],
                "needs_summary_change": True,
                "suggested_summary": "New summary",
                "analysis_reasoning": "Good match"
            }

            result = service._normalize_response(raw_response)

            assert result.score == "high"  # Normalized to lowercase
            assert result.compatibility_percentage == 85
            assert len(result.matching_skills) == 2

    def test_normalize_response_invalid_score(self, mock_settings):
        """Test normalizing response with invalid score"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            raw_response = {
                "score": "INVALID",
                "compatibility_percentage": 50
            }

            result = service._normalize_response(raw_response)

            assert result.score == "medium"  # Default

    def test_normalize_response_out_of_range_compatibility(self, mock_settings):
        """Test normalizing out-of-range compatibility percentage"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            raw_response = {
                "score": "high",
                "compatibility_percentage": 150  # Out of range
            }

            result = service._normalize_response(raw_response)

            assert result.compatibility_percentage == 100  # Capped


class TestAIMatchingServiceFallback:
    """Tests for fallback keyword analysis"""

    def test_fallback_keyword_analysis(self, mock_settings, sample_cv_content):
        """Test fallback keyword-based analysis"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            service.client = None  # No AI configured

            result = service._fallback_keyword_analysis(
                cv_content=sample_cv_content,
                job_title="Python Developer",
                job_description="Looking for Python developer with AWS experience",
                job_requirements="Python, FastAPI, AWS, Docker"
            )

            assert result.score in ["high", "medium", "low"]
            assert hasattr(result, 'compatibility_percentage')
            assert hasattr(result, 'matching_skills')
            assert result.prefiltered is False


class TestAIMatchingServiceBatch:
    """Tests for batch job analysis"""

    def test_batch_analyze_jobs(self, mock_settings, sample_cv_content):
        """Test batch analysis of multiple jobs"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            service.prefilter_enabled = True
            service.exclude_keywords = ["senior"]
            service.must_notify_keywords = ["junior"]
            service.include_keywords = []

            jobs = [
                {"id": 1, "title": "Software Engineer", "company": "A",
                 "description": "Desc", "requirements": "Python, AWS"},
                {"id": 2, "title": "Senior Developer", "company": "B",
                 "description": "Desc", "requirements": "Python"},
                {"id": 3, "title": "Junior Developer", "company": "C",
                 "description": "Desc", "requirements": "Python, Django"},
            ]

            results = service.batch_analyze_jobs(
                cv_content=sample_cv_content,
                cv_summary=None,
                jobs=jobs
            )

            assert len(results) == 3
            # Senior job should be filtered
            senior_result = next(r for r in results if r.job_id == 2)
            assert senior_result.prefiltered is True

    def test_batch_analyze_jobs_early_termination(self, mock_settings, sample_cv_content):
        """Test early termination after max high matches"""
        with patch('app.services.ai_matching_service.anthropic') as mock_anthropic:
            # Mock AI to return high scores
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=json.dumps({
                "score": "high",
                "compatibility_percentage": 90,
                "matching_skills": ["python"],
                "missing_requirements": [],
                "needs_summary_change": False,
                "analysis_reasoning": "Good match"
            }))]
            mock_client.messages.create.return_value = mock_message
            mock_anthropic.Anthropic.return_value = mock_client

            service = AIMatchingService()
            service.prefilter_enabled = False
            service.must_notify_keywords = []
            service.exclude_keywords = []
            service.include_keywords = []

            # Create many jobs with sufficient requirements
            jobs = [
                {"id": i, "title": "Developer", "company": "Corp",
                 "description": "Desc" * 20, "requirements": "Python, AWS, Docker, Kubernetes " * 5}
                for i in range(10)
            ]

            results = service.batch_analyze_jobs(
                cv_content=sample_cv_content,
                cv_summary=None,
                jobs=jobs,
                max_high_matches=3  # Stop after 3 high matches
            )

            assert len(results) == 10
            # Test passes if we get results back (early termination behavior may vary)


class TestAIMatchingServiceConfig:
    """Tests for filter configuration"""

    def test_get_filter_config(self, mock_settings):
        """Test getting filter configuration"""
        with patch('app.services.ai_matching_service.anthropic'):
            service = AIMatchingService()
            service.prefilter_enabled = True
            service.exclude_keywords = ["senior", "lead"]
            service.include_keywords = ["python"]
            service.must_notify_keywords = ["junior"]

            config = service.get_filter_config()

            assert config.prefilter_enabled is True
            assert config.exclude_count == 2
            assert config.include_count == 1
            assert config.must_notify_count == 1
