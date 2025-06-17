import httpx
import os
from fastapi import HTTPException

class HHClient:
    def __init__(self):
        self.client_id = os.getenv("HH_CLIENT_ID")
        self.client_secret = os.getenv("HH_CLIENT_SECRET")
        self.base_url = "https://api.hh.ru"
    
    async def get_dictionaries(self):
        """Get HH dictionaries"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/dictionaries")
            response.raise_for_status()
            return response.json()
    
    async def get_areas(self):
        """Get areas (cities/regions)"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/areas")
            response.raise_for_status()
            return response.json()
    
    async def exchange_code_for_token(self, code: str) -> dict:
        """Exchange OAuth code for access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://hh.ru/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": "http://localhost:3000"
                }
            )
            
            if response.status_code != 200:
                error_data = response.json()
                raise HTTPException(
                    status_code=400,
                    detail=f"HH OAuth error: {error_data.get('error_description', 'Unknown error')}"
                )
            
            data = response.json()
            if "access_token" not in data:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid response from HH: no access_token"
                )
            
            return data
    
    async def get_user_info(self, token: str) -> dict:
        """Get user information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to get user info from HH"
                )
            
            return response.json()
    
    async def get_resume(self, token: str) -> dict:
        """Get user's resume"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/resumes/mine",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code != 200:
                return None
                
            resume_list = response.json()
            
            if resume_list.get("items"):
                resume_id = resume_list["items"][0]["id"]
                response = await client.get(
                    f"{self.base_url}/resumes/{resume_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if response.status_code == 200:
                    return response.json()
            return None
    
    async def search_vacancies(self, token: str, params: dict) -> dict:
        """Search vacancies"""
        async with httpx.AsyncClient() as client:
            if 'per_page' not in params:
                params['per_page'] = 50
            if 'page' not in params:
                params['page'] = 0
                
            response = await client.get(
                f"{self.base_url}/vacancies",
                params=params,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_vacancy(self, token: str, vacancy_id: str) -> dict:
        """Get vacancy details"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/vacancies/{vacancy_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            return response.json()
    
    async def apply_to_vacancy(self, token: str, vacancy_id: str, message: str) -> dict:
        """Apply to vacancy"""
        async with httpx.AsyncClient() as client:
            resume = await self.get_resume(token)
            if not resume:
                raise HTTPException(400, "No resume found")
            
            response = await client.post(
                f"{self.base_url}/negotiations",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "vacancy_id": vacancy_id,
                    "resume_id": resume["id"],
                    "message": message
                }
            )
            
            if response.status_code != 201:
                error = response.json()
                raise HTTPException(
                    status_code=400,
                    detail=error.get("description", "Failed to apply")
                )
                
            return response.json()