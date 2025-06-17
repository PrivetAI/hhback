from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

# Request models
class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ApplyRequest(BaseModel):
    message: str

# Response models
class AuthResponse(BaseModel):
    token: str
    refresh_token: Optional[str] = None
    user: Dict[str, Any]

class ResumeResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    title: str
    total_experience: Optional[Dict[str, Any]] = None
    skill_set: Optional[List[str]] = None

class Dictionaries(BaseModel):
    experience: List[Dict[str, str]]
    employment: List[Dict[str, str]]
    schedule: List[Dict[str, str]]

class ResponseHistoryItem(BaseModel):
    id: int
    vacancy_id: str
    vacancy_title: str
    cover_letter: str
    match_score: int
    created_at: datetime
    sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class MatchAnalysis(BaseModel):
    score: int
    strengths: List[str]
    gaps: List[str]
    recommendation: str

class CoverLetter(BaseModel):
    content: str
    score: int