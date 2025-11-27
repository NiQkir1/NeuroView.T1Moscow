"""
Adaptive Difficulty Engine v4.2.0 - адаптивная система подбора сложности

Возможности:
- Определение начального уровня кандидата
- Динамическая подстройка сложности вопросов
- Анализ прогресса кандидата
- Рекомендации по следующим вопросам
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.models.interview import Question, Answer, InterviewSession
from backend.utils.logger import get_module_logger

logger = get_module_logger("AdaptiveDifficultyEngine")


class AdaptiveDifficultyEngine:
    """Движок адаптивной сложности"""
    
    # Уровни сложности
    DIFFICULTY_LEVELS = ["easy", "medium", "hard", "expert"]
    
    # Пороговые значения для перехода между уровнями
    THRESHOLDS = {
        "easy_to_medium": 75,      # 75%+ правильных ответов -> переход на medium
        "medium_to_hard": 80,       # 80%+ -> переход на hard
        "hard_to_expert": 85,       # 85%+ -> переход на expert
        "drop_to_easy": 40,         # <40% -> возврат на easy
        "drop_to_medium": 50,       # <50% -> возврат на medium
        "drop_to_hard": 60,         # <60% -> возврат на hard
    }
    
    def __init__(self):
        pass
    
    async def determine_initial_level(
        self,
        db: Session,
        session_id: int
    ) -> str:
        """
        Определяет начальный уровень кандидата на основе первых вопросов
        
        Args:
            db: Database session
            session_id: ID сессии интервью
        
        Returns:
            Рекомендуемый уровень сложности
        """
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        
        if not session:
            return "medium"  # Дефолтный уровень
        
        # Получаем первые 3 ответа
        answers = db.query(Answer).join(Question).filter(
            Question.session_id == session_id,
            Question.topic != "ready_check"  # Исключаем вопрос готовности
        ).limit(3).all()
        
        if len(answers) < 2:
            # Недостаточно данных, используем дефолтный или из конфигурации
            interview = session.interview
            if interview and interview.interview_config:
                return interview.interview_config.get("level", "medium")
            return "medium"
        
        # Рассчитываем среднюю оценку
        scores = [a.score for a in answers if a.score is not None]
        if not scores:
            return "medium"
        
        avg_score = sum(scores) / len(scores)
        
        # Определяем уровень на основе оценки
        if avg_score >= 85:
            return "expert"
        elif avg_score >= 70:
            return "hard"
        elif avg_score >= 50:
            return "medium"
        else:
            return "easy"
    
    async def analyze_performance(
        self,
        db: Session,
        session_id: int,
        recent_questions: int = 5
    ) -> Dict[str, Any]:
        """
        Анализирует производительность кандидата
        
        Args:
            db: Database session
            session_id: ID сессии
            recent_questions: Количество последних вопросов для анализа
        
        Returns:
            Анализ производительности
        """
        # Получаем последние ответы
        answers = db.query(Answer).join(Question).filter(
            Question.session_id == session_id,
            Question.topic != "ready_check"
        ).order_by(Question.order.desc()).limit(recent_questions).all()
        
        if not answers:
            return {
                "average_score": 0,
                "trend": "stable",
                "consistency": 0,
                "recommendations": []
            }
        
        # Рассчитываем метрики
        scores = [a.score for a in answers if a.score is not None]
        if not scores:
            return {
                "average_score": 0,
                "trend": "stable",
                "consistency": 0,
                "recommendations": []
            }
        
        avg_score = sum(scores) / len(scores)
        
        # Определяем тренд (растет, падает, стабильный)
        trend = "stable"
        if len(scores) >= 3:
            first_half = scores[:len(scores)//2]
            second_half = scores[len(scores)//2:]
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
            
            if avg_second > avg_first + 10:
                trend = "improving"
            elif avg_second < avg_first - 10:
                trend = "declining"
        
        # Рассчитываем consistency (стандартное отклонение)
        if len(scores) > 1:
            mean = sum(scores) / len(scores)
            variance = sum((x - mean) ** 2 for x in scores) / len(scores)
            std_dev = variance ** 0.5
            consistency = max(0, 100 - std_dev)  # 100 = очень стабильно, 0 = очень нестабильно
        else:
            consistency = 100
        
        # Формируем рекомендации
        recommendations = []
        if trend == "declining":
            recommendations.append("Снизить сложность вопросов")
        elif trend == "improving" and avg_score >= 80:
            recommendations.append("Увеличить сложность вопросов")
        
        if consistency < 50:
            recommendations.append("Кандидат демонстрирует нестабильные результаты")
        
        return {
            "average_score": round(avg_score, 1),
            "trend": trend,
            "consistency": round(consistency, 1),
            "recommendations": recommendations,
            "recent_scores": scores,
        }
    
    async def suggest_next_difficulty(
        self,
        db: Session,
        session_id: int,
        current_difficulty: str
    ) -> str:
        """
        Предлагает сложность для следующего вопроса
        
        Args:
            db: Database session
            session_id: ID сессии
            current_difficulty: Текущая сложность
        
        Returns:
            Рекомендуемая сложность
        """
        # Анализируем производительность
        performance = await self.analyze_performance(db, session_id, recent_questions=3)
        
        avg_score = performance["average_score"]
        trend = performance["trend"]
        
        # Определяем индекс текущей сложности
        try:
            current_idx = self.DIFFICULTY_LEVELS.index(current_difficulty)
        except ValueError:
            current_idx = 1  # medium по умолчанию
        
        # Решаем, нужно ли изменить сложность
        new_idx = current_idx
        
        # Повышаем сложность если:
        # 1. Средний балл высокий
        # 2. Тренд улучшается
        if avg_score >= self.THRESHOLDS["hard_to_expert"] and trend in ["improving", "stable"]:
            new_idx = min(current_idx + 1, len(self.DIFFICULTY_LEVELS) - 1)
        elif avg_score >= self.THRESHOLDS["medium_to_hard"] and trend in ["improving", "stable"]:
            new_idx = min(current_idx + 1, len(self.DIFFICULTY_LEVELS) - 1)
        elif avg_score >= self.THRESHOLDS["easy_to_medium"] and current_difficulty == "easy":
            new_idx = min(current_idx + 1, len(self.DIFFICULTY_LEVELS) - 1)
        
        # Понижаем сложность если:
        # 1. Средний балл низкий
        # 2. Тренд ухудшается
        elif avg_score < self.THRESHOLDS["drop_to_easy"] and trend == "declining":
            new_idx = 0  # Возврат на easy
        elif avg_score < self.THRESHOLDS["drop_to_medium"] and current_difficulty in ["hard", "expert"]:
            new_idx = max(current_idx - 1, 0)
        elif avg_score < self.THRESHOLDS["drop_to_hard"] and current_difficulty == "expert":
            new_idx = max(current_idx - 1, 0)
        
        new_difficulty = self.DIFFICULTY_LEVELS[new_idx]
        
        if new_difficulty != current_difficulty:
            logger.info(
                f"Адаптация сложности для сессии {session_id}: "
                f"{current_difficulty} -> {new_difficulty} (avg_score={avg_score}, trend={trend})"
            )
        
        return new_difficulty
    
    async def get_adaptive_question_config(
        self,
        db: Session,
        session_id: int,
        topic: str
    ) -> Dict[str, Any]:
        """
        Возвращает конфигурацию для генерации следующего вопроса с адаптивной сложностью
        
        Args:
            db: Database session
            session_id: ID сессии
            topic: Тема вопроса
        
        Returns:
            Конфигурация вопроса
        """
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        
        if not session:
            return {"difficulty": "medium", "topic": topic}
        
        # Получаем текущую сложность из последнего вопроса
        last_question = db.query(Question).filter(
            Question.session_id == session_id,
            Question.topic != "ready_check"
        ).order_by(Question.order.desc()).first()
        
        current_difficulty = last_question.difficulty if last_question else "medium"
        
        # Предлагаем следующую сложность
        next_difficulty = await self.suggest_next_difficulty(
            db, session_id, current_difficulty
        )
        
        # Анализируем производительность
        performance = await self.analyze_performance(db, session_id)
        
        return {
            "difficulty": next_difficulty,
            "topic": topic,
            "performance_analysis": performance,
            "adaptive_mode": True,
        }


# Глобальный экземпляр
adaptive_difficulty_engine = AdaptiveDifficultyEngine()

