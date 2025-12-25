"""Unit tests for Configuration"""
import pytest
from unittest.mock import patch, MagicMock
import os


class TestSettings:
    """Tests for Settings class"""

    def test_settings_required_fields(self):
        """Test that required settings fields are present"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379/0'
        }):
            from app.config import Settings
            settings = Settings()

            # Check that required fields exist
            assert hasattr(settings, 'database_url')
            assert hasattr(settings, 'redis_url')
            assert hasattr(settings, 'app_name')
            assert hasattr(settings, 'smtp_host')
            assert hasattr(settings, 'fetch_interval_minutes')
            assert hasattr(settings, 'job_prefilter_enabled')

            # Check app name default
            assert settings.app_name == "Job Matcher"

    def test_settings_from_env(self):
        """Test settings loaded from environment variables"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://user:pass@host:5432/db',
            'REDIS_URL': 'redis://redis:6379/1',
            'ANTHROPIC_API_KEY': 'sk-ant-test-key',
            'RAPIDAPI_KEY': 'rapid-test-key',
            'SMTP_USER': 'test@example.com',
            'SMTP_PASS': 'testpassword',
            'NOTIFICATION_EMAIL': 'notify@example.com'
        }):
            from app.config import Settings
            settings = Settings()

            assert settings.database_url == 'postgresql://user:pass@host:5432/db'
            assert settings.redis_url == 'redis://redis:6379/1'
            assert settings.anthropic_api_key == 'sk-ant-test-key'
            assert settings.rapidapi_key == 'rapid-test-key'


class TestSettingsKeywordParsing:
    """Tests for keyword parsing methods"""

    def test_get_exclude_keywords(self):
        """Test parsing exclude keywords"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379/0',
            'JOB_TITLE_EXCLUDE_KEYWORDS': 'senior, lead, architect, manager'
        }):
            from app.config import Settings
            settings = Settings()
            keywords = settings.get_exclude_keywords()

            assert isinstance(keywords, list)
            assert 'senior' in keywords
            assert 'lead' in keywords
            assert 'architect' in keywords
            assert 'manager' in keywords
            # Check lowercase
            assert all(k == k.lower() for k in keywords)

    def test_get_exclude_keywords_empty(self):
        """Test parsing empty exclude keywords"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379/0',
            'JOB_TITLE_EXCLUDE_KEYWORDS': ''
        }):
            from app.config import Settings
            settings = Settings()
            keywords = settings.get_exclude_keywords()

            assert keywords == []

    def test_get_include_keywords(self):
        """Test parsing include keywords"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379/0',
            'JOB_TITLE_INCLUDE_KEYWORDS': 'python, javascript, react'
        }):
            from app.config import Settings
            settings = Settings()
            keywords = settings.get_include_keywords()

            assert 'python' in keywords
            assert 'javascript' in keywords
            assert 'react' in keywords

    def test_get_include_keywords_empty(self):
        """Test parsing empty include keywords"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379/0',
            'JOB_TITLE_INCLUDE_KEYWORDS': ''
        }):
            from app.config import Settings
            settings = Settings()
            keywords = settings.get_include_keywords()

            assert keywords == []

    def test_get_must_notify_keywords(self):
        """Test parsing must-notify keywords"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379/0',
            'JOB_TITLE_MUST_NOTIFY_KEYWORDS': 'junior, entry-level, intern, graduate'
        }):
            from app.config import Settings
            settings = Settings()
            keywords = settings.get_must_notify_keywords()

            assert 'junior' in keywords
            assert 'entry-level' in keywords
            assert 'intern' in keywords
            assert 'graduate' in keywords

    def test_get_must_notify_keywords_empty(self):
        """Test parsing empty must-notify keywords"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379/0',
            'JOB_TITLE_MUST_NOTIFY_KEYWORDS': ''
        }):
            from app.config import Settings
            settings = Settings()
            keywords = settings.get_must_notify_keywords()

            assert keywords == []

    def test_keyword_parsing_strips_whitespace(self):
        """Test that keywords are stripped of whitespace"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379/0',
            'JOB_TITLE_EXCLUDE_KEYWORDS': '  senior  ,  lead  ,  architect  '
        }):
            from app.config import Settings
            settings = Settings()
            keywords = settings.get_exclude_keywords()

            assert 'senior' in keywords
            assert '  senior  ' not in keywords
            assert all(k == k.strip() for k in keywords)

    def test_keyword_parsing_handles_empty_items(self):
        """Test that empty items between commas are filtered"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379/0',
            'JOB_TITLE_EXCLUDE_KEYWORDS': 'senior,,lead,,,architect'
        }):
            from app.config import Settings
            settings = Settings()
            keywords = settings.get_exclude_keywords()

            assert '' not in keywords
            assert len(keywords) == 3


