"""AI-powered job matching service using Anthropic Claude API"""
import json
import re
from typing import Optional, Dict, Any, List, Tuple
import anthropic
from app.config import get_settings

settings = get_settings()


class AIMatchingService:
    """Service for AI-powered CV-to-job matching using Claude"""

    def __init__(self):
        self.client = None
        if settings.anthropic_api_key:
            self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            self.model_name = 'claude-3-5-haiku-20241022'  # Fast and cost-effective

        # Pre-filtering settings
        self.prefilter_enabled = settings.job_prefilter_enabled
        self.exclude_keywords = settings.get_exclude_keywords()
        self.include_keywords = settings.get_include_keywords()
        self.must_notify_keywords = settings.get_must_notify_keywords()

        # CV skills cache (for smart truncation)
        self._cv_skills_cache = {}

        # Tech keywords for keyword-based pre-screening
        self.tech_keywords = {
            # Programming languages
            'python', 'java', 'javascript', 'typescript', 'golang', 'rust', 'scala',
            'ruby', 'php', 'swift', 'kotlin', 'csharp', 'c#', 'cpp', 'c++',
            # Frontend
            'react', 'angular', 'vue', 'nextjs', 'svelte', 'html', 'css', 'sass',
            # Backend
            'node', 'nodejs', 'django', 'flask', 'fastapi', 'spring', 'express', 'rails',
            # Databases
            'sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'dynamodb', 'cassandra', 'neo4j',
            # Cloud & DevOps
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins',
            'cicd', 'ci/cd', 'devops', 'linux', 'nginx', 'ansible',
            # Data & ML
            'machine', 'learning', 'tensorflow', 'pytorch', 'pandas', 'numpy',
            'spark', 'kafka', 'airflow', 'databricks', 'snowflake',
            # Concepts
            'microservices', 'api', 'rest', 'graphql', 'grpc', 'websocket',
            'agile', 'scrum', 'testing', 'security', 'architecture',
        }

    def is_configured(self) -> bool:
        """Check if Anthropic API is configured"""
        return self.client is not None and bool(settings.anthropic_api_key)

    def check_must_notify(self, job_title: str) -> Tuple[bool, Optional[str]]:
        """
        Check if job title contains must-notify keywords.

        Returns:
            Tuple of (must_notify, matched_keyword)
            - must_notify: True if job should always trigger notification
            - matched_keyword: The keyword that triggered the flag, or None
        """
        if not self.must_notify_keywords:
            return False, None

        title_lower = job_title.lower()
        for keyword in self.must_notify_keywords:
            if keyword in title_lower:
                return True, keyword
        return False, None

    def extract_cv_skills(self, cv_content: str) -> Dict[str, Any]:
        """
        Extract key skills from CV for smart truncation.
        Caches results to avoid re-extraction.
        """
        # Check cache
        cv_hash = hash(cv_content[:1000])  # Hash first 1000 chars as key
        if cv_hash in self._cv_skills_cache:
            return self._cv_skills_cache[cv_hash]

        cv_lower = cv_content.lower()

        # Extract technical skills
        found_skills = []
        for skill in self.tech_keywords:
            if skill in cv_lower:
                found_skills.append(skill)

        # Extract years of experience
        years_match = re.search(r'(\d+)\+?\s*years?\s+(?:of\s+)?experience', cv_lower)
        years_experience = int(years_match.group(1)) if years_match else None

        # Extract recent roles (look for job titles in experience section)
        roles = re.findall(r'(?:^|\n)([A-Z][^\n]{20,80}?(?:engineer|developer|analyst|architect|manager))',
                          cv_content, re.IGNORECASE)
        recent_roles = roles[:3] if roles else []

        result = {
            "skills": found_skills,
            "years_experience": years_experience,
            "recent_roles": recent_roles,
            "skill_count": len(found_skills)
        }

        # Cache result
        self._cv_skills_cache[cv_hash] = result
        return result

    def extract_experience_level(self, job_title: str, job_description: str) -> Optional[str]:
        """
        Extract experience level from job posting.
        Returns: 'intern', 'junior', 'entry', 'mid', 'senior', 'lead', 'principal', or None
        """
        combined_text = f"{job_title} {job_description}".lower()

        # Check for explicit level keywords
        if re.search(r'\b(intern|internship)\b', combined_text):
            return 'intern'
        if re.search(r'\b(junior|jr\.?)\b', combined_text):
            return 'junior'
        if re.search(r'\b(entry[\s-]?level|graduate|new grad)\b', combined_text):
            return 'entry'
        if re.search(r'\b(senior|sr\.?)\b', combined_text):
            return 'senior'
        if re.search(r'\b(lead|tech lead|team lead)\b', combined_text):
            return 'lead'
        if re.search(r'\b(principal|staff|architect)\b', combined_text):
            return 'principal'

        # Check years of experience
        years_match = re.search(r'(\d+)\+?\s*years?\s+(?:of\s+)?experience', combined_text)
        if years_match:
            years = int(years_match.group(1))
            if years <= 2:
                return 'entry'
            elif years <= 5:
                return 'mid'
            elif years <= 8:
                return 'senior'
            else:
                return 'lead'

        return None  # Experience level not specified

    def check_experience_match(self, cv_skills: Dict[str, Any], job_level: Optional[str]) -> bool:
        """
        Check if CV experience matches job requirements.
        Returns True if match is acceptable, False if should filter out.
        """
        if not job_level:
            return True  # No experience requirement specified, allow

        cv_years = cv_skills.get("years_experience")
        if not cv_years:
            return True  # Can't determine CV experience, allow

        # Experience level progression matching
        # Allow applying to same level or one level up, but not more
        level_hierarchy = {
            'intern': 0,
            'junior': 1,
            'entry': 1,
            'mid': 2,
            'senior': 3,
            'lead': 4,
            'principal': 5
        }

        # Determine CV level from years
        if cv_years <= 2:
            cv_level = 'entry'
        elif cv_years <= 5:
            cv_level = 'mid'
        elif cv_years <= 8:
            cv_level = 'senior'
        else:
            cv_level = 'lead'

        cv_level_num = level_hierarchy.get(cv_level, 2)
        job_level_num = level_hierarchy.get(job_level, 2)

        # Allow if CV level is within 1 level below or at/above job level
        # e.g., mid-level can apply to mid or senior, but not lead/principal
        return cv_level_num >= job_level_num - 1

    def keyword_based_prescreening(
        self,
        cv_skills: Dict[str, Any],
        job_requirements: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Quick keyword-based screening BEFORE AI analysis.
        Returns (should_analyze, prescreen_result)
        """
        job_lower = job_requirements.lower()

        # Extract required skills from job
        job_words = set(re.findall(r'\b[a-z#+-]{2,}\b', job_lower))
        job_tech_skills = job_words & self.tech_keywords

        # Get CV skills
        cv_tech_skills = set(cv_skills["skills"])

        # Calculate match
        if not job_tech_skills:
            return True, None  # No clear tech requirements, send to AI

        matching = job_tech_skills & cv_tech_skills
        match_percentage = (len(matching) / len(job_tech_skills)) * 100

        # If less than 30% match, auto-reject (too many missing skills)
        if match_percentage < 30:
            missing_skills = list(job_tech_skills - cv_tech_skills)[:10]
            return False, {
                "score": "low",
                "compatibility_percentage": int(match_percentage),
                "matching_skills": list(matching)[:10],
                "missing_requirements": missing_skills,
                "needs_summary_change": False,
                "suggested_summary": None,
                "analysis_reasoning": f"Keyword pre-screening: Only {int(match_percentage)}% skill match. Missing critical skills: {', '.join(missing_skills[:3])}",
                "prefiltered": True,
                "prefilter_reason": "insufficient_skills",
                "must_notify": False
            }

        # Good enough match, send to AI for detailed analysis
        return True, None

    def prefilter_job(self, job_title: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Pre-filter job based on title keywords to save AI API calls.

        Returns:
            Tuple of (should_analyze, prefilter_result)
            - should_analyze: True if job should be sent to AI, False if pre-filtered
            - prefilter_result: If pre-filtered, contains the result dict; None if should analyze
        """
        if not self.prefilter_enabled:
            return True, None

        title_lower = job_title.lower()

        # Check exclude keywords - if found, auto-reject
        for keyword in self.exclude_keywords:
            if keyword in title_lower:
                return False, {
                    "score": "low",
                    "compatibility_percentage": 0,
                    "matching_skills": [],
                    "missing_requirements": [f"Job title contains excluded keyword: '{keyword}'"],
                    "needs_summary_change": False,
                    "suggested_summary": None,
                    "analysis_reasoning": f"Auto-filtered: Job title '{job_title}' contains excluded keyword '{keyword}'",
                    "prefiltered": True,
                    "prefilter_reason": "excluded_keyword",
                    "matched_keyword": keyword,
                    "must_notify": False
                }

        # If include keywords are specified, job must match at least one
        if self.include_keywords:
            matched = False
            for keyword in self.include_keywords:
                if keyword in title_lower:
                    matched = True
                    break
            if not matched:
                return False, {
                    "score": "low",
                    "compatibility_percentage": 0,
                    "matching_skills": [],
                    "missing_requirements": ["Job title does not match required keywords"],
                    "needs_summary_change": False,
                    "suggested_summary": None,
                    "analysis_reasoning": f"Auto-filtered: Job title '{job_title}' does not contain any required keywords",
                    "prefiltered": True,
                    "prefilter_reason": "missing_include_keyword",
                    "must_notify": False
                }

        # Job passed pre-filter, should be analyzed
        return True, None

    def analyze_job_match(
        self,
        cv_content: str,
        cv_summary: Optional[str],
        job_title: str,
        job_company: str,
        job_description: str,
        job_requirements: Optional[str] = None,
        job_location: Optional[str] = None,
        skip_prefilter: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze how well a CV matches a job posting using Claude AI.

        NEW PIPELINE ORDER:
        1. Must-notify check
        2. Title-based pre-filter
        3. Skip if no requirements
        4. Extract CV skills (smart truncation)
        5. Experience level matching
        6. Keyword-based pre-screening (Tier 3 before Tier 2!)
        7. AI analysis (if passed all filters)

        Args:
            skip_prefilter: If True, skip pre-filtering and always analyze

        Returns:
            dict with keys:
            - score: "high", "medium", or "low"
            - compatibility_percentage: int 0-100
            - missing_requirements: list of strings
            - needs_summary_change: bool
            - suggested_summary: str or None
            - analysis_reasoning: str (brief explanation)
            - prefiltered: bool (True if job was pre-filtered without AI)
        """
        # STEP 1: Check for must-notify keywords first
        must_notify, notify_keyword = self.check_must_notify(job_title)

        # STEP 2: Apply title-based pre-filter
        if not skip_prefilter:
            should_analyze, prefilter_result = self.prefilter_job(job_title)
            if not should_analyze:
                # Add must_notify flag to prefiltered results
                if prefilter_result:
                    prefilter_result["must_notify"] = must_notify
                    if must_notify:
                        prefilter_result["must_notify_keyword"] = notify_keyword
                print(f"  ⏭️  Title filtered: {job_title} - {prefilter_result.get('prefilter_reason')}")
                return prefilter_result

        # STEP 3: Skip jobs without requirements (NEW!)
        if not job_requirements or len(job_requirements.strip()) < 50:
            return {
                "score": "low",
                "compatibility_percentage": 0,
                "matching_skills": [],
                "missing_requirements": ["Job has no clear requirements specified"],
                "needs_summary_change": False,
                "suggested_summary": None,
                "analysis_reasoning": "Skipped: Job posting lacks detailed requirements for proper matching",
                "prefiltered": True,
                "prefilter_reason": "no_requirements",
                "must_notify": must_notify,
                "must_notify_keyword": notify_keyword if must_notify else None
            }

        # STEP 4: Extract CV skills for smart analysis (NEW!)
        cv_skills = self.extract_cv_skills(cv_content)

        # STEP 5: Check experience level match (NEW!)
        if not skip_prefilter:
            job_level = self.extract_experience_level(job_title, job_description)
            if not self.check_experience_match(cv_skills, job_level):
                return {
                    "score": "low",
                    "compatibility_percentage": 0,
                    "matching_skills": [],
                    "missing_requirements": [f"Experience level mismatch: Job requires {job_level} level"],
                    "needs_summary_change": False,
                    "suggested_summary": None,
                    "analysis_reasoning": f"Experience level filtering: Job requires {job_level}, candidate has ~{cv_skills.get('years_experience', 'unknown')} years",
                    "prefiltered": True,
                    "prefilter_reason": "experience_mismatch",
                    "must_notify": must_notify,
                    "must_notify_keyword": notify_keyword if must_notify else None
                }

        # STEP 6: Keyword-based pre-screening BEFORE AI (NEW! - Tier swap)
        if not skip_prefilter:
            should_analyze, prescreen_result = self.keyword_based_prescreening(cv_skills, job_requirements)
            if not should_analyze:
                prescreen_result["must_notify"] = must_notify
                if must_notify:
                    prescreen_result["must_notify_keyword"] = notify_keyword
                print(f"  ⏭️  Keyword filtered: {job_title} - insufficient skill match")
                return prescreen_result

        # STEP 7: AI analysis (only if passed all filters)
        if not self.is_configured():
            fallback = self._fallback_keyword_analysis(
                cv_content, job_title, job_description, job_requirements
            )
            fallback["must_notify"] = must_notify
            if must_notify:
                fallback["must_notify_keyword"] = notify_keyword
            return fallback

        # Build the job context - prioritize requirements over full description
        job_context = f"""
Job Title: {job_title}
Company: {job_company}
Location: {job_location or 'Not specified'}
"""

        # Use requirements if available (more focused), otherwise use description
        if job_requirements:
            job_context += f"""
Requirements:
{job_requirements}
"""
        else:
            job_context += f"""
Job Description:
{job_description[:2000]}
"""

        # Build CV context using SMART TRUNCATION (NEW!)
        # Instead of sending full CV, send extracted skills summary
        skills_str = ", ".join(cv_skills["skills"][:30])  # Top 30 skills
        roles_str = "\n".join([f"- {role}" for role in cv_skills["recent_roles"]])

        cv_context = f"""
Candidate Profile:
- Technical Skills: {skills_str}
- Years of Experience: {cv_skills.get('years_experience', 'Not specified')}
- Recent Roles:
{roles_str if roles_str else '- See CV summary'}
"""
        if cv_summary:
            cv_context += f"""
- Professional Summary: {cv_summary}
"""

        prompt = f"""You are an expert HR analyst and career advisor. Analyze how well this candidate's CV matches the job posting.

{job_context}

---

{cv_context}

---

Provide a detailed analysis in the following JSON format:
{{
    "score": "high|medium|low",
    "compatibility_percentage": <number 0-100>,
    "matching_skills": ["skill1", "skill2", ...],
    "missing_requirements": ["requirement1", "requirement2", ...],
    "needs_summary_change": true|false,
    "suggested_summary": "A 2-3 sentence professional summary tailored for this specific job, or null if no change needed",
    "analysis_reasoning": "Brief 1-2 sentence explanation of the match quality"
}}

Scoring criteria:
- HIGH (70-100%): Strong match - candidate has most required skills and relevant experience
- MEDIUM (40-69%): Partial match - candidate has some required skills but gaps exist
- LOW (0-39%): Weak match - significant skill gaps or experience mismatch

Focus on:
1. Technical skills match (programming languages, frameworks, tools)
2. Experience level alignment
3. Domain/industry relevance
4. Soft skills and cultural fit indicators

Be specific about missing requirements - list actual skills/qualifications from the job posting that aren't evident in the CV.

Respond ONLY with valid JSON, no markdown formatting or additional text."""

        try:
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=2048,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            response_text = message.content[0].text.strip()

            # Try to extract JSON if wrapped in markdown code blocks
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                response_text = json_match.group(1)

            result = json.loads(response_text)

            # Validate and normalize response
            normalized = self._normalize_response(result)
            # Add must_notify flag
            normalized["must_notify"] = must_notify
            if must_notify:
                normalized["must_notify_keyword"] = notify_keyword
            return normalized

        except json.JSONDecodeError as e:
            print(f"Error parsing AI response: {e}")
            fallback = self._fallback_keyword_analysis(
                cv_content, job_title, job_description, job_requirements
            )
            fallback["must_notify"] = must_notify
            if must_notify:
                fallback["must_notify_keyword"] = notify_keyword
            return fallback
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            fallback = self._fallback_keyword_analysis(
                cv_content, job_title, job_description, job_requirements
            )
            fallback["must_notify"] = must_notify
            if must_notify:
                fallback["must_notify_keyword"] = notify_keyword
            return fallback

    def _normalize_response(self, result: Dict) -> Dict[str, Any]:
        """Normalize and validate the AI response"""
        # Ensure score is valid
        score = result.get("score", "medium").lower()
        if score not in ["high", "medium", "low"]:
            score = "medium"

        # Ensure compatibility is in range
        compatibility = result.get("compatibility_percentage", 50)
        if not isinstance(compatibility, (int, float)):
            compatibility = 50
        compatibility = max(0, min(100, int(compatibility)))

        # Ensure lists are lists
        missing = result.get("missing_requirements", [])
        if not isinstance(missing, list):
            missing = []

        matching = result.get("matching_skills", [])
        if not isinstance(matching, list):
            matching = []

        return {
            "score": score,
            "compatibility_percentage": compatibility,
            "matching_skills": matching[:10],  # Limit to 10
            "missing_requirements": missing[:10],  # Limit to 10
            "needs_summary_change": bool(result.get("needs_summary_change", False)),
            "suggested_summary": result.get("suggested_summary"),
            "analysis_reasoning": result.get("analysis_reasoning", ""),
            "prefiltered": False
        }

    def _fallback_keyword_analysis(
        self,
        cv_content: str,
        job_title: str,
        job_description: str,
        job_requirements: Optional[str]
    ) -> Dict[str, Any]:
        """
        Fallback to keyword-based analysis when AI is not available.
        This is a more sophisticated version of the original keyword matching.
        """
        print("Using fallback keyword-based analysis (AI not configured)")

        # Combine job text
        job_text = f"{job_title} {job_description or ''} {job_requirements or ''}".lower()
        cv_text = cv_content.lower()

        # Extract words
        job_words = set(re.findall(r'\b[a-z]{3,}\b', job_text))
        cv_words = set(re.findall(r'\b[a-z]{3,}\b', cv_text))

        # Important tech keywords to look for
        tech_keywords = {
            # Programming languages
            'python', 'java', 'javascript', 'typescript', 'golang', 'rust', 'scala',
            'ruby', 'php', 'swift', 'kotlin', 'csharp', 'cpp',
            # Frontend
            'react', 'angular', 'vue', 'nextjs', 'svelte', 'html', 'css', 'sass',
            # Backend
            'node', 'django', 'flask', 'fastapi', 'spring', 'express', 'rails',
            # Databases
            'sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'dynamodb', 'cassandra', 'neo4j',
            # Cloud & DevOps
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins',
            'cicd', 'devops', 'linux', 'nginx', 'ansible',
            # Data & ML
            'machine', 'learning', 'tensorflow', 'pytorch', 'pandas', 'numpy',
            'spark', 'kafka', 'airflow', 'databricks', 'snowflake',
            # Concepts
            'microservices', 'api', 'rest', 'graphql', 'grpc', 'websocket',
            'agile', 'scrum', 'testing', 'security', 'architecture',
            # Roles
            'backend', 'frontend', 'fullstack', 'engineer', 'developer', 'architect',
            'senior', 'lead', 'manager', 'data', 'devops', 'sre'
        }

        # Find matching and missing keywords
        job_important = job_words & tech_keywords
        cv_important = cv_words & tech_keywords
        matching = job_important & cv_important
        missing = job_important - cv_important

        # Calculate compatibility
        if len(job_important) > 0:
            compatibility = int((len(matching) / len(job_important)) * 100)
        else:
            compatibility = 50

        # Determine score
        if compatibility >= 70:
            score = "high"
        elif compatibility >= 40:
            score = "medium"
        else:
            score = "low"

        return {
            "score": score,
            "compatibility_percentage": compatibility,
            "matching_skills": list(matching)[:10],
            "missing_requirements": list(missing)[:10],
            "needs_summary_change": len(missing) > 3,
            "suggested_summary": None,
            "analysis_reasoning": f"Keyword-based analysis: {len(matching)}/{len(job_important)} key skills matched",
            "prefiltered": False
        }

    def generate_tailored_summary(
        self,
        cv_content: str,
        current_summary: Optional[str],
        job_title: str,
        job_description: str,
        missing_requirements: List[str]
    ) -> Optional[str]:
        """
        Generate a tailored CV summary for a specific job.
        Only call this when needs_summary_change is True.
        """
        if not self.is_configured():
            return None

        prompt = f"""You are a professional resume writer. Create a compelling 2-3 sentence professional summary 
tailored for this specific job application.

Target Job: {job_title}

Job Description Summary:
{job_description[:2000]}

Current CV Summary (if any): {current_summary or 'None provided'}

Candidate's Full CV:
{cv_content[:4000]}

Skills the candidate should emphasize (if they have them):
{', '.join(missing_requirements[:5]) if missing_requirements else 'N/A'}

Write a professional summary that:
1. Highlights the candidate's most relevant experience for this role
2. Uses keywords from the job description naturally
3. Is authentic - only mention skills/experience evident in the CV
4. Is 2-3 sentences, punchy and impactful

Respond with ONLY the summary text, no quotes or additional formatting."""

        try:
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=512,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            summary = message.content[0].text.strip()
            # Remove any quotes that might wrap the summary
            summary = summary.strip('"\'')
            return summary

        except Exception as e:
            print(f"Error generating summary: {e}")
            return None

    def get_filter_config(self) -> Dict[str, Any]:
        """Get current pre-filter configuration"""
        return {
            "prefilter_enabled": self.prefilter_enabled,
            "exclude_keywords": self.exclude_keywords,
            "include_keywords": self.include_keywords,
            "must_notify_keywords": self.must_notify_keywords,
            "exclude_count": len(self.exclude_keywords),
            "include_count": len(self.include_keywords),
            "must_notify_count": len(self.must_notify_keywords)
        }

    def batch_analyze_jobs(
        self,
        cv_content: str,
        cv_summary: Optional[str],
        jobs: List[Dict[str, Any]],
        skip_prefilter: bool = False,
        max_high_matches: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple jobs against a CV with SMART EARLY TERMINATION.

        NEW BEHAVIOR:
        - Stops after finding max_high_matches HIGH-scoring jobs
        - BUT always analyzes must-notify jobs regardless of early stop
        - Returns list of analysis results in same order as input jobs

        Args:
            skip_prefilter: If True, skip pre-filtering for all jobs
            max_high_matches: Stop after N high matches (default: 5)
        """
        results = []
        prefiltered_count = 0
        analyzed_count = 0
        high_match_count = 0
        early_stopped = False

        # First pass: Identify must-notify jobs
        must_notify_indices = []
        for i, job in enumerate(jobs):
            is_must_notify, _ = self.check_must_notify(job.get("title", ""))
            if is_must_notify:
                must_notify_indices.append(i)

        for i, job in enumerate(jobs):
            # Check if we should stop early (unless this is a must-notify job)
            if (high_match_count >= max_high_matches and
                i not in must_notify_indices and
                not early_stopped):
                early_stopped = True
                print(f"  ⏸️  Early stop: Found {high_match_count} high matches, skipping remaining non-priority jobs")

            # Skip if early stopped and not must-notify
            if early_stopped and i not in must_notify_indices:
                result = {
                    "job_id": job.get("id"),
                    "score": "low",
                    "compatibility_percentage": 0,
                    "matching_skills": [],
                    "missing_requirements": [],
                    "needs_summary_change": False,
                    "suggested_summary": None,
                    "analysis_reasoning": "Skipped: Early termination after finding enough high matches",
                    "prefiltered": True,
                    "prefilter_reason": "early_stop",
                    "must_notify": False
                }
                results.append(result)
                prefiltered_count += 1
                continue

            # Analyze the job
            result = self.analyze_job_match(
                cv_content=cv_content,
                cv_summary=cv_summary,
                job_title=job.get("title", ""),
                job_company=job.get("company", ""),
                job_description=job.get("description", ""),
                job_requirements=job.get("requirements"),
                job_location=job.get("location"),
                skip_prefilter=skip_prefilter
            )
            result["job_id"] = job.get("id")
            results.append(result)

            # Track statistics
            if result.get("prefiltered"):
                prefiltered_count += 1
            else:
                analyzed_count += 1
                if result.get("score") == "high":
                    high_match_count += 1

        print(f"  ✅ Batch complete: {analyzed_count} analyzed, {prefiltered_count} pre-filtered, {high_match_count} high matches")
        if must_notify_indices:
            print(f"  🔔 Processed {len(must_notify_indices)} must-notify jobs regardless of early stop")

        return results
