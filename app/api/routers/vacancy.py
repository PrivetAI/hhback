from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session

from ...core.auth import get_current_user_id
from ...core.database import get_db
from ...services.hh_service import HHService
from ...models.db_models import ResponseHistory

router = APIRouter(prefix="/api", tags=["vacancy"])
hh_service = HHService()

@router.get("/vacancies")
async def get_vacancies(
    text: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    salary: Optional[int] = Query(None),
    only_with_salary: Optional[bool] = Query(False),
    experience: Optional[str] = Query(None),
    employment: Optional[str] = Query(None),
    schedule: Optional[str] = Query(None),
    page: int = Query(0),
    per_page: int = Query(20, ge=20, le=100),
    user_id: str = Depends(get_current_user_id)
):
    """Get vacancies list with filters"""
    params = {
        "page": page,
        "per_page": per_page
    }
    
    if text:
        params["text"] = text
    if area:
        params["area"] = area
    if salary:
        params["salary"] = salary
    if only_with_salary:
        params["only_with_salary"] = "true"
    if experience:
        params["experience"] = experience
    if employment:
        params["employment"] = employment
    if schedule:
        params["schedule"] = schedule
    
    return await hh_service.search_vacancies(user_id, params)

@router.get("/vacancy/{vacancy_id}")
async def get_vacancy_details(
    vacancy_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get full vacancy details"""
    return await hh_service.get_vacancy_details(user_id, vacancy_id)

@router.post("/vacancy/{vacancy_id}/analyze")
async def analyze_vacancy(
    vacancy_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Analyze vacancy match"""
    return await hh_service.analyze_vacancy_match(user_id, vacancy_id)

@router.post("/vacancy/{vacancy_id}/generate-letter")
async def generate_letter(
    vacancy_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Generate cover letter"""
    return await hh_service.generate_cover_letter(user_id, vacancy_id)

@router.post("/vacancy/{vacancy_id}/apply")
async def apply_to_vacancy(
    vacancy_id: str,
    message: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Apply to vacancy"""
    result = await hh_service.apply_to_vacancy(user_id, vacancy_id, message)
    
    # Save to history
    history = ResponseHistory(
        user_id=user_id,
        vacancy_id=vacancy_id,
        vacancy_title=result.get("vacancy", {}).get("name", "Unknown"),
        cover_letter=message,
        match_score=0  # TODO: add score from analysis
    )
    db.add(history)
    db.commit()
    
    return result