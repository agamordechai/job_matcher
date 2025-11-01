"""Search filter management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas import SearchFilterCreate, SearchFilterUpdate, SearchFilterResponse
from app.services.filter_service import FilterService

router = APIRouter()


@router.get("/", response_model=List[SearchFilterResponse])
async def get_filters(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get all search filters"""
    filter_service = FilterService(db)
    return filter_service.get_all_filters(active_only=active_only)


@router.get("/{filter_id}", response_model=SearchFilterResponse)
async def get_filter(filter_id: int, db: Session = Depends(get_db)):
    """Get specific search filter"""
    filter_service = FilterService(db)
    search_filter = filter_service.get_filter(filter_id)
    if not search_filter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filter not found"
        )
    return search_filter


@router.post("/", response_model=SearchFilterResponse, status_code=status.HTTP_201_CREATED)
async def create_filter(
    filter_data: SearchFilterCreate,
    db: Session = Depends(get_db)
):
    """Create new search filter"""
    filter_service = FilterService(db)
    return filter_service.create_filter(filter_data)


@router.put("/{filter_id}", response_model=SearchFilterResponse)
async def update_filter(
    filter_id: int,
    filter_data: SearchFilterUpdate,
    db: Session = Depends(get_db)
):
    """Update search filter"""
    filter_service = FilterService(db)
    search_filter = filter_service.update_filter(filter_id, filter_data)
    if not search_filter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filter not found"
        )
    return search_filter


@router.delete("/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_filter(filter_id: int, db: Session = Depends(get_db)):
    """Delete search filter"""
    filter_service = FilterService(db)
    success = filter_service.delete_filter(filter_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filter not found"
        )
    return None