class TestGetSettings:
    """Tests for get_settings function"""

    def test_get_settings_returns_settings(self):
        """Test that get_settings returns a Settings instance"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379/0'
        }):
            from app.config import get_settings, Settings
            # Clear cache
            get_settings.cache_clear()

            result = get_settings()
            assert isinstance(result, Settings)

    def test_get_settings_cached(self):
        """Test that get_settings returns cached instance"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379/0'
        }):
            from app.config import get_settings
            # Clear cache
            get_settings.cache_clear()

            settings1 = get_settings()
            settings2 = get_settings()

            # Should be the same object due to caching
            assert settings1 is settings2


class TestSettingsSearchDefaults:
    """Tests for search-related default settings"""

    def test_search_fields_exist(self):
        """Test search settings fields exist"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379/0'
        }):
            from app.config import Settings
            settings = Settings()

            # Check that search-related fields exist
            assert hasattr(settings, 'search_location')
            assert hasattr(settings, 'search_remote_only')
            assert hasattr(settings, 'search_date_posted')
            assert hasattr(settings, 'search_max_pages')

    def test_search_keywords_default(self):
        """Test default search keywords"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379/0'
        }):
            from app.config import Settings
            settings = Settings()

            assert "Software Engineer" in settings.search_keywords
            assert "Backend Developer" in settings.search_keywords


class TestSettingsStorage:
    """Tests for storage path settings"""

    def test_storage_paths(self):
        """Test default storage paths"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379/0'
        }):
            from app.config import Settings
            settings = Settings()

            assert settings.storage_path == "./storage"
            assert settings.cv_storage_path == "./storage/cvs"
            assert settings.temp_storage_path == "./storage/temp"

    def test_custom_storage_paths(self):
        """Test custom storage paths from environment"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379/0',
            'STORAGE_PATH': '/data/storage',
            'CV_STORAGE_PATH': '/data/storage/cvs',
            'TEMP_STORAGE_PATH': '/data/storage/temp'
        }):
            from app.config import Settings
            settings = Settings()

            assert settings.storage_path == '/data/storage'
            assert settings.cv_storage_path == '/data/storage/cvs'
            assert settings.temp_storage_path == '/data/storage/temp'


class TestSettingsEdgeCases:
    """Edge case tests for Settings"""

    def test_settings_case_insensitive(self):
        """Test that environment variables are case-insensitive"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'redis_url': 'redis://localhost:6379/0',
            'Anthropic_Api_Key': 'test-key'
        }, clear=False):
            from app.config import Settings
            # Settings should handle case insensitivity based on SettingsConfigDict
            settings = Settings()
            # At minimum, required fields should be found
            assert settings.database_url is not None

    def test_settings_extra_ignored(self):
        """Test that extra environment variables are ignored"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379/0',
            'UNKNOWN_SETTING': 'should be ignored'
        }):
            from app.config import Settings
            settings = Settings()
            # Should not raise error
            assert not hasattr(settings, 'unknown_setting')
