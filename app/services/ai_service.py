class AIService:
    async def analyze_match(self, resume: dict, vacancy: dict) -> dict:
        """Mock AI match analysis"""
        score = 75
        
        if vacancy.get("salary") and vacancy["salary"].get("from", 0) > 200000:
            score += 10
        
        if "senior" in vacancy.get("name", "").lower():
            score -= 5
            
        return {
            "score": min(max(score, 0), 100),
            "strengths": ["Релевантный опыт", "Подходящие навыки"],
            "gaps": ["Может потребоваться изучение новых технологий"],
            "recommendation": "Хорошее соответствие, рекомендуем откликнуться"
        }
    
    async def generate_cover_letter(self, resume: dict, vacancy: dict) -> dict:
        """Mock cover letter generation"""
        company = vacancy.get("employer", {}).get("name", "вашей компании")
        position = vacancy.get("name", "должность")
        
        letter = f"""Здравствуйте!

Меня заинтересовала вакансия "{position}" в {company}.

Мой опыт работы в течение {resume.get('total_experience', {}).get('months', 0) // 12} лет позволит мне эффективно решать поставленные задачи. 

Ключевые навыки, которые помогут в этой роли:
- {', '.join(resume.get('skill_set', ['Профессиональные навыки'])[:3])}

Буду рад обсудить детали сотрудничества на собеседовании.

С уважением,
{resume.get('first_name', '')} {resume.get('last_name', '')}"""
        
        return {
            "content": letter,
            "score": 85
        }