import json
import re
from typing import Dict, Any, Optional
from fastapi import HTTPException
from .hh_client import HHClient
from .redis_service import RedisService
from .ai_service import AIService

class HHService:
    def __init__(self):
        self.hh_client = HHClient()
        self.redis_service = RedisService()
        self.ai_service = AIService()

    async def get_user_resume(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's resume with caching"""
        cached = await self.redis_service.get_json(f"resume:{user_id}")
        if cached:
            return cached
        
        token = await self.redis_service.get_user_token(user_id)
        if not token:
            raise HTTPException(401, "Token expired")
        
        resume = await self.hh_client.get_resume(token)
        if resume:
            await self.redis_service.set_json(f"resume:{user_id}", resume, 3600)
        return resume

    async def search_vacancies(self, user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search vacancies with filters"""
        token = await self.redis_service.get_user_token(user_id)
        if not token:
            raise HTTPException(401, "Token expired")
        
        result = await self.hh_client.search_vacancies(token, params)
        
        # Normalize response
        if "items" in result:
            for vacancy in result["items"]:
                if "employer" not in vacancy:
                    vacancy["employer"] = {"name": "Не указано"}
                if "area" not in vacancy:
                    vacancy["area"] = {"name": "Не указано"}
                if "salary" not in vacancy:
                    vacancy["salary"] = None
        
        return result

    async def get_vacancy_details(self, user_id: str, vacancy_id: str) -> Dict[str, Any]:
        """Get full vacancy details with caching"""
        cache_key = f"vacancy:full:{vacancy_id}"
        cached = await self.redis_service.get_json(cache_key)
        if cached:
            return cached
        
        token = await self.redis_service.get_user_token(user_id)
        if not token:
            raise HTTPException(401, "Token expired")
        
        vacancy = await self.hh_client.get_vacancy(token, vacancy_id)
        
        # Extract clean description
        description = ""
        if vacancy.get("description"):
            clean_text = re.sub('<.*?>', '', vacancy["description"])
            description = clean_text[:500] + "..." if len(clean_text) > 500 else clean_text
        
        result = {
            "id": vacancy["id"],
            "name": vacancy.get("name", ""),
            "description": description,
            "schedule": vacancy.get("schedule", {}).get("name", "") if vacancy.get("schedule") else "",
            "employment": vacancy.get("employment", {}).get("name", "") if vacancy.get("employment") else "",
            "published_at": vacancy.get("published_at", ""),
            "salary": vacancy.get("salary"),
            "employer": vacancy.get("employer", {"name": "Не указано"}),
            "area": vacancy.get("area", {"name": "Не указано"}),
            "snippet": vacancy.get("snippet")
        }
        
        await self.redis_service.set_json(cache_key, result, 86400)
        return result

    async def get_dictionaries(self) -> Dict[str, Any]:
        """Get HH dictionaries with caching"""
        cached = await self.redis_service.get_json("dictionaries")
        if cached:
            return cached
        
        data = await self.hh_client.get_dictionaries()
        result = {
            "experience": data.get("experience", []),
            "employment": data.get("employment", []),
            "schedule": data.get("schedule", [])
        }
        
        await self.redis_service.set_json("dictionaries", result, 604800)
        return result

    async def get_areas(self) -> Dict[str, Any]:
        """Get areas with caching"""
        cached = await self.redis_service.get_json("areas")
        if cached:
            return cached
        
        data = await self.hh_client.get_areas()
        await self.redis_service.set_json("areas", data, 604800)
        return data

    async def analyze_vacancy_match(self, user_id: str, vacancy_id: str) -> Dict[str, Any]:
        """Analyze match between resume and vacancy"""
        cache_key = f"analysis:{user_id}:{vacancy_id}"
        cached = await self.redis_service.get_json(cache_key)
        if cached:
            return cached
        
        token = await self.redis_service.get_user_token(user_id)
        if not token:
            raise HTTPException(401, "Token expired")
        
        resume = await self.get_user_resume(user_id)
        vacancy = await self.hh_client.get_vacancy(token, vacancy_id)
        
        score = await self.ai_service.analyze_match(resume, vacancy)
        await self.redis_service.set_json(cache_key, score, 86400)
        return score

    async def generate_cover_letter(self, user_id: str, vacancy_id: str) -> Dict[str, Any]:
        """Generate cover letter for vacancy"""
        token = await self.redis_service.get_user_token(user_id)
        if not token:
            raise HTTPException(401, "Token expired")
        
        resume = await self.get_user_resume(user_id)
        vacancy = await self.hh_client.get_vacancy(token, vacancy_id)
        
        return await self.ai_service.generate_cover_letter(resume, vacancy)

    async def apply_to_vacancy(self, user_id: str, vacancy_id: str, message: str) -> Dict[str, Any]:
        """Apply to vacancy"""
        token = await self.redis_service.get_user_token(user_id)
        if not token:
            raise HTTPException(401, "Token expired")
        
        return await self.hh_client.apply_to_vacancy(token, vacancy_id, message)