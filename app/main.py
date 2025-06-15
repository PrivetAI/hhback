from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import httpx
from typing import Optional
from datetime import datetime
import json

from .database import engine, get_db
from .models import Base, ResponseHistory
from .schemas import VacancyResponse, ResumeResponse, CoverLetterRequest
from .auth import create_access_token, get_current_user_id
from .hh_api import HHClient
from .ai_service import AIService
from .redis_client import redis_client

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

hh_client = HHClient()
ai_service = AIService()

@app.post("/api/auth/callback")
async def auth_callback(code: str):
    """HH OAuth callback"""
    token_data = await hh_client.exchange_code_for_token(code)
    user_data = await hh_client.get_user_info(token_data["access_token"])
    
    # Save token to redis with user_id as key
    await redis_client.setex(
        f"token:{user_data['id']}", 
        token_data["expires_in"], 
        token_data["access_token"]
    )
    
    jwt_token = create_access_token({"sub": str(user_data["id"])})
    return {"token": jwt_token, "user": user_data}

@app.get("/api/resume")
async def get_resume(user_id: str = Depends(get_current_user_id)):
    """Get user's resume"""
    token = await redis_client.get(f"token:{user_id}")
    if not token:
        raise HTTPException(401, "Token expired")
    
    # Check cache first
    cached = await redis_client.get(f"resume:{user_id}")
    if cached:
        return json.loads(cached)
    
    resume = await hh_client.get_resume(token)
    
    # Cache for 1 hour
    await redis_client.setex(f"resume:{user_id}", 3600, json.dumps(resume))
    return resume

@app.get("/api/vacancies")
async def get_vacancies(
    page: int = Query(0),
    per_page: int = Query(20),
    user_id: str = Depends(get_current_user_id)
):
    """Get vacancies list"""
    token = await redis_client.get(f"token:{user_id}")
    if not token:
        raise HTTPException(401, "Token expired")
    
    vacancies = await hh_client.search_vacancies(token, page, per_page)
    return vacancies

@app.post("/api/vacancy/{vacancy_id}/analyze")
async def analyze_vacancy(
    vacancy_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Analyze match between resume and vacancy"""
    token = await redis_client.get(f"token:{user_id}")
    if not token:
        raise HTTPException(401, "Token expired")
    
    # Get resume and vacancy
    resume = await get_resume(user_id)
    vacancy = await hh_client.get_vacancy(token, vacancy_id)
    
    # Check cache
    cache_key = f"analysis:{user_id}:{vacancy_id}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    score = await ai_service.analyze_match(resume, vacancy)
    
    # Cache for 24 hours
    await redis_client.setex(cache_key, 86400, json.dumps(score))
    return score

@app.post("/api/vacancy/{vacancy_id}/generate-letter")
async def generate_cover_letter(
    vacancy_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Generate cover letter"""
    token = await redis_client.get(f"token:{user_id}")
    if not token:
        raise HTTPException(401, "Token expired")
    
    resume = await get_resume(user_id)
    vacancy = await hh_client.get_vacancy(token, vacancy_id)
    
    letter = await ai_service.generate_cover_letter(resume, vacancy)
    
    # Save to history
    history = ResponseHistory(
        user_id=user_id,
        vacancy_id=vacancy_id,
        vacancy_title=vacancy["name"],
        cover_letter=letter["content"],
        match_score=letter["score"]
    )
    db.add(history)
    db.commit()
    
    return letter

@app.post("/api/vacancy/{vacancy_id}/apply")
async def apply_to_vacancy(
    vacancy_id: str,
    message: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Send application to vacancy"""
    token = await redis_client.get(f"token:{user_id}")
    if not token:
        raise HTTPException(401, "Token expired")
    
    result = await hh_client.apply_to_vacancy(token, vacancy_id, message)
    
    # Update history
    history = db.query(ResponseHistory).filter(
        ResponseHistory.user_id == user_id,
        ResponseHistory.vacancy_id == vacancy_id
    ).first()
    
    if history:
        history.sent_at = datetime.utcnow()
        db.commit()
    
    return result

@app.get("/api/history")
async def get_history(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get user's application history"""
    history = db.query(ResponseHistory).filter(
        ResponseHistory.user_id == user_id
    ).order_by(ResponseHistory.created_at.desc()).all()
    
    return history
