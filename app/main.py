from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Dict, Any

from .core.database import get_db, engine
from .core.auth import get_current_user_id
from .api.routers.user import router as user_router
from .services.auth_service import AuthService
from .services.hh_service import HHService
from models.db_models import Base, ResponseHistory

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="HH Job Application API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
auth_service = AuthService()
hh_service = HHService()

# Include routers
app.include_router(user_router)

@app.get("/")
async def root():
    return {"message": "HH Job Application API"}

@app.get("/auth/hh")
async def hh_auth():
    return {
        "url": "https://hh.ru/oauth/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:3000"
    }

@app.post("/auth/callback")
async def auth_callback(code: str):
    return await auth_service.handle_oauth_callback(code)

@app.get("/api/vacancies")
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
    token = await redis_client.get(f"token:{user_id}")
    if not token:
        raise HTTPException(401, "Token expired")
    
    # Build params for HH API
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
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{hh_client.base_url}/vacancies",
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()

@app.get("/api/vacancy/{vacancy_id}")
async def get_vacancy_details(
    vacancy_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get full vacancy details with caching"""
    token = await redis_client.get(f"token:{user_id}")
    if not token:
        raise HTTPException(401, "Token expired")
    
    # Check cache first
    cache_key = f"vacancy:full:{vacancy_id}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Get from HH API
    vacancy = await hh_client.get_vacancy(token, vacancy_id)
    
    # Extract description (first 500 chars)
    description = ""
    if vacancy.get("description"):
        # Remove HTML tags
        import re
        clean_text = re.sub('<.*?>', '', vacancy["description"])
        description = clean_text[:500] + "..." if len(clean_text) > 500 else clean_text
    
    # Prepare response with needed fields
    result = {
        "id": vacancy["id"],
        "description": description,
        "schedule": vacancy.get("schedule", {}).get("name", ""),
        "employment": vacancy.get("employment", {}).get("name", ""),
        "published_at": vacancy.get("published_at", "")
    }
    
    # Cache for 24 hours
    await redis_client.setex(cache_key, 86400, json.dumps(result))
    
    return result

@app.get("/api/dictionaries")
async def get_dictionaries():
    """Get HH dictionaries for filters"""
    # Check cache
    cached = await redis_client.get("dictionaries")
    if cached:
        return json.loads(cached)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{hh_client.base_url}/dictionaries")
        data = response.json()
        
        # Extract needed dictionaries
        result = {
            "experience": data.get("experience", []),
            "employment": data.get("employment", []),
            "schedule": data.get("schedule", [])
        }
        
        # Cache for 1 week
        await redis_client.setex("dictionaries", 604800, json.dumps(result))
        
        return result

@app.get("/api/areas")
async def get_areas():
    """Get areas (cities) for filters"""
    # Check cache
    cached = await redis_client.get("areas")
    if cached:
        return json.loads(cached)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{hh_client.base_url}/areas")
        data = response.json()
        
        # Cache for 1 week
        await redis_client.setex("areas", 604800, json.dumps(data))
        
        return data