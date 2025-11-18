"""JSearch API integration service for fetching jobs from LinkedIn and other sources"""
import httpx
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from app.config import get_settings

settings = get_settings()


class JSearchService:
    """Service for interacting with JSearch API via RapidAPI"""

    BASE_URL = "https://jsearch.p.rapidapi.com"

    def __init__(self):
        self.api_key = settings.rapidapi_key
        self.api_host = settings.rapidapi_host

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for RapidAPI requests"""
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host,
        }

    async def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        remote_jobs_only: bool = False,
        employment_types: Optional[str] = None,
        job_requirements: Optional[str] = None,
        page: int = 1,
        num_pages: int = 1,
        date_posted: str = "all",
        linkedin_only: bool = True,
    ) -> Dict[str, Any]:
        """
        Search for jobs using JSearch API

        Args:
            query: Search query (e.g., "Software Engineer", "Back End Developer")
            location: Location filter (e.g., "Israel", "Tel Aviv, Israel")
            remote_jobs_only: Filter for remote jobs only
            employment_types: Comma-separated values (FULLTIME, CONTRACTOR, PARTTIME, INTERN)
            job_requirements: Experience level (under_3_years_experience, more_than_3_years_experience, no_experience, no_degree)
            page: Page number (default: 1)
            num_pages: Number of pages to fetch (default: 1)
            date_posted: Filter by date posted (all, today, 3days, week, month)
            linkedin_only: Only search LinkedIn jobs (default: True)

        Returns:
            Dict containing job listings and metadata
        """
        url = f"{self.BASE_URL}/search"

        # Note: JSearch aggregates from multiple sources (LinkedIn, Indeed, Glassdoor, etc.)
        # The API doesn't support filtering by specific sources directly
        # Using site:linkedin.com in query may not work as expected
        search_query = query

        params = {
            "query": search_query,
            "page": str(page),
            "num_pages": str(num_pages),
            "date_posted": date_posted,
        }

        if location:
            params["location"] = location

        if remote_jobs_only:
            params["remote_jobs_only"] = "true"

        if employment_types:
            params["employment_types"] = employment_types

        if job_requirements:
            params["job_requirements"] = job_requirements

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    params=params,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            print(f"Request error occurred: {str(e)}")
            raise
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise

    def parse_job_data(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse JSearch job data into our internal format

        Args:
            job_data: Raw job data from JSearch API

        Returns:
            Dict containing parsed job data ready for database insertion
        """
        # Extract job details
        job_id = job_data.get("job_id", "")
        title = job_data.get("job_title", "")
        company = job_data.get("employer_name", "Unknown Company")
        location = job_data.get("job_city", "")

        # Add state/country if available
        if job_data.get("job_state"):
            location = f"{location}, {job_data.get('job_state')}"
        if job_data.get("job_country"):
            location = f"{location}, {job_data.get('job_country')}" if location else job_data.get("job_country")

        # Job type and experience level
        job_type = None
        employment_type = job_data.get("job_employment_type", "")
        if employment_type:
            job_type_map = {
                "FULLTIME": "full-time",
                "PARTTIME": "part-time",
                "CONTRACTOR": "contract",
                "INTERN": "internship",
            }
            job_type = job_type_map.get(employment_type, employment_type.lower())

        experience_level = None
        if job_data.get("job_required_experience"):
            exp_data = job_data.get("job_required_experience", {})
            if exp_data.get("required_experience_in_months"):
                months = exp_data.get("required_experience_in_months", 0)
                if months < 12:
                    experience_level = "entry"
                elif months < 60:
                    experience_level = "mid"
                else:
                    experience_level = "senior"

        # Description and requirements
        description = job_data.get("job_description", "")

        # Try to extract requirements (JSearch sometimes provides highlights)
        requirements_parts = []
        if job_data.get("job_highlights"):
            highlights = job_data.get("job_highlights", {})
            if highlights.get("Qualifications"):
                requirements_parts.extend(highlights.get("Qualifications", []))
            if highlights.get("Responsibilities"):
                requirements_parts.extend(highlights.get("Responsibilities", []))

        requirements = "\n".join(requirements_parts) if requirements_parts else None

        # URL
        url = job_data.get("job_apply_link") or job_data.get("job_google_link", "")

        # Salary
        salary_range = None
        if job_data.get("job_min_salary") or job_data.get("job_max_salary"):
            min_sal = job_data.get("job_min_salary", "")
            max_sal = job_data.get("job_max_salary", "")
            currency = job_data.get("job_salary_currency", "USD")
            period = job_data.get("job_salary_period", "YEAR")

            if min_sal and max_sal:
                salary_range = f"{currency} {min_sal:,.0f} - {max_sal:,.0f} per {period.lower()}"
            elif min_sal:
                salary_range = f"{currency} {min_sal:,.0f}+ per {period.lower()}"
            elif max_sal:
                salary_range = f"Up to {currency} {max_sal:,.0f} per {period.lower()}"

        # Posted date
        posted_at = None
        if job_data.get("job_posted_at_timestamp"):
            posted_at = datetime.fromtimestamp(job_data.get("job_posted_at_timestamp"))
        elif job_data.get("job_posted_at_datetime_utc"):
            try:
                posted_at = datetime.fromisoformat(
                    job_data.get("job_posted_at_datetime_utc").replace("Z", "+00:00")
                )
            except:
                pass

        return {
            "external_job_id": job_id,
            "title": title,
            "company": company,
            "location": location or None,
            "job_type": job_type,
            "experience_level": experience_level,
            "description": description,
            "requirements": requirements,
            "url": url,
            "salary_range": salary_range,
            "posted_at": posted_at,
            "fetched_at": datetime.now(timezone.utc),
        }

    async def fetch_jobs_by_filter(
        self,
        filter_config: Dict[str, Any],
        max_pages: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch jobs based on a search filter configuration

        Args:
            filter_config: Search filter configuration with keywords, location, etc.
            max_pages: Maximum number of pages to fetch (default: from settings, max recommended: 3)

        Returns:
            List of parsed job data dictionaries
        """
        # Use config default if not specified
        if max_pages is None:
            max_pages = settings.search_max_pages

        # Build query from keywords
        keywords = filter_config.get("keywords", [])
        if not keywords:
            return []

        # FIX: Use OR operator to search for multiple job titles
        # Instead of "Software Engineer Back End Developer Data Analyst"
        # Use: "Software Engineer" OR "Back End Developer" OR "Data Analyst"
        if len(keywords) > 1:
            query = " OR ".join(f'"{keyword}"' for keyword in keywords)
        else:
            query = keywords[0]

        location = filter_config.get("location")
        remote = filter_config.get("remote", False)

        # Map job type to JSearch format
        job_type = filter_config.get("job_type")
        employment_types = None
        if job_type:
            type_map = {
                "full-time": "FULLTIME",
                "part-time": "PARTTIME",
                "contract": "CONTRACTOR",
                "internship": "INTERN",
            }
            employment_types = type_map.get(job_type.lower())

        # Map experience level
        experience = filter_config.get("experience_level")
        job_requirements = None
        if experience:
            exp_map = {
                "entry": "under_3_years_experience",
                "mid": "more_than_3_years_experience",
                "senior": "more_than_3_years_experience",
            }
            job_requirements = exp_map.get(experience.lower())

        # Search jobs
        try:
            results = await self.search_jobs(
                query=query,
                location=location,
                remote_jobs_only=remote,
                employment_types=employment_types,
                job_requirements=job_requirements,
                num_pages=max_pages,
                date_posted="week",  # Only get jobs from the last week
                linkedin_only=settings.search_linkedin_only,
            )

            # Parse results
            jobs = results.get("data", [])
            parsed_jobs = [self.parse_job_data(job) for job in jobs]

            return parsed_jobs

        except Exception as e:
            print(f"Error fetching jobs for filter: {str(e)}")
            return []

