"""Email notification service"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import NotificationLog, Job

settings = get_settings()


class EmailService:
    """Service for sending email notifications"""

    def __init__(self, db: Session):
        self.db = db
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_pass = settings.smtp_pass
        self.notification_email = settings.notification_email

    def _is_configured(self) -> bool:
        """Check if email is properly configured"""
        return bool(
            self.smtp_user and
            self.smtp_pass and
            self.notification_email
        )

    def send_batch_notification(self, jobs: List[Job]) -> dict:
        """
        Send email notification for a batch of newly fetched jobs

        Args:
            jobs: List of Job objects to include in the notification

        Returns:
            dict with status and details
        """
        if not self._is_configured():
            print("Email not configured. Skipping notification.")
            return {
                "status": "skipped",
                "reason": "email_not_configured"
            }

        if not jobs:
            print("No jobs to notify about.")
            return {
                "status": "skipped",
                "reason": "no_jobs"
            }

        try:
            # Generate email content
            subject = f"🎯 {len(jobs)} New Job Opportunities Found"
            html_body = self._generate_batch_email_html(jobs)

            # Send email
            success = self._send_email(
                recipient=self.notification_email,
                subject=subject,
                html_body=html_body
            )

            # Log the notification
            self._log_notification(
                job_ids=[job.id for job in jobs],
                subject=subject,
                body=html_body,
                success=success
            )

            if success:
                print(f"Successfully sent email notification for {len(jobs)} jobs")
                return {
                    "status": "success",
                    "jobs_count": len(jobs),
                    "recipient": self.notification_email
                }
            else:
                return {
                    "status": "error",
                    "reason": "send_failed"
                }

        except Exception as e:
            print(f"Error sending batch notification: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _generate_batch_email_html(self, jobs: List[Job]) -> str:
        """
        Generate HTML email content for a batch of jobs

        Format: Company Name - Job Title - Location - Link
        """
        html = f"""
        <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                    }}
                    .header {{
                        background-color: #4CAF50;
                        color: white;
                        padding: 20px;
                        text-align: center;
                    }}
                    .content {{
                        padding: 20px;
                    }}
                    .job-list {{
                        list-style: none;
                        padding: 0;
                    }}
                    .job-item {{
                        background-color: #f9f9f9;
                        border-left: 4px solid #4CAF50;
                        margin: 15px 0;
                        padding: 15px;
                    }}
                    .job-title {{
                        font-size: 18px;
                        font-weight: bold;
                        color: #2c3e50;
                        margin-bottom: 5px;
                    }}
                    .job-company {{
                        font-size: 16px;
                        color: #555;
                        margin-bottom: 5px;
                    }}
                    .job-location {{
                        font-size: 14px;
                        color: #777;
                        margin-bottom: 10px;
                    }}
                    .job-link {{
                        display: inline-block;
                        padding: 8px 15px;
                        background-color: #4CAF50;
                        color: white !important;
                        text-decoration: none;
                        border-radius: 4px;
                        font-size: 14px;
                    }}
                    .job-link:hover {{
                        background-color: #45a049;
                    }}
                    .footer {{
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #ddd;
                        font-size: 12px;
                        color: #777;
                        text-align: center;
                    }}
                    .stats {{
                        background-color: #e3f2fd;
                        padding: 10px;
                        border-radius: 4px;
                        margin-bottom: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🎯 New Job Opportunities</h1>
                    <p>Found {len(jobs)} new positions matching your profile</p>
                </div>
                
                <div class="content">
                    <div class="stats">
                        <strong>📊 Summary:</strong> {len(jobs)} new job(s) • Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}
                    </div>
                    
                    <ul class="job-list">
        """

        # Add each job to the list
        for idx, job in enumerate(jobs, 1):
            location = self._format_location(job.location)

            html += f"""
                        <li class="job-item">
                            <div class="job-title">{idx}. {job.title}</div>
                            <div class="job-company">🏢 {job.company}</div>
                            <div class="job-location">📍 {location}</div>
                            <a href="{job.url}" class="job-link" target="_blank">View Job Details →</a>
                        </li>
            """

        html += """
                    </ul>
                </div>
                
                <div class="footer">
                    <p>This is an automated notification from Job Matcher</p>
                    <p>To manage your job search preferences, visit your dashboard</p>
                </div>
            </body>
        </html>
        """

        return html

    def _format_location(self, location: Optional[str]) -> str:
        """
        Format job location string
        Extracts city, state, country from location
        """
        if not location:
            return "Remote / Location not specified"

        # Clean up location string
        location = location.strip()

        # If it's already formatted nicely, return as is
        if location:
            return location

        return "Remote / Location not specified"

    def _send_email(self, recipient: str, subject: str, html_body: str) -> bool:
        """
        Send email via SMTP

        Args:
            recipient: Email address to send to
            subject: Email subject
            html_body: HTML content of email

        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.smtp_user
            message["To"] = recipient

            # Attach HTML content
            html_part = MIMEText(html_body, "html")
            message.attach(html_part)

            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(message)

            return True

        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

    def _log_notification(
        self,
        job_ids: List[int],
        subject: str,
        body: str,
        success: bool,
        error_message: Optional[str] = None
    ):
        """
        Log notification to database

        Args:
            job_ids: List of job IDs included in notification
            subject: Email subject
            body: Email body content
            success: Whether email was sent successfully
            error_message: Error message if failed
        """
        try:
            # For batch notifications, we'll log once with the first job_id
            # or None if no jobs
            job_id = job_ids[0] if job_ids else None

            log_entry = NotificationLog(
                job_id=job_id,
                recipient_email=self.notification_email,
                subject=subject,
                body=body[:1000],  # Truncate body to avoid huge database entries
                success=success,
                error_message=error_message
            )

            self.db.add(log_entry)
            self.db.commit()

        except Exception as e:
            print(f"Error logging notification: {str(e)}")
            self.db.rollback()

