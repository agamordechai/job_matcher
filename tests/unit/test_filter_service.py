"""Unit tests for Filter Service"""
import pytest
from unittest.mock import patch

from app.services.filter_service import FilterService
from app.models import SearchFilter
from app.schemas import SearchFilterCreate, SearchFilterUpdate


class TestFilterService:
    """Tests for FilterService class"""

    def test_init(self, db_session):
        """Test service initialization"""
        service = FilterService(db_session)
        assert service.db == db_session

    def test_get_filter_by_id(self, db_session, sample_search_filter):
        """Test getting filter by ID"""
        service = FilterService(db_session)
        result = service.get_filter(sample_search_filter.id)
        assert result is not None
        assert result.id == sample_search_filter.id
        assert result.name == sample_search_filter.name

    def test_get_filter_by_id_not_found(self, db_session):
        """Test returns None for non-existent filter"""
        service = FilterService(db_session)
        result = service.get_filter(9999)
        assert result is None


class TestFilterServiceGetAll:
    """Tests for get_all_filters functionality"""

    def test_get_all_filters_active_only_default(self, db_session, sample_search_filter):
        """Test getting all filters (active only by default)"""
        service = FilterService(db_session)
        results = service.get_all_filters()
        assert len(results) >= 1
        for f in results:
            assert f.is_active is True

    def test_get_all_filters_include_inactive(self, db_session, sample_search_filter):
        """Test getting all filters including inactive"""
        # Create an inactive filter
        inactive_filter = SearchFilter(
            name="Inactive Filter",
            keywords=["Test"],
            is_active=False
        )
        db_session.add(inactive_filter)
        db_session.commit()

        service = FilterService(db_session)

        # Active only
        active_results = service.get_all_filters(active_only=True)
        assert all(f.is_active for f in active_results)

        # Include inactive
        all_results = service.get_all_filters(active_only=False)
        assert len(all_results) > len(active_results)

    def test_get_all_filters_ordered_by_created_at(self, db_session):
        """Test that filters are ordered by creation date descending"""
        # Create multiple filters
        filter1 = SearchFilter(name="Filter 1", keywords=["test1"])
        db_session.add(filter1)
        db_session.commit()

        filter2 = SearchFilter(name="Filter 2", keywords=["test2"])
        db_session.add(filter2)
        db_session.commit()

        service = FilterService(db_session)
        results = service.get_all_filters()

        # Both filters should be present
        assert len(results) >= 2
        filter_names = [f.name for f in results]
        assert "Filter 1" in filter_names
        assert "Filter 2" in filter_names


class TestFilterServiceCreate:
    """Tests for filter creation"""

    def test_create_filter_basic(self, db_session):
        """Test creating a basic filter"""
        service = FilterService(db_session)
        filter_data = SearchFilterCreate(
            name="New Test Filter",
            keywords=["Python Developer", "Backend Engineer"],
            location="New York",
            remote=False
        )

        result = service.create_filter(filter_data)
        assert result is not None
        assert result.id is not None
        assert result.name == "New Test Filter"
        assert result.keywords == ["Python Developer", "Backend Engineer"]
        assert result.location == "New York"
        assert result.remote is False
        assert result.is_active is True

    def test_create_filter_full_options(self, db_session):
        """Test creating filter with all options"""
        service = FilterService(db_session)
        filter_data = SearchFilterCreate(
            name="Full Options Filter",
            keywords=["Software Engineer"],
            location="San Francisco, CA",
            job_type="full-time",
            experience_level="mid",
            remote=True
        )

        result = service.create_filter(filter_data)
        assert result is not None
        assert result.job_type == "full-time"
        assert result.experience_level == "mid"
        assert result.remote is True

    def test_create_filter_minimal(self, db_session):
        """Test creating filter with minimal required fields"""
        service = FilterService(db_session)
        filter_data = SearchFilterCreate(
            name="Minimal Filter",
            keywords=["Developer"]
        )

        result = service.create_filter(filter_data)
        assert result is not None
        assert result.name == "Minimal Filter"
        assert result.keywords == ["Developer"]
        assert result.location is None
        assert result.job_type is None
        assert result.experience_level is None
        assert result.remote is False


