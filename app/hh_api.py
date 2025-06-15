import httpx
import os

class HHClient:
    def __init__(self):
        self.client_id = os.getenv("HH_CLIENT_ID")
        self.client_secret = os.getenv("HH_CLIENT_SECRET")
        self.base_url = "https://api.hh.ru"
    
    async def exchange_code_for_token(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://hh.ru/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code
                }
            )
            return response.json()
    
    async def get_user_info(self, token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            return response.json()
    
    async def get_resume(self, token: str) -> dict:
        async with httpx.AsyncClient() as client:
            # Get resume list
            resumes = await client.get(
                f"{self.base_url}/resumes/mine",
                headers={"Authorization": f"Bearer {token}"}
            )
            resume_list = resumes.json()
            
            if resume_list["items"]:
                # Get detailed resume
                resume_id = resume_list["items"][0]["id"]
                response = await client.get(
                    f"{self.base_url}/resumes/{resume_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                return response.json()
            return None
    
    async def search_vacancies(self, token: str, page: int = 0, per_page: int = 20) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/vacancies",
                params={"page": page, "per_page": per_page},
                headers={"Authorization": f"Bearer {token}"}
            )
            return response.json()
    
    async def get_vacancy(self, token: str, vacancy_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/vacancies/{vacancy_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            return response.json()
    
    async def apply_to_vacancy(self, token: str, vacancy_id: str, message: str) -> dict:
        async with httpx.AsyncClient() as client:
            # Get resume id first
            resume = await self.get_resume(token)
            if not resume:
                raise Exception("No resume found")
            
            response = await client.post(
                f"{self.base_url}/negotiations",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "vacancy_id": vacancy_id,
                    "resume_id": resume["id"],
                    "message": message
                }
            )
            return response.json()
