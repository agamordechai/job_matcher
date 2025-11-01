"""CV management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas import CVResponse, CVSummaryUpdate
from app.services.cv_service import CVService

router = APIRouter()


@router.post("/upload", response_model=CVResponse, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a CV file (PDF or DOCX)"""
    cv_service = CVService(db)
    cv = await cv_service.upload_cv(file)
    return cv


@router.get("/", response_model=CVResponse)
async def get_current_cv(db: Session = Depends(get_db)):
    """Get the current active CV"""
    cv_service = CVService(db)
    cv = cv_service.get_active_cv()
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active CV found. Please upload a CV first."
        )
    return cv


@router.get("/all", response_model=List[CVResponse])
async def get_all_cvs(db: Session = Depends(get_db)):
    """Get all uploaded CVs"""
    cv_service = CVService(db)
    return cv_service.get_all_cvs()


@router.put("/summary", response_model=CVResponse)
async def update_cv_summary(
    summary_update: CVSummaryUpdate,
    db: Session = Depends(get_db)
):
    """Update CV summary manually"""
    cv_service = CVService(db)
    cv = cv_service.update_summary(summary_update.summary)
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active CV found"
        )
    return cv


@router.delete("/{cv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cv(cv_id: int, db: Session = Depends(get_db)):
    """Delete a CV (soft delete - marks as inactive)"""
    cv_service = CVService(db)
    success = cv_service.delete_cv(cv_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    return None