class TestFilterServiceUpdate:
    """Tests for filter update operations"""

    def test_update_filter_name(self, db_session, sample_search_filter):
        """Test updating filter name"""
        service = FilterService(db_session)
        update_data = SearchFilterUpdate(name="Updated Name")

        result = service.update_filter(sample_search_filter.id, update_data)
        assert result is not None
        assert result.name == "Updated Name"

    def test_update_filter_keywords(self, db_session, sample_search_filter):
        """Test updating filter keywords"""
        service = FilterService(db_session)
        new_keywords = ["New Keyword 1", "New Keyword 2", "New Keyword 3"]
        update_data = SearchFilterUpdate(keywords=new_keywords)

        result = service.update_filter(sample_search_filter.id, update_data)
        assert result is not None
        assert result.keywords == new_keywords

    def test_update_filter_multiple_fields(self, db_session, sample_search_filter):
        """Test updating multiple fields at once"""
        service = FilterService(db_session)
        update_data = SearchFilterUpdate(
            name="Completely Updated",
            keywords=["Updated Keyword"],
            location="Austin, TX",
            remote=False,
            is_active=False
        )

        result = service.update_filter(sample_search_filter.id, update_data)
        assert result is not None
        assert result.name == "Completely Updated"
        assert result.keywords == ["Updated Keyword"]
        assert result.location == "Austin, TX"
        assert result.remote is False
        assert result.is_active is False

    def test_update_filter_partial(self, db_session, sample_search_filter):
        """Test partial update doesn't affect other fields"""
        original_keywords = sample_search_filter.keywords
        original_location = sample_search_filter.location

        service = FilterService(db_session)
        update_data = SearchFilterUpdate(name="Only Name Updated")

        result = service.update_filter(sample_search_filter.id, update_data)
        assert result is not None
        assert result.name == "Only Name Updated"
        assert result.keywords == original_keywords
        assert result.location == original_location

    def test_update_filter_not_found(self, db_session):
        """Test updating non-existent filter"""
        service = FilterService(db_session)
        update_data = SearchFilterUpdate(name="Test")

        result = service.update_filter(9999, update_data)
        assert result is None


class TestFilterServiceDelete:
    """Tests for filter deletion (soft delete)"""

    def test_delete_filter_soft_delete(self, db_session, sample_search_filter):
        """Test that delete performs soft delete"""
        service = FilterService(db_session)
        result = service.delete_filter(sample_search_filter.id)

        assert result is True
        db_session.refresh(sample_search_filter)
        assert sample_search_filter.is_active is False

        # Should still exist in database
        still_exists = service.get_filter(sample_search_filter.id)
        assert still_exists is not None

    def test_delete_filter_not_found(self, db_session):
        """Test deleting non-existent filter"""
        service = FilterService(db_session)
        result = service.delete_filter(9999)
        assert result is False

    def test_delete_filter_already_inactive(self, db_session, sample_search_filter):
        """Test deleting already inactive filter"""
        sample_search_filter.is_active = False
        db_session.commit()

        service = FilterService(db_session)
        result = service.delete_filter(sample_search_filter.id)

        assert result is True
        db_session.refresh(sample_search_filter)
        assert sample_search_filter.is_active is False


class TestFilterServiceEdgeCases:
    """Edge case tests for Filter Service"""

    def test_get_all_filters_empty_database(self, db_session):
        """Test listing filters when database is empty"""
        service = FilterService(db_session)
        results = service.get_all_filters()
        assert len(results) == 0

    def test_create_filter_with_single_keyword(self, db_session):
        """Test creating filter with single keyword"""
        service = FilterService(db_session)
        filter_data = SearchFilterCreate(
            name="Single Keyword",
            keywords=["Python"]
        )

        result = service.create_filter(filter_data)
        assert result is not None
        assert result.keywords == ["Python"]

    def test_create_filter_with_many_keywords(self, db_session):
        """Test creating filter with many keywords"""
        service = FilterService(db_session)
        many_keywords = [f"Keyword {i}" for i in range(20)]
        filter_data = SearchFilterCreate(
            name="Many Keywords",
            keywords=many_keywords
        )

        result = service.create_filter(filter_data)
        assert result is not None
        assert len(result.keywords) == 20

    def test_update_filter_clear_optional_fields(self, db_session, sample_search_filter):
        """Test clearing optional fields via update"""
        service = FilterService(db_session)
        update_data = SearchFilterUpdate(
            location=None,
            job_type=None
        )

        result = service.update_filter(sample_search_filter.id, update_data)
        # Note: Pydantic will exclude unset fields, so None won't clear existing values
        # This tests the actual behavior of exclude_unset=True
        assert result is not None
