"""
Candidate Profiler Service - анализ и профилирование кандидатов
Mercor AI v2.0.0: Расширенная аналитика кандидатов
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import json

from backend.models.user import User
from backend.services.llm_client import llm_client


class CandidateProfiler:
    """Сервис для анализа и профилирования кандидатов"""
    
    async def analyze_github_profile(self, github_username: str) -> Dict[str, Any]:
        """
        Анализ профиля GitHub кандидата
        В будущем: интеграция с GitHub API
        """
        # TODO: Реальная интеграция с GitHub API
        # Пока возвращаем структуру для будущей реализации
        return {
            "username": github_username,
            "repositories": [],
            "languages": [],
            "contributions": 0,
            "stars": 0,
            "analysis": {
                "code_quality": None,
                "activity_level": None,
                "tech_stack": []
            }
        }
    
    async def analyze_linkedin_profile(self, linkedin_url: str) -> Dict[str, Any]:
        """
        Анализ профиля LinkedIn кандидата
        В будущем: интеграция с LinkedIn API (с соблюдением ToS)
        """
        # TODO: Реальная интеграция с LinkedIn API
        return {
            "url": linkedin_url,
            "experience": [],
            "education": [],
            "skills": [],
            "recommendations": 0
        }
    
    async def extract_skills_from_interviews(
        self,
        db: Session,
        user_id: int
    ) -> List[str]:
        """Извлечение навыков из истории интервью кандидата"""
        from backend.models.interview import InterviewSession, Question, Answer
        
        sessions = db.query(InterviewSession).filter(
            InterviewSession.candidate_id == user_id
        ).all()
        
        skills = set()
        for session in sessions:
            questions = db.query(Question).filter(
                Question.session_id == session.id
            ).all()
            
            for question in questions:
                if question.topic:
                    skills.add(question.topic)
                if question.expected_keywords:
                    for keyword in question.expected_keywords:
                        if isinstance(keyword, str):
                            skills.add(keyword)
        
        return sorted(list(skills))
    
    async def build_skill_matrix(
        self,
        db: Session,
        user_id: int
    ) -> Dict[str, Any]:
        """Построение матрицы навыков на основе интервью"""
        from backend.models.interview import InterviewSession, Question, Answer
        
        from backend.models.interview import InterviewStatus
        sessions = db.query(InterviewSession).filter(
            InterviewSession.candidate_id == user_id,
            InterviewSession.status == InterviewStatus.COMPLETED
        ).all()
        
        skill_scores = {}
        
        for session in sessions:
            questions = db.query(Question).join(Answer).filter(
                Question.session_id == session.id
            ).all()
            
            for question in questions:
                if question.answers:
                    answer = question.answers[0]
                    if answer.score is not None:
                        skill = question.topic or "general"
                        if skill not in skill_scores:
                            skill_scores[skill] = []
                        skill_scores[skill].append(answer.score)
        
        # Вычисляем средние оценки по навыкам
        skill_matrix = {}
        for skill, scores in skill_scores.items():
            avg_score = sum(scores) / len(scores) if scores else 0
            skill_matrix[skill] = {
                "score": avg_score,
                "questions_count": len(scores),
                "level": self._score_to_level(avg_score)
            }
        
        return skill_matrix
    
    def _score_to_level(self, score: float) -> str:
        """Преобразование оценки в уровень"""
        if score >= 80:
            return "expert"
        elif score >= 60:
            return "advanced"
        elif score >= 40:
            return "intermediate"
        else:
            return "beginner"
    
    async def update_candidate_profile(
        self,
        db: Session,
        user_id: int,
        github_username: Optional[str] = None,
        linkedin_url: Optional[str] = None
    ) -> User:
        """Обновление профиля кандидата с данными из внешних источников"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("Пользователь не найден")
        
        # Обновляем внешние профили
        if github_username:
            user.github_username = github_username
            github_data = await self.analyze_github_profile(github_username)
            if not user.external_profiles:
                user.external_profiles = {}
            user.external_profiles["github"] = github_data
        
        if linkedin_url:
            user.linkedin_url = linkedin_url
            linkedin_data = await self.analyze_linkedin_profile(linkedin_url)
            if not user.external_profiles:
                user.external_profiles = {}
            user.external_profiles["linkedin"] = linkedin_data
        
        # Извлекаем навыки из интервью
        skills = await self.extract_skills_from_interviews(db, user_id)
        user.skills = skills
        
        # Строим матрицу навыков
        skill_matrix = await self.build_skill_matrix(db, user_id)
        user.skill_matrix = skill_matrix
        
        db.commit()
        db.refresh(user)
        
        return user


# Глобальный экземпляр
candidate_profiler = CandidateProfiler()






