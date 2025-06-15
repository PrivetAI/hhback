from openai import AsyncOpenAI
import os
import json

class AIService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def analyze_match(self, resume: dict, vacancy: dict) -> dict:
        prompt = f"""
        Analyze match between candidate and vacancy.
        Resume: {json.dumps(resume, ensure_ascii=False)[:2000]}
        Vacancy: {json.dumps(vacancy, ensure_ascii=False)[:2000]}
        
        Return JSON with:
        - score (0-100)
        - strengths (list)
        - gaps (list)
        - recommendation (string)
        """
        
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    async def generate_cover_letter(self, resume: dict, vacancy: dict) -> dict:
        prompt = f"""
        Generate professional cover letter in Russian.
        Resume: {json.dumps(resume, ensure_ascii=False)[:2000]}
        Vacancy: {json.dumps(vacancy, ensure_ascii=False)[:2000]}
        
        Return JSON with:
        - content (cover letter text)
        - score (match score 0-100)
        """
        
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
