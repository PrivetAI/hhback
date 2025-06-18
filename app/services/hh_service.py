import json
import re
import asyncio
from typing import Dict, Any, Optional, List
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

    async def search_vacancies_with_details(self, user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search vacancies and load details for each with parallel loading"""
        token = await self.redis_service.get_user_token(user_id)
        if not token:
            raise HTTPException(401, "Token expired")
        
        # Get initial list
        result = await self.hh_client.search_vacancies(token, params)
        
        # Load details for each vacancy
        if "items" in result and result["items"]:
            # Create semaphore to limit concurrent requests (max 5 at a time)
            semaphore = asyncio.Semaphore(5)
            
            async def load_vacancy_details(vacancy: Dict[str, Any]) -> Dict[str, Any]:
                async with semaphore:
                    try:
                        # Check cache first (10 min cache)
                        cache_key = f"vacancy:detail:{vacancy['id']}"
                        cached = await self.redis_service.get_json(cache_key)
                        
                        if cached:
                            return cached
                        
                        # Get full details from API
                        full_vacancy = await self.hh_client.get_vacancy(token, vacancy["id"])
                        
                        # Extract essential fields
                        detail = {
                            "id": full_vacancy["id"],
                            "name": full_vacancy.get("name", ""),
                            "salary": full_vacancy.get("salary"),
                            "employer": full_vacancy.get("employer", {"name": "Не указано"}),
                            "area": full_vacancy.get("area", {"name": "Не указано"}),
                            "published_at": full_vacancy.get("published_at"),
                            "schedule": full_vacancy.get("schedule"),
                            "employment": full_vacancy.get("employment"),
                            "description": self._clean_description(full_vacancy.get("description", "")),
                            "snippet": full_vacancy.get("snippet"),
                            "experience": full_vacancy.get("experience")
                        }
                        
                        # Cache for 10 minutes
                        await self.redis_service.set_json(cache_key, detail, 600)
                        return detail
                        
                    except Exception as e:
                        print(f"Error loading vacancy {vacancy['id']}: {e}")
                        # Return basic info on error
                        return {
                            "id": vacancy["id"],
                            "name": vacancy.get("name", ""),
                            "salary": vacancy.get("salary"),
                            "employer": vacancy.get("employer", {"name": "Не указано"}),
                            "area": vacancy.get("area", {"name": "Не указано"}),
                            "published_at": vacancy.get("published_at"),
                            "snippet": vacancy.get("snippet")
                        }
            
            # Load all details in parallel
            tasks = [load_vacancy_details(vacancy) for vacancy in result["items"]]
            detailed_items = await asyncio.gather(*tasks)
            result["items"] = detailed_items
        
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

    def _clean_description(self, html_text: str) -> str:
        """Clean HTML from description"""
        if not html_text:
            return ""
        clean_text = re.sub('<.*?>', '', html_text)
        # Limit to 500 chars
        return clean_text[:500] + "..." if len(clean_text) > 500 else clean_text
    
    async def warm_cache_next_page(self, user_id: str, params: Dict[str, Any]) -> None:
        """Pre-load next page of results in background"""
        try:
            # Get next page params
            next_params = params.copy()
            next_params["page"] = params.get("page", 0) + 1
            
            # Run in background without waiting
            asyncio.create_task(self.search_vacancies_with_details(user_id, next_params))
        except Exception as e:
            print(f"Cache warming failed: {e}")