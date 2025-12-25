"""Unit tests for JSearch Service"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from app.services.jsearch_service import JSearchService


class TestJSearchService:
    """Tests for JSearchService class"""

    def test_init(self, mock_settings):
        """Test service initialization"""
        with patch('app.services.jsearch_service.settings', mock_settings):
            service = JSearchService()
            assert service.api_key == mock_settings.rapidapi_key
            assert service.api_host == mock_settings.rapidapi_host

    def test_get_headers(self, mock_settings):
        """Test API headers generation"""
        with patch('app.services.jsearch_service.settings', mock_settings):
            service = JSearchService()
            headers = service._get_headers()

            assert "X-RapidAPI-Key" in headers
            assert "X-RapidAPI-Host" in headers
            assert headers["X-RapidAPI-Key"] == mock_settings.rapidapi_key


class TestJSearchServiceSearch:
    """Tests for job search functionality"""

    @pytest.mark.asyncio
    async def test_search_jobs_basic(self, mock_settings, jsearch_api_response):
        """Test basic job search"""
        service = JSearchService()

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = jsearch_api_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            async with httpx.AsyncClient() as client:
                result = await service.search_jobs(query="Python Developer")

            assert result is not None

    @pytest.mark.asyncio
    async def test_search_jobs_with_location(self, mock_settings):
        """Test job search with location filter"""
        service = JSearchService()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": []}
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await service.search_jobs(
                query="Software Engineer",
                location="San Francisco, CA"
            )

            mock_client.get.assert_called_once()
            call_kwargs = mock_client.get.call_args
            assert "location" in call_kwargs.kwargs.get("params", {})

    @pytest.mark.asyncio
    async def test_search_jobs_remote_only(self, mock_settings):
        """Test job search with remote filter"""
        service = JSearchService()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": []}
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await service.search_jobs(
                query="Developer",
                remote_jobs_only=True
            )

            call_kwargs = mock_client.get.call_args
            params = call_kwargs.kwargs.get("params", {})
            assert params.get("remote_jobs_only") == "true"

    @pytest.mark.asyncio
    async def test_search_jobs_http_error(self, mock_settings):
        """Test handling of HTTP errors"""
        service = JSearchService()

        # Create a proper mock response for httpx
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"

        # Create the HTTPStatusError with proper arguments
        http_error = httpx.HTTPStatusError(
            message="Rate limit exceeded",
            request=mock_request,
            response=mock_response
        )
        mock_response.raise_for_status.side_effect = http_error

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__.return_value = None

            with pytest.raises(httpx.HTTPStatusError):
                await service.search_jobs(query="Developer")


class TestJSearchServiceParseJobData:
    """Tests for job data parsing"""

    def test_parse_job_data_full(self, mock_settings):
        """Test parsing complete job data"""
        service = JSearchService()
        raw_data = {
            "job_id": "test_job_123",
            "job_title": "Senior Python Developer",
            "employer_name": "Tech Corp",
            "job_city": "Austin",
            "job_state": "TX",
            "job_country": "US",
            "job_employment_type": "FULLTIME",
            "job_description": "We are looking for a Python developer...",
            "job_highlights": {
                "Qualifications": ["5+ years Python", "Django experience"],
                "Responsibilities": ["Build APIs", "Write tests"]
            },
            "job_apply_link": "https://example.com/apply",
            "job_min_salary": 100000,
            "job_max_salary": 150000,
            "job_salary_currency": "USD",
            "job_salary_period": "YEAR",
            "job_posted_at_timestamp": 1700000000
        }

        result = service.parse_job_data(raw_data)

        assert result.external_job_id == "test_job_123"
        assert result.title == "Senior Python Developer"
        assert result.company == "Tech Corp"
        assert result.location == "Austin, TX, US"
        assert result.job_type == "full-time"
        assert result.url == "https://example.com/apply"
        assert "100,000" in result.salary_range
        assert "150,000" in result.salary_range
        assert result.requirements is not None
        assert "5+ years Python" in result.requirements

    def test_parse_job_data_minimal(self, mock_settings):
        """Test parsing minimal job data"""
        service = JSearchService()
        raw_data = {
            "job_id": "minimal_job",
            "job_title": "Developer",
            "employer_name": "Company",
            "job_description": "Job description here"
        }

        result = service.parse_job_data(raw_data)

        assert result.external_job_id == "minimal_job"
        assert result.title == "Developer"
        assert result.company == "Company"
        assert result.location is None or result.location == ""
        assert result.salary_range is None

    def test_parse_job_data_employment_types(self, mock_settings):
        """Test parsing different employment types"""
        service = JSearchService()

        test_cases = [
            ("FULLTIME", "full-time"),
            ("PARTTIME", "part-time"),
            ("CONTRACTOR", "contract"),
            ("INTERN", "internship"),
        ]

        for input_type, expected_type in test_cases:
            raw_data = {
                "job_id": f"job_{input_type}",
                "job_title": "Developer",
                "employer_name": "Company",
                "job_description": "Description",
                "job_employment_type": input_type
            }
            result = service.parse_job_data(raw_data)
            assert result.job_type == expected_type

    def test_parse_job_data_experience_level(self, mock_settings):
        """Test parsing experience level from months"""
        service = JSearchService()

        test_cases = [
            (6, "entry"),   # Less than 12 months
            (24, "mid"),    # 12-60 months
            (72, "senior"), # More than 60 months
        ]

        for months, expected_level in test_cases:
            raw_data = {
                "job_id": f"job_{months}",
                "job_title": "Developer",
                "employer_name": "Company",
                "job_description": "Description",
                "job_required_experience": {
                    "required_experience_in_months": months
                }
            }
            result = service.parse_job_data(raw_data)
            assert result.experience_level == expected_level

    def test_parse_job_data_salary_formats(self, mock_settings):
        """Test parsing different salary formats"""
        service = JSearchService()

        # Min and max salary
        raw_data = {
            "job_id": "job_1",
            "job_title": "Dev",
            "employer_name": "Co",
            "job_description": "Desc",
            "job_min_salary": 80000,
            "job_max_salary": 120000,
            "job_salary_currency": "USD",
            "job_salary_period": "YEAR"
        }
        result = service.parse_job_data(raw_data)
        assert "80,000" in result.salary_range
        assert "120,000" in result.salary_range

        # Only min salary
        raw_data["job_min_salary"] = 90000
        raw_data["job_max_salary"] = None
        result = service.parse_job_data(raw_data)
        assert "90,000+" in result.salary_range

        # Only max salary
        raw_data["job_min_salary"] = None
        raw_data["job_max_salary"] = 100000
        result = service.parse_job_data(raw_data)
        assert "Up to" in result.salary_range

    def test_parse_job_data_posted_date(self, mock_settings):
        """Test parsing posted date from different formats"""
        service = JSearchService()

        # From timestamp
        raw_data = {
            "job_id": "job_1",
            "job_title": "Dev",
            "employer_name": "Co",
            "job_description": "Desc",
            "job_posted_at_timestamp": 1700000000
        }
        result = service.parse_job_data(raw_data)
        assert result.posted_at is not None
        assert isinstance(result.posted_at, datetime)

        # From ISO datetime
        raw_data = {
            "job_id": "job_2",
            "job_title": "Dev",
            "employer_name": "Co",
            "job_description": "Desc",
            "job_posted_at_datetime_utc": "2024-01-15T10:00:00Z"
        }
        result = service.parse_job_data(raw_data)
        assert result.posted_at is not None


class TestJSearchServiceFetchByFilter:
    """Tests for fetch_jobs_by_filter functionality"""

    @pytest.mark.asyncio
    async def test_fetch_jobs_by_filter_basic(self, mock_settings, jsearch_api_response):
        """Test fetching jobs by filter configuration"""
        service = JSearchService()

        filter_config = {
            "keywords": ["Python Developer"],
            "location": "United States",
            "remote": True
        }

        with patch.object(service, 'search_jobs', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = jsearch_api_response
            result = await service.fetch_jobs_by_filter(filter_config)

            assert len(result) == 2
            mock_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_jobs_by_filter_multiple_keywords(self, mock_settings):
        """Test query building with multiple keywords"""
        service = JSearchService()

        filter_config = {
            "keywords": ["Python Developer", "Backend Engineer", "Data Engineer"],
            "location": "Remote"
        }

        with patch.object(service, 'search_jobs', new_callable=AsyncMock) as mock_search:
            from app.schemas import JSearchAPIResponse
            mock_search.return_value = JSearchAPIResponse(status="OK", data=[])
            await service.fetch_jobs_by_filter(filter_config)

            call_args = mock_search.call_args
            query = call_args.kwargs.get("query", "") or call_args.args[0]
            # Should use OR operator for multiple keywords
            assert "OR" in query

    @pytest.mark.asyncio
    async def test_fetch_jobs_by_filter_empty_keywords(self, mock_settings):
        """Test handling of empty keywords"""
        service = JSearchService()

        filter_config = {
            "keywords": [],
            "location": "United States"
        }

        result = await service.fetch_jobs_by_filter(filter_config)
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_jobs_by_filter_job_type_mapping(self, mock_settings):
        """Test job type mapping to JSearch format"""
        service = JSearchService()

        type_mappings = [
            ("full-time", "FULLTIME"),
            ("part-time", "PARTTIME"),
            ("contract", "CONTRACTOR"),
            ("internship", "INTERN"),
        ]

        for input_type, expected_type in type_mappings:
            filter_config = {
                "keywords": ["Developer"],
                "job_type": input_type
            }

            with patch.object(service, 'search_jobs', new_callable=AsyncMock) as mock_search:
                from app.schemas import JSearchAPIResponse
                mock_search.return_value = JSearchAPIResponse(status="OK", data=[])
                await service.fetch_jobs_by_filter(filter_config)

                call_kwargs = mock_search.call_args.kwargs
                assert call_kwargs.get("employment_types") == expected_type

    @pytest.mark.asyncio
    async def test_fetch_jobs_by_filter_error_handling(self, mock_settings):
        """Test error handling in fetch_jobs_by_filter"""
        service = JSearchService()

        filter_config = {
            "keywords": ["Developer"]
        }

        with patch.object(service, 'search_jobs', new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = Exception("API Error")
            result = await service.fetch_jobs_by_filter(filter_config)

            assert result == []


class TestJSearchServiceEdgeCases:
    """Edge case tests for JSearch Service"""

    def test_parse_job_data_missing_employer(self, mock_settings):
        """Test parsing job with missing employer name"""
        service = JSearchService()
        raw_data = {
            "job_id": "job_no_employer",
            "job_title": "Developer",
            "job_description": "Description"
        }

        result = service.parse_job_data(raw_data)
        assert result.company == "Unknown Company"

    def test_parse_job_data_fallback_url(self, mock_settings):
        """Test URL fallback to Google link"""
        service = JSearchService()
        raw_data = {
            "job_id": "job_google_link",
            "job_title": "Developer",
            "employer_name": "Company",
            "job_description": "Description",
            "job_google_link": "https://google.com/jobs/123"
        }

        result = service.parse_job_data(raw_data)
        assert result.url == "https://google.com/jobs/123"

    def test_parse_job_data_requirements_from_highlights(self, mock_settings):
        """Test requirements extraction from highlights"""
        service = JSearchService()
        raw_data = {
            "job_id": "job_highlights",
            "job_title": "Developer",
            "employer_name": "Company",
            "job_description": "Description",
            "job_highlights": {
                "Qualifications": ["Req 1", "Req 2"],
                "Responsibilities": ["Resp 1", "Resp 2"]
            }
        }

        result = service.parse_job_data(raw_data)
        assert result.requirements is not None
        assert "Req 1" in result.requirements
        assert "Resp 1" in result.requirements
