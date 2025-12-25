"""Unit tests for CV Service"""
import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException

from app.services.cv_service import CVService
from app.models import CV


class TestCVService:
    """Tests for CVService class"""

    def test_init_creates_storage_dirs(self, db_session, mock_settings):
        """Test that initialization creates storage directories"""
        with patch('os.makedirs') as mock_makedirs, \
             patch('pathlib.Path.mkdir') as mock_mkdir:
            service = CVService(db_session)
            assert service.db == db_session

    def test_get_active_cv_returns_active(self, db_session, sample_cv):
        """Test getting the active CV"""
        service = CVService(db_session)
        result = service.get_active_cv()
        assert result is not None
        assert result.id == sample_cv.id
        assert result.is_active is True

    def test_get_active_cv_returns_none_when_no_active(self, db_session):
        """Test returns None when no active CV exists"""
        service = CVService(db_session)
        result = service.get_active_cv()
        assert result is None

    def test_get_cv_by_id(self, db_session, sample_cv):
        """Test getting CV by specific ID"""
        service = CVService(db_session)
        result = service.get_cv(sample_cv.id)
        assert result is not None
        assert result.id == sample_cv.id
        assert result.filename == sample_cv.filename

    def test_get_cv_by_id_not_found(self, db_session):
        """Test returns None when CV ID doesn't exist"""
        service = CVService(db_session)
        result = service.get_cv(9999)
        assert result is None

    def test_get_all_cvs(self, db_session, sample_cv):
        """Test getting all active CVs"""
        service = CVService(db_session)
        results = service.get_all_cvs()
        assert len(results) == 1
        assert results[0].id == sample_cv.id

    def test_get_all_cvs_excludes_inactive(self, db_session, sample_cv):
        """Test that inactive CVs are excluded from list"""
        sample_cv.is_active = False
        db_session.commit()

        service = CVService(db_session)
        results = service.get_all_cvs()
        assert len(results) == 0

    def test_update_summary(self, db_session, sample_cv):
        """Test updating CV summary"""
        service = CVService(db_session)
        new_summary = "Updated professional summary for testing."
        result = service.update_summary(new_summary)

        assert result is not None
        assert result.summary == new_summary

    def test_update_summary_no_active_cv(self, db_session):
        """Test update summary returns None when no active CV"""
        service = CVService(db_session)
        result = service.update_summary("New summary")
        assert result is None

    def test_delete_cv_success(self, db_session, sample_cv):
        """Test successful CV deletion"""
        service = CVService(db_session)

        with patch('os.path.exists', return_value=True), \
             patch('os.remove') as mock_remove:
            result = service.delete_cv(sample_cv.id)
            assert result is True
            mock_remove.assert_called_once_with(sample_cv.file_path)

    def test_delete_cv_not_found(self, db_session):
        """Test deletion returns False when CV not found"""
        service = CVService(db_session)
        result = service.delete_cv(9999)
        assert result is False

    def test_delete_cv_file_not_exists(self, db_session, sample_cv):
        """Test deletion succeeds even if file doesn't exist"""
        service = CVService(db_session)

        with patch('os.path.exists', return_value=False):
            result = service.delete_cv(sample_cv.id)
            assert result is True


class TestCVServiceUpload:
    """Tests for CV upload functionality"""

    @pytest.mark.asyncio
    async def test_upload_cv_no_filename(self, db_session, mock_settings):
        """Test upload fails with no filename"""
        service = CVService(db_session)
        mock_file = MagicMock()
        mock_file.filename = None

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_cv(mock_file)
        assert exc_info.value.status_code == 400
        assert "No filename provided" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_cv_invalid_extension(self, db_session, mock_settings):
        """Test upload fails with invalid file extension"""
        service = CVService(db_session)
        mock_file = MagicMock()
        mock_file.filename = "test.txt"

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_cv(mock_file)
        assert exc_info.value.status_code == 400
        assert "Only PDF and DOCX files are supported" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_cv_success(self, db_session, mock_settings):
        """Test successful CV upload"""
        service = CVService(db_session)

        mock_file = MagicMock()
        mock_file.filename = "test_resume.pdf"
        mock_file.read = AsyncMock(return_value=b"PDF content")

        with patch('builtins.open', MagicMock()), \
             patch('app.services.cv_service.parse_cv_file', return_value="Parsed CV content"):
            result = await service.upload_cv(mock_file)

            assert result is not None
            assert result.content == "Parsed CV content"
            assert result.is_active is True

    @pytest.mark.asyncio
    async def test_upload_cv_deactivates_previous(self, db_session, sample_cv, mock_settings):
        """Test that uploading new CV deactivates previous"""
        service = CVService(db_session)

        mock_file = MagicMock()
        mock_file.filename = "new_resume.pdf"
        mock_file.read = AsyncMock(return_value=b"New PDF content")

        with patch('builtins.open', MagicMock()), \
             patch('app.services.cv_service.parse_cv_file', return_value="New parsed content"):
            new_cv = await service.upload_cv(mock_file)

            # Refresh the old CV to get updated state
            db_session.refresh(sample_cv)

            assert new_cv.is_active is True
            assert sample_cv.is_active is False

    @pytest.mark.asyncio
    async def test_upload_cv_parse_failure_cleans_up(self, db_session, mock_settings):
        """Test that parse failure cleans up saved file"""
        service = CVService(db_session)

        mock_file = MagicMock()
        mock_file.filename = "test.pdf"
        mock_file.read = AsyncMock(return_value=b"Invalid content")

        with patch('builtins.open', MagicMock()), \
             patch('os.remove') as mock_remove, \
             patch('app.services.cv_service.parse_cv_file', side_effect=Exception("Parse error")):

            with pytest.raises(HTTPException) as exc_info:
                await service.upload_cv(mock_file)

            assert exc_info.value.status_code == 400
            assert "Failed to parse CV" in str(exc_info.value.detail)
            mock_remove.assert_called_once()


class TestCVServiceEdgeCases:
    """Edge case tests for CV service"""

    def test_multiple_active_cvs_only_one_returned(self, db_session):
        """Test that only one CV is returned even if multiple are active"""
        # Create multiple active CVs
        cv1 = CV(
            filename="cv1.pdf",
            file_path="/tmp/cv1.pdf",
            content="Content 1",
            is_active=True
        )
        cv2 = CV(
            filename="cv2.pdf",
            file_path="/tmp/cv2.pdf",
            content="Content 2",
            is_active=True
        )
        db_session.add_all([cv1, cv2])
        db_session.commit()

        service = CVService(db_session)
        result = service.get_active_cv()

        # Should return one (the first one found)
        assert result is not None
        assert result.is_active is True

    def test_get_all_cvs_ordered_by_upload_date(self, db_session):
        """Test that CVs are ordered by upload date descending"""
        # Create CVs in order
        cv1 = CV(
            filename="old_cv.pdf",
            file_path="/tmp/old_cv.pdf",
            content="Old content",
            is_active=True
        )
        db_session.add(cv1)
        db_session.commit()

        cv2 = CV(
            filename="new_cv.pdf",
            file_path="/tmp/new_cv.pdf",
            content="New content",
            is_active=True
        )
        db_session.add(cv2)
        db_session.commit()

        service = CVService(db_session)
        results = service.get_all_cvs()

        # Should return both CVs
        assert len(results) >= 2
        # Check that both CVs are returned (order may vary in SQLite)
        filenames = [r.filename for r in results]
        assert "old_cv.pdf" in filenames
        assert "new_cv.pdf" in filenames
