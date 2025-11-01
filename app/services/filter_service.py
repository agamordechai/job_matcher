"""Search filter management service"""
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models import SearchFilter
from app.schemas import SearchFilterCreate, SearchFilterUpdate


class FilterService:
    """Service for search filter management"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_filters(self, active_only: bool = True) -> List[SearchFilter]:
        """Get all search filters"""
        query = self.db.query(SearchFilter)
        if active_only:
            query = query.filter(SearchFilter.is_active == True)
        return query.order_by(SearchFilter.created_at.desc()).all()

    def get_filter(self, filter_id: int) -> Optional[SearchFilter]:
        """Get specific filter by ID"""
        return self.db.query(SearchFilter).filter(SearchFilter.id == filter_id).first()

    def create_filter(self, filter_data: SearchFilterCreate) -> SearchFilter:
        """Create a new search filter"""
        search_filter = SearchFilter(**filter_data.model_dump())
        self.db.add(search_filter)
        self.db.commit()
        self.db.refresh(search_filter)
        return search_filter

    def update_filter(
        self,
        filter_id: int,
        filter_data: SearchFilterUpdate
    ) -> Optional[SearchFilter]:
        """Update a search filter"""
        search_filter = self.get_filter(filter_id)
        if search_filter:
            update_data = filter_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(search_filter, key, value)
            self.db.commit()
            self.db.refresh(search_filter)
        return search_filter

    def delete_filter(self, filter_id: int) -> bool:
        """Soft delete a filter"""
        search_filter = self.get_filter(filter_id)
        if search_filter:
            search_filter.is_active = False
            self.db.commit()
            return True
        return False

