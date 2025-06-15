from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class VacancyResponse(BaseModel):
    id: str
    name: str
    employer: dict
    snippet: Optional[dict]

class ResumeResponse(BaseModel):
    id: str
    title: str
    total_experience: Optional[dict]

class CoverLetterRequest(BaseModel):
    vacancy_id: str
    
class MatchAnalysis(BaseModel):
    score: int
    strengths: List[str]
    gaps: List[str]
    recommendation: str

class CoverLetter(BaseModel):
    content: str
    score: int
