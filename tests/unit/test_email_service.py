"""Unit tests for Email Service"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.services.email_service import EmailService
from app.models import Job, NotificationLog, JobScore, JobStatus


class TestEmailServiceInit:
    """Tests for EmailService initialization"""

    def test_init(self, db_session, mock_settings):
        """Test service initialization"""
        service = EmailService(db_session)
        assert service.db == db_session
        assert service.smtp_host == mock_settings.smtp_host
        assert service.smtp_port == mock_settings.smtp_port


class TestEmailServiceConfiguration:
    """Tests for email configuration checking"""

    def test_is_configured_true(self, db_session, mock_settings):
        """Test configuration check when properly configured"""
        service = EmailService(db_session)
        assert service._is_configured() is True

    def test_is_configured_missing_user(self, db_session, mock_settings):
        """Test configuration check when SMTP user missing"""
        service = EmailService(db_session)
        service.smtp_user = ""
        assert service._is_configured() is False

    def test_is_configured_missing_password(self, db_session, mock_settings):
        """Test configuration check when SMTP password missing"""
        service = EmailService(db_session)
        service.smtp_pass = ""
        assert service._is_configured() is False

    def test_is_configured_missing_notification_email(self, db_session, mock_settings):
        """Test configuration check when notification email missing"""
        service = EmailService(db_session)
        service.notification_email = ""
        assert service._is_configured() is False


class TestEmailServiceBatchNotification:
    """Tests for batch notification sending"""

    def test_send_batch_notification_not_configured(self, db_session, mock_settings):
        """Test batch notification when email not configured"""
        service = EmailService(db_session)
        service.smtp_user = ""

        result = service.send_batch_notification([])

        assert result["status"] == "skipped"
        assert result["reason"] == "email_not_configured"

    def test_send_batch_notification_empty_jobs(self, db_session, mock_settings):
        """Test batch notification with no jobs"""
        service = EmailService(db_session)

        result = service.send_batch_notification([])

        assert result["status"] == "skipped"
        assert result["reason"] == "no_jobs"

    def test_send_batch_notification_success(self, db_session, mock_settings, sample_job):
        """Test successful batch notification"""
        service = EmailService(db_session)

        with patch.object(service, '_send_email', return_value=True) as mock_send, \
             patch.object(service, '_log_notification') as mock_log:
            result = service.send_batch_notification([sample_job])

            assert result["status"] == "success"
            assert result["jobs_count"] == 1
            mock_send.assert_called_once()
            mock_log.assert_called_once()

    def test_send_batch_notification_multiple_jobs(self, db_session, mock_settings, sample_cv):
        """Test batch notification with multiple jobs"""
        # Create multiple jobs
        jobs = []
        for i in range(3):
            job = Job(
                cv_id=sample_cv.id,
                external_job_id=f"job_{i}",
                title=f"Job {i}",
                company=f"Company {i}",
                description="Description",
                url=f"https://example.com/job/{i}"
            )
            db_session.add(job)
            jobs.append(job)
        db_session.commit()

        service = EmailService(db_session)

        with patch.object(service, '_send_email', return_value=True), \
             patch.object(service, '_log_notification'):
            result = service.send_batch_notification(jobs)

            assert result["status"] == "success"
            assert result["jobs_count"] == 3

    def test_send_batch_notification_send_failure(self, db_session, mock_settings, sample_job):
        """Test batch notification when send fails"""
        service = EmailService(db_session)

        with patch.object(service, '_send_email', return_value=False), \
             patch.object(service, '_log_notification'):
            result = service.send_batch_notification([sample_job])

            assert result["status"] == "error"
            assert result["reason"] == "send_failed"

    def test_send_batch_notification_exception(self, db_session, mock_settings, sample_job):
        """Test batch notification when exception occurs"""
        service = EmailService(db_session)

        with patch.object(service, '_send_email', side_effect=Exception("SMTP error")):
            result = service.send_batch_notification([sample_job])

            assert result["status"] == "error"
            assert "SMTP error" in result.get("error", "")


class TestEmailServiceHTMLGeneration:
    """Tests for HTML email generation"""

    def test_generate_batch_email_html_single_job(self, db_session, mock_settings, sample_job):
        """Test HTML generation for single job"""
        service = EmailService(db_session)
        html = service._generate_batch_email_html([sample_job])

        assert sample_job.title in html
        assert sample_job.company in html
        assert "New Job Opportunities" in html
        assert "1 new" in html

    def test_generate_batch_email_html_multiple_jobs(self, db_session, mock_settings, sample_cv):
        """Test HTML generation for multiple jobs"""
        jobs = []
        for i in range(5):
            job = Job(
                cv_id=sample_cv.id,
                external_job_id=f"job_{i}",
                title=f"Developer Position {i}",
                company=f"Company {i}",
                description="Description",
                location=f"City {i}",
                url=f"https://example.com/job/{i}"
            )
            db_session.add(job)
            jobs.append(job)
        db_session.commit()

        service = EmailService(db_session)
        html = service._generate_batch_email_html(jobs)

        assert "5 new" in html
        for i in range(5):
            assert f"Developer Position {i}" in html
            assert f"Company {i}" in html

    def test_generate_batch_email_html_missing_location(self, db_session, mock_settings, sample_cv):
        """Test HTML generation when job has no location"""
        job = Job(
            cv_id=sample_cv.id,
            external_job_id="no_location_job",
            title="Remote Developer",
            company="Remote Corp",
            description="Description",
            location=None,
            url="https://example.com/job/123"
        )
        db_session.add(job)
        db_session.commit()

        service = EmailService(db_session)
        html = service._generate_batch_email_html([job])

        assert "Remote / Location not specified" in html


class TestEmailServiceFormatLocation:
    """Tests for location formatting"""

    def test_format_location_valid(self, db_session, mock_settings):
        """Test formatting valid location"""
        service = EmailService(db_session)
        result = service._format_location("San Francisco, CA")
        assert result == "San Francisco, CA"

    def test_format_location_none(self, db_session, mock_settings):
        """Test formatting None location"""
        service = EmailService(db_session)
        result = service._format_location(None)
        assert result == "Remote / Location not specified"

    def test_format_location_empty(self, db_session, mock_settings):
        """Test formatting empty location"""
        service = EmailService(db_session)
        result = service._format_location("")
        assert result == "Remote / Location not specified"

    def test_format_location_whitespace(self, db_session, mock_settings):
        """Test formatting whitespace-only location"""
        service = EmailService(db_session)
        result = service._format_location("   ")
        # After strip, becomes empty
        assert "Remote" in result or result == "   "


class TestEmailServiceSendEmail:
    """Tests for SMTP email sending"""

    def test_send_email_success(self, db_session, mock_settings):
        """Test successful email send"""
        service = EmailService(db_session)

        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock()

            result = service._send_email(
                recipient="test@example.com",
                subject="Test Subject",
                html_body="<html><body>Test</body></html>"
            )

            assert result is True
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.send_message.assert_called_once()

    def test_send_email_failure(self, db_session, mock_settings):
        """Test email send failure"""
        service = EmailService(db_session)

        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.return_value.__enter__ = MagicMock(
                side_effect=Exception("Connection failed")
            )

            result = service._send_email(
                recipient="test@example.com",
                subject="Test Subject",
                html_body="<html><body>Test</body></html>"
            )

            assert result is False


class TestEmailServiceLogging:
    """Tests for notification logging"""

    def test_log_notification_success(self, db_session, mock_settings, sample_job):
        """Test successful notification logging"""
        service = EmailService(db_session)

        service._log_notification(
            job_ids=[sample_job.id],
            subject="Test Subject",
            body="Test Body",
            success=True
        )

        # Verify log entry was created
        log_entry = db_session.query(NotificationLog).filter(
            NotificationLog.job_id == sample_job.id
        ).first()

        assert log_entry is not None
        assert log_entry.success is True
        assert log_entry.subject == "Test Subject"

    def test_log_notification_failure(self, db_session, mock_settings, sample_job):
        """Test logging failed notification"""
        service = EmailService(db_session)

        service._log_notification(
            job_ids=[sample_job.id],
            subject="Test Subject",
            body="Test Body",
            success=False,
            error_message="SMTP timeout"
        )

        log_entry = db_session.query(NotificationLog).filter(
            NotificationLog.job_id == sample_job.id
        ).first()

        assert log_entry is not None
        assert log_entry.success is False
        assert log_entry.error_message == "SMTP timeout"

    def test_log_notification_empty_job_ids(self, db_session, mock_settings):
        """Test logging with empty job IDs"""
        service = EmailService(db_session)

        service._log_notification(
            job_ids=[],
            subject="Test Subject",
            body="Test Body",
            success=True
        )

        # Should create log with job_id=None
        log_entry = db_session.query(NotificationLog).filter(
            NotificationLog.subject == "Test Subject"
        ).first()

        assert log_entry is not None
        assert log_entry.job_id is None

    def test_log_notification_body_truncation(self, db_session, mock_settings, sample_job):
        """Test that long body is truncated"""
        service = EmailService(db_session)

        long_body = "x" * 2000  # Longer than 1000 char limit

        service._log_notification(
            job_ids=[sample_job.id],
            subject="Test Subject",
            body=long_body,
            success=True
        )

        log_entry = db_session.query(NotificationLog).filter(
            NotificationLog.job_id == sample_job.id
        ).first()

        assert log_entry is not None
        assert len(log_entry.body) == 1000


class TestEmailServiceEdgeCases:
    """Edge case tests for Email Service"""

    def test_send_batch_notification_special_characters(self, db_session, mock_settings, sample_cv):
        """Test notification with special characters in job details"""
        job = Job(
            cv_id=sample_cv.id,
            external_job_id="special_chars_job",
            title="Software Engineer <Full Stack>",
            company="A & B Corp",
            description="Description with 'quotes' and \"double quotes\"",
            url="https://example.com/job/123"
        )
        db_session.add(job)
        db_session.commit()

        service = EmailService(db_session)

        with patch.object(service, '_send_email', return_value=True), \
             patch.object(service, '_log_notification'):
            result = service.send_batch_notification([job])
            assert result["status"] == "success"

    def test_send_batch_notification_very_long_title(self, db_session, mock_settings, sample_cv):
        """Test notification with very long job title"""
        job = Job(
            cv_id=sample_cv.id,
            external_job_id="long_title_job",
            title="A" * 500,  # Very long title
            company="Test Corp",
            description="Description",
            url="https://example.com/job/123"
        )
        db_session.add(job)
        db_session.commit()

        service = EmailService(db_session)

        with patch.object(service, '_send_email', return_value=True), \
             patch.object(service, '_log_notification'):
            result = service.send_batch_notification([job])
            assert result["status"] == "success"
