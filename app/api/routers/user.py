from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ...models.schemas import ResumeResponse, Dictionaries, ResponseHistoryItem
from ...models.db_models import ResponseHistory
from ...core.auth import get_current_user_id
from ...core.database import get_db
from ...services.hh_service import HHService

router = APIRouter(prefix="/api", tags=["user"])
hh_service = HHService()

@router.get("/resume", response_model=ResumeResponse)
async def get_resume(user_id: str = Depends(get_current_user_id)):
    """Get user's resume"""
    return await hh_service.get_user_resume(user_id)

@router.get("/dictionaries", response_model=Dictionaries)
async def get_dictionaries():
    """Get HH dictionaries for filters"""
    return await hh_service.get_dictionaries()

@router.get("/areas")
async def get_areas():
    """Get areas (cities) for filters"""
    return await hh_service.get_areas()

@router.get("/history", response_model=List[ResponseHistoryItem])
async def get_history(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get user's application history"""
    history = db.query(ResponseHistory).filter(
        ResponseHistory.user_id == user_id
    ).order_by(ResponseHistory.created_at.desc()).all()
    
    return history