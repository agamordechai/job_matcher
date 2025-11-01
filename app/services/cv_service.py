"""CV management service"""
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status
from typing import Optional, List
import os
from pathlib import Path
from datetime import datetime
from app.models import CV
from app.config import get_settings
from app.utils.file_parser import parse_cv_file

settings = get_settings()


class CVService:
    """Service for CV management operations"""

    def __init__(self, db: Session):
        self.db = db
        self._ensure_storage_dirs()

    def _ensure_storage_dirs(self):
        """Ensure storage directories exist"""
        Path(settings.cv_storage_path).mkdir(parents=True, exist_ok=True)
        Path(settings.temp_storage_path).mkdir(parents=True, exist_ok=True)

    async def upload_cv(self, file: UploadFile) -> CV:
        """Upload and parse a CV file"""
        # Validate file type
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )

        file_ext = file.filename.lower().split('.')[-1]
        if file_ext not in ['pdf', 'docx', 'doc']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF and DOCX files are supported"
            )

        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"cv_{timestamp}.{file_ext}"
        file_path = os.path.join(settings.cv_storage_path, safe_filename)

        # Save file
        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )

        # Parse CV content
        try:
            cv_text = parse_cv_file(file_path, file_ext)
        except Exception as e:
            # Clean up file if parsing fails
            os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse CV: {str(e)}"
            )

        # Deactivate previous active CVs
        self.db.query(CV).filter(CV.is_active == True).update({"is_active": False})

        # Create CV record
        cv = CV(
            filename=file.filename,
            file_path=file_path,
            content=cv_text,
            is_active=True
        )

        self.db.add(cv)
        self.db.commit()
        self.db.refresh(cv)

        return cv

    def get_active_cv(self) -> Optional[CV]:
        """Get the currently active CV"""
        return self.db.query(CV).filter(CV.is_active == True).first()

    def get_all_cvs(self) -> List[CV]:
        """Get all CVs"""
        return self.db.query(CV).order_by(CV.uploaded_at.desc()).all()

    def update_summary(self, summary: str) -> Optional[CV]:
        """Update CV summary"""
        cv = self.get_active_cv()
        if cv:
            cv.summary = summary
            self.db.commit()
            self.db.refresh(cv)
        return cv

    def delete_cv(self, cv_id: int) -> bool:
        """Soft delete a CV"""
        cv = self.db.query(CV).filter(CV.id == cv_id).first()
        if cv:
            cv.is_active = False
            self.db.commit()
            return True
        return False

