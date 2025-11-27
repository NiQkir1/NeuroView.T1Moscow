"""
Prediction Engine - прогнозирование успешности кандидата
Mercor AI v2.0.0: Прогнозирование успешности кандидата
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta


class PredictionEngine:
    """Сервис для прогнозирования успешности кандидата"""
    
    async def predict_success(
        self,
        db: Session,
        user_id: int,
        job_requirements: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Прогнозирование успешности кандидата на основе:
        - Истории интервью
        - Оценок soft skills
        - Соответствия требованиям вакансии
        - Исторических данных (если доступны)
        """
        from backend.models.user import User
        from backend.models.interview import InterviewSession, Question, Answer
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("Пользователь не найден")
        
        # Собираем данные о кандидате
        from backend.models.interview import InterviewStatus
        sessions = db.query(InterviewSession).filter(
            InterviewSession.candidate_id == user_id,
            InterviewSession.status == InterviewStatus.COMPLETED
        ).all()
        
        if not sessions:
            return {
                "success_probability": 0.5,
                "confidence": 0.1,
                "factors": {
                    "insufficient_data": True
                },
                "recommendations": ["Недостаточно данных для прогноза. Проведите больше интервью."]
            }
        
        # Анализ технических навыков
        technical_score = self._calculate_technical_score(db, sessions)
        
        # Анализ soft skills
        soft_skills_score = user.soft_skills_score or {}
        if isinstance(soft_skills_score, dict):
            soft_skills_avg = self._calculate_soft_skills_avg(soft_skills_score)
        else:
            soft_skills_avg = 5.0
        
        # Анализ стабильности результатов
        consistency_score = self._calculate_consistency(db, sessions)
        
        # Анализ прогресса
        progress_score = self._calculate_progress(db, sessions)
        
        # Соответствие требованиям вакансии
        job_fit_score = 5.0
        if job_requirements:
            job_fit_score = self._calculate_job_fit(
                user, technical_score, soft_skills_avg, job_requirements
            )
        
        # Расчет общей вероятности успеха
        weights = {
            "technical": 0.35,
            "soft_skills": 0.25,
            "consistency": 0.15,
            "progress": 0.10,
            "job_fit": 0.15
        }
        
        success_probability = (
            technical_score * weights["technical"] +
            soft_skills_avg * weights["soft_skills"] +
            consistency_score * weights["consistency"] +
            progress_score * weights["progress"] +
            job_fit_score * weights["job_fit"]
        ) / 10.0  # Нормализация к 0-1
        
        # Уверенность в прогнозе
        confidence = min(len(sessions) * 0.15, 1.0)  # Больше сессий = больше уверенности
        
        # Факторы влияния
        factors = {
            "technical_skills": {
                "score": technical_score,
                "weight": weights["technical"],
                "impact": "high" if technical_score >= 7 else "medium" if technical_score >= 5 else "low"
            },
            "soft_skills": {
                "score": soft_skills_avg,
                "weight": weights["soft_skills"],
                "impact": "high" if soft_skills_avg >= 7 else "medium" if soft_skills_avg >= 5 else "low"
            },
            "consistency": {
                "score": consistency_score,
                "weight": weights["consistency"],
                "impact": "high" if consistency_score >= 7 else "medium"
            },
            "progress": {
                "score": progress_score,
                "weight": weights["progress"],
                "impact": "positive" if progress_score > 5 else "neutral"
            },
            "job_fit": {
                "score": job_fit_score,
                "weight": weights["job_fit"],
                "impact": "high" if job_fit_score >= 7 else "medium" if job_fit_score >= 5 else "low"
            }
        }
        
        # Рекомендации
        recommendations = self._generate_recommendations(
            success_probability, factors, technical_score, soft_skills_avg
        )
        
        # Прогноз retention (вероятность удержания)
        retention_probability = self._predict_retention(
            technical_score, soft_skills_avg, consistency_score
        )
        
        # Прогноз производительности (первые 6 месяцев)
        performance_forecast = self._forecast_performance(
            technical_score, soft_skills_avg
        )
        
        return {
            "success_probability": round(success_probability, 2),
            "confidence": round(confidence, 2),
            "retention_probability": round(retention_probability, 2),
            "performance_forecast": performance_forecast,
            "factors": factors,
            "recommendations": recommendations,
            "risk_level": self._calculate_risk_level(success_probability),
            "sessions_analyzed": len(sessions)
        }
    
    def _calculate_technical_score(
        self,
        db: Session,
        sessions: List
    ) -> float:
        """Расчет средней технической оценки"""
        from backend.models.interview import Question, Answer
        
        all_scores = []
        for session in sessions:
            if session.total_score is not None:
                all_scores.append(session.total_score)
            else:
                # Вычисляем из ответов
                questions = db.query(Question).filter(
                    Question.session_id == session.id
                ).all()
                for question in questions:
                    if question.answers:
                        answer = question.answers[0]
                        if answer.score is not None:
                            all_scores.append(answer.score)
        
        if all_scores:
            return sum(all_scores) / len(all_scores)
        return 5.0
    
    def _calculate_soft_skills_avg(self, soft_skills_score: Dict[str, Any]) -> float:
        """Расчет средней оценки soft skills"""
        if not soft_skills_score:
            return 5.0
        
        skills = soft_skills_score.get("skills", {})
        if not skills:
            return 5.0
        
        scores = []
        for skill_data in skills.values():
            if isinstance(skill_data, dict):
                score = skill_data.get("score", 0)
                scores.append(score)
        
        if scores:
            return sum(scores) / len(scores)
        return 5.0
    
    def _calculate_consistency(
        self,
        db: Session,
        sessions: List
    ) -> float:
        """Расчет стабильности результатов"""
        if len(sessions) < 2:
            return 5.0
        
        scores = []
        for session in sessions:
            if session.total_score is not None:
                scores.append(session.total_score)
        
        if len(scores) < 2:
            return 5.0
        
        # Вычисляем стандартное отклонение (чем меньше, тем стабильнее)
        mean = sum(scores) / len(scores)
        variance = sum((x - mean) ** 2 for x in scores) / len(scores)
        std_dev = variance ** 0.5
        
        # Преобразуем в оценку (меньше отклонение = выше оценка)
        # Максимальное отклонение 50 -> оценка 0, минимальное 0 -> оценка 10
        consistency_score = max(0, 10 - (std_dev / 5))
        
        return consistency_score
    
    def _calculate_progress(
        self,
        db: Session,
        sessions: List
    ) -> float:
        """Расчет прогресса кандидата"""
        if len(sessions) < 2:
            return 5.0
        
        # Сортируем по дате
        sorted_sessions = sorted(sessions, key=lambda s: s.created_at)
        
        scores = []
        for session in sorted_sessions:
            if session.total_score is not None:
                scores.append(session.total_score)
        
        if len(scores) < 2:
            return 5.0
        
        # Линейная регрессия для определения тренда
        n = len(scores)
        x = list(range(n))
        y = scores
        
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
        
        # Преобразуем slope в оценку (положительный тренд = выше оценка)
        progress_score = 5.0 + (slope * 10)  # Нормализация
        progress_score = max(0, min(10, progress_score))
        
        return progress_score
    
    def _calculate_job_fit(
        self,
        user: Any,
        technical_score: float,
        soft_skills_avg: float,
        job_requirements: Dict[str, Any]
    ) -> float:
        """Расчет соответствия требованиям вакансии"""
        required_skills = job_requirements.get("required_skills", [])
        required_soft_skills = job_requirements.get("required_soft_skills", [])
        
        # Проверяем технические навыки
        user_skills = user.skills or []
        skill_match = 0.0
        if required_skills:
            matched_skills = [s for s in required_skills if s in user_skills]
            skill_match = len(matched_skills) / len(required_skills) * 10
        
        # Проверяем soft skills
        soft_skills_match = soft_skills_avg  # Упрощенная версия
        
        # Комбинируем
        job_fit = (skill_match * 0.6 + soft_skills_match * 0.4)
        
        return job_fit
    
    def _generate_recommendations(
        self,
        success_probability: float,
        factors: Dict[str, Any],
        technical_score: float,
        soft_skills_avg: float
    ) -> List[str]:
        """Генерация рекомендаций"""
        recommendations = []
        
        if success_probability >= 0.7:
            recommendations.append("Высокая вероятность успеха. Кандидат хорошо подходит для позиции.")
        elif success_probability >= 0.5:
            recommendations.append("Средняя вероятность успеха. Рекомендуется дополнительное обучение.")
        else:
            recommendations.append("Низкая вероятность успеха. Требуется значительная подготовка.")
        
        if technical_score < 6:
            recommendations.append("Рекомендуется улучшить технические навыки.")
        
        if soft_skills_avg < 6:
            recommendations.append("Рекомендуется развить мягкие навыки (коммуникация, работа в команде).")
        
        return recommendations
    
    def _predict_retention(
        self,
        technical_score: float,
        soft_skills_avg: float,
        consistency_score: float
    ) -> float:
        """Прогноз вероятности удержания кандидата"""
        # Комбинируем факторы
        retention = (
            technical_score * 0.3 +
            soft_skills_avg * 0.4 +
            consistency_score * 0.3
        ) / 10.0
        
        return min(1.0, max(0.0, retention))
    
    def _forecast_performance(
        self,
        technical_score: float,
        soft_skills_avg: float
    ) -> Dict[str, Any]:
        """Прогноз производительности в первые 6 месяцев"""
        avg_score = (technical_score + soft_skills_avg) / 2
        
        if avg_score >= 8:
            performance_level = "excellent"
            months_to_peak = 2
        elif avg_score >= 6:
            performance_level = "good"
            months_to_peak = 3
        elif avg_score >= 4:
            performance_level = "average"
            months_to_peak = 4
        else:
            performance_level = "below_average"
            months_to_peak = 6
        
        return {
            "expected_level": performance_level,
            "months_to_peak_performance": months_to_peak,
            "estimated_score_6months": min(10, avg_score + 1)  # Ожидаемый рост
        }
    
    def _calculate_risk_level(self, success_probability: float) -> str:
        """Расчет уровня риска"""
        if success_probability >= 0.7:
            return "low"
        elif success_probability >= 0.5:
            return "medium"
        else:
            return "high"


# Глобальный экземпляр
prediction_engine = PredictionEngine()






