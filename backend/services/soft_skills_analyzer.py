"""
Soft Skills Analyzer Service - анализ мягких навыков кандидата
Mercor AI v2.0.0: Soft Skills и Culture Fit анализ
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import json

from backend.models.interview import InterviewSession, Question, Answer
from backend.services.llm_client import llm_client


class SoftSkillsAnalyzer:
    """Сервис для анализа soft skills кандидата"""
    
    SYSTEM_PROMPT = """Ты эксперт по анализу мягких навыков (soft skills) кандидатов.
Твоя задача - проанализировать ответы кандидата и оценить следующие аспекты:

1. Коммуникативные навыки (communication)
2. Работа в команде (teamwork)
3. Лидерство (leadership)
4. Решение проблем (problem_solving)
5. Адаптивность (adaptability)
6. Эмоциональный интеллект (emotional_intelligence)
7. Тайм-менеджмент (time_management)
8. Критическое мышление (critical_thinking)

Для каждого навыка предоставь:
- Оценку от 0 до 10
- Обоснование оценки
- Примеры из ответов
- Рекомендации по улучшению

Формат ответа: JSON с полями для каждого навыка."""

    async def analyze_answer(
        self,
        question_text: str,
        answer_text: str,
        question_type: str
    ) -> Dict[str, Any]:
        """Анализ одного ответа на предмет soft skills"""
        
        prompt = f"""
Проанализируй ответ кандидата на предмет мягких навыков.

Вопрос: {question_text}
Тип вопроса: {question_type}
Ответ кандидата: {answer_text}

Оцени каждый из следующих навыков (0-10):
- communication: коммуникативные навыки
- teamwork: работа в команде
- leadership: лидерство
- problem_solving: решение проблем
- adaptability: адаптивность
- emotional_intelligence: эмоциональный интеллект
- time_management: тайм-менеджмент
- critical_thinking: критическое мышление

Для каждого навыка предоставь:
- score: оценка (0-10)
- reasoning: обоснование
- evidence: примеры из ответа

Верни результат в формате JSON.
"""
        
        result = await llm_client.generate(prompt, system_prompt=self.SYSTEM_PROMPT)
        response = result.get("content", "")
        
        try:
            # Пытаемся распарсить JSON из ответа
            if isinstance(response, str):
                # Ищем JSON в ответе
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    # Если не нашли JSON, создаем базовую структуру
                    analysis = self._create_default_analysis()
            else:
                analysis = response
        except:
            analysis = self._create_default_analysis()
        
        return analysis
    
    def _create_default_analysis(self) -> Dict[str, Any]:
        """Создание базовой структуры анализа"""
        skills = [
            "communication", "teamwork", "leadership", "problem_solving",
            "adaptability", "emotional_intelligence", "time_management", "critical_thinking"
        ]
        
        return {
            skill: {
                "score": 5.0,
                "reasoning": "Недостаточно данных для оценки",
                "evidence": []
            }
            for skill in skills
        }
    
    async def analyze_session(
        self,
        db: Session,
        session_id: int
    ) -> Dict[str, Any]:
        """Анализ всей сессии интервью на предмет soft skills"""
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        
        if not session:
            raise ValueError("Сессия не найдена")
        
        questions = db.query(Question).filter(
            Question.session_id == session_id
        ).all()
        
        all_analyses = []
        skill_scores = {
            "communication": [],
            "teamwork": [],
            "leadership": [],
            "problem_solving": [],
            "adaptability": [],
            "emotional_intelligence": [],
            "time_management": [],
            "critical_thinking": []
        }
        
        for question in questions:
            if question.answers:
                answer = question.answers[0]
                if answer.answer_text:
                    analysis = await self.analyze_answer(
                        question.question_text,
                        answer.answer_text,
                        question.question_type
                    )
                    all_analyses.append(analysis)
                    
                    # Собираем оценки по навыкам
                    for skill, data in analysis.items():
                        if isinstance(data, dict) and "score" in data:
                            skill_scores[skill].append(data["score"])
        
        # Вычисляем средние оценки
        soft_skills_score = {}
        for skill, scores in skill_scores.items():
            if scores:
                avg_score = sum(scores) / len(scores)
                soft_skills_score[skill] = {
                    "score": avg_score,
                    "level": self._score_to_level(avg_score),
                    "answers_analyzed": len(scores)
                }
            else:
                soft_skills_score[skill] = {
                    "score": 0,
                    "level": "no_data",
                    "answers_analyzed": 0
                }
        
        # Общая оценка soft skills
        if skill_scores:
            all_scores = [score for scores in skill_scores.values() for score in scores]
            overall_score = sum(all_scores) / len(all_scores) if all_scores else 0
        else:
            overall_score = 0
        
        return {
            "overall_score": overall_score,
            "skills": soft_skills_score,
            "detailed_analyses": all_analyses,
            "recommendations": self._generate_recommendations(soft_skills_score)
        }
    
    def _score_to_level(self, score: float) -> str:
        """Преобразование оценки в уровень"""
        if score >= 8:
            return "excellent"
        elif score >= 6:
            return "good"
        elif score >= 4:
            return "average"
        else:
            return "needs_improvement"
    
    def _generate_recommendations(self, skills: Dict[str, Any]) -> List[str]:
        """Генерация рекомендаций на основе анализа"""
        recommendations = []
        
        for skill, data in skills.items():
            if isinstance(data, dict):
                score = data.get("score", 0)
                if score < 5:
                    skill_name = skill.replace("_", " ").title()
                    recommendations.append(
                        f"Рекомендуется улучшить навык '{skill_name}'. "
                        f"Текущая оценка: {score:.1f}/10"
                    )
        
        return recommendations
    
    async def calculate_culture_fit(
        self,
        soft_skills_analysis: Dict[str, Any],
        company_culture: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Расчет соответствия корпоративной культуре
        company_culture: {"teamwork": 0.3, "leadership": 0.2, ...} - веса навыков
        """
        if not company_culture:
            # Дефолтные веса
            company_culture = {
                "communication": 0.2,
                "teamwork": 0.2,
                "leadership": 0.15,
                "problem_solving": 0.15,
                "adaptability": 0.1,
                "emotional_intelligence": 0.1,
                "time_management": 0.05,
                "critical_thinking": 0.05
            }
        
        culture_fit_score = 0.0
        total_weight = 0.0
        
        skills = soft_skills_analysis.get("skills", {})
        
        for skill, weight in company_culture.items():
            if skill in skills:
                skill_data = skills[skill]
                if isinstance(skill_data, dict):
                    score = skill_data.get("score", 0)
                    culture_fit_score += score * weight
                    total_weight += weight
        
        if total_weight > 0:
            return culture_fit_score / total_weight
        else:
            return 0.0


# Глобальный экземпляр
soft_skills_analyzer = SoftSkillsAnalyzer()






