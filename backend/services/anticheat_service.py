"""
Централизованный сервис античита для анализа подозрительной активности
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from backend.models.interview import InterviewSession, Answer, Question, InterviewStatus
from backend.services.ai_detection import ai_detection_service
from backend.utils.logger import get_module_logger

logger = get_module_logger("AnticheatService")


class AnticheatService:
    """Централизованный сервис античита"""
    
    def __init__(self):
        self.ai_detection = ai_detection_service
    
    async def analyze_session(self, session_id: int, db: Session) -> Dict[str, Any]:
        """
        Комплексный анализ сессии на читерство
        
        Args:
            session_id: ID сессии
            db: Сессия БД
        
        Returns:
            Результаты анализа с оценкой подозрительности
        """
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        
        if not session:
            raise ValueError("Session not found")
        
        suspicion_factors = []
        total_score = 0.0
        
        # 1. Анализ активности браузера
        if session.activity_history:
            activity_score = self._analyze_activity(session.activity_history)
            if activity_score > 0.3:
                suspicion_factors.append({
                    "type": "suspicious_activity",
                    "score": activity_score,
                    "description": "Обнаружена подозрительная активность браузера"
                })
                total_score += activity_score * 0.3
        
        # 2. Анализ времени ответов
        answers = db.query(Answer).join(Question).filter(
            Question.session_id == session_id
        ).all()
        
        if answers:
            time_score = self._analyze_response_times(answers)
            if time_score > 0.3:
                suspicion_factors.append({
                    "type": "suspicious_timing",
                    "score": time_score,
                    "description": "Подозрительно быстрое время ответов"
                })
                total_score += time_score * 0.2
        
        # 3. Анализ AI-детекции
        if session.ai_detection_results:
            ai_score = session.ai_detection_results.get("ai_probability", 0)
            if ai_score > 0.5:
                suspicion_factors.append({
                    "type": "ai_usage",
                    "score": ai_score,
                    "description": "Высокая вероятность использования AI-помощников",
                    "indicators": session.ai_detection_results.get("indicators", [])
                })
                total_score += ai_score * 0.3
        
        # 4. Проверка множественных устройств
        if session.concurrent_sessions:
            concurrent_count = len(session.concurrent_sessions) if isinstance(session.concurrent_sessions, list) else 1
            if concurrent_count > 0:
                total_score += 0.2
                suspicion_factors.append({
                    "type": "multiple_devices",
                    "score": 0.8,
                    "description": f"Обнаружено {concurrent_count} одновременных сессий",
                    "concurrent_sessions": session.concurrent_sessions
                })
        
        # 5. Анализ паттернов печати
        if session.typing_metrics:
            typing_score = self._analyze_typing_patterns(session.typing_metrics)
            if typing_score > 0.5:
                suspicion_factors.append({
                    "type": "suspicious_typing",
                    "score": typing_score,
                    "description": "Подозрительные паттерны печати"
                })
                total_score += typing_score * 0.1
        
        # Обновляем suspicion_score в сессии
        final_score = min(total_score, 1.0)
        session.suspicion_score = final_score
        
        # SQLAlchemy не отслеживает изменения в JSON полях автоматически
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "suspicion_score")
        
        db.commit()
        
        return {
            "suspicion_score": round(final_score, 3),
            "factors": suspicion_factors,
            "recommendation": self._get_recommendation(final_score),
            "analysis_date": datetime.utcnow().isoformat()
        }
    
    def _analyze_activity(self, activity_history: List[Dict]) -> float:
        """
        Анализ активности на подозрительность
        
        Args:
            activity_history: История активности
        
        Returns:
            Оценка подозрительности активности (0-1)
        """
        if not activity_history:
            return 0.0
        
        score = 0.0
        
        # Подсчет различных типов активности
        tab_switches = sum(1 for a in activity_history if a.get("type") == "visibility_change" and a.get("details", {}).get("hidden"))
        focus_losses = sum(1 for a in activity_history if a.get("type") == "focus_change" and not a.get("details", {}).get("focused", True))
        copy_events = sum(1 for a in activity_history if a.get("type") == "copy")
        paste_events = sum(1 for a in activity_history if a.get("type") == "paste")
        
        # Переключение вкладок более 3 раз - подозрительно
        if tab_switches > 3:
            score += 0.3
        elif tab_switches > 1:
            score += 0.15
        
        # Потеря фокуса более 5 раз - подозрительно
        if focus_losses > 5:
            score += 0.2
        elif focus_losses > 2:
            score += 0.1
        
        # Копирование/вставка - подозрительно, если происходит часто
        if copy_events > 0 or paste_events > 0:
            if copy_events + paste_events > 2:
                score += 0.5
            else:
                score += 0.2
        
        # Анализ временных паттернов
        if len(activity_history) > 5:
            # Если много активности в короткий период - подозрительно
            timestamps = [a.get("timestamp", 0) for a in activity_history if isinstance(a.get("timestamp"), (int, float))]
            if timestamps:
                time_span = max(timestamps) - min(timestamps)
                if time_span > 0:
                    activity_rate = len(activity_history) / (time_span / 1000)  # событий в секунду
                    if activity_rate > 2:  # Более 2 событий в секунду
                        score += 0.15
        
        return min(score, 1.0)
    
    def _analyze_response_times(self, answers: List[Answer]) -> float:
        """
        Анализ времени ответов
        
        Args:
            answers: Список ответов
        
        Returns:
            Оценка подозрительности по времени (0-1)
        """
        if not answers:
            return 0.0
        
        # Фильтруем ответы с временем
        answers_with_time = [a for a in answers if a.time_to_answer is not None and a.time_to_answer > 0]
        
        if len(answers_with_time) < 2:
            return 0.0
        
        # Подсчет подозрительно быстрых ответов
        fast_answers = sum(1 for a in answers_with_time if a.time_to_answer < 10)
        very_fast_answers = sum(1 for a in answers_with_time if a.time_to_answer < 5)
        
        ratio = fast_answers / len(answers_with_time)
        very_fast_ratio = very_fast_answers / len(answers_with_time)
        
        score = 0.0
        
        # Если более 50% ответов слишком быстрые - подозрительно
        if ratio > 0.5:
            score += 0.5
        elif ratio > 0.3:
            score += 0.3
        
        # Если есть очень быстрые ответы на сложные вопросы
        if very_fast_ratio > 0.2:
            score += 0.3
        
        # Анализ скорости печати
        typing_speeds = [a.typing_speed for a in answers_with_time if a.typing_speed and a.typing_speed > 0]
        if typing_speeds:
            avg_typing_speed = sum(typing_speeds) / len(typing_speeds)
            # Нормальная скорость: 150-250 символов/минуту (30-50 WPM)
            # Подозрительно высокая: > 400 символов/минуту (80 WPM)
            if avg_typing_speed > 400:
                score += 0.2
        
        return min(score, 1.0)
    
    def _analyze_typing_patterns(self, typing_metrics: Dict[str, Any]) -> float:
        """
        Анализ паттернов печати
        
        Args:
            typing_metrics: Метрики печати
        
        Returns:
            Оценка подозрительности (0-1)
        """
        score = 0.0
        
        # Проверка на слишком равномерную скорость печати (признак копирования)
        if "variance" in typing_metrics:
            variance = typing_metrics["variance"]
            # Очень низкая вариативность - подозрительно
            if variance < 100:
                score += 0.3
        
        # Проверка на слишком высокую скорость
        if "average_speed" in typing_metrics:
            speed = typing_metrics["average_speed"]
            if speed > 500:  # Более 500 символов/минуту (100 WPM)
                score += 0.4
        
        return min(score, 1.0)
    
    def _get_recommendation(self, score: float) -> str:
        """
        Рекомендация на основе оценки подозрительности
        
        Args:
            score: Оценка подозрительности (0-1)
        
        Returns:
            Рекомендация
        """
        if score < 0.3:
            return "low_risk"
        elif score < 0.6:
            return "medium_risk"
        else:
            return "high_risk"
    
    async def log_activity(
        self,
        session_id: int,
        activity_type: str,
        details: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """
        Логирование активности пользователя
        
        Args:
            session_id: ID сессии
            activity_type: Тип активности
            details: Детали активности
            db: Сессия БД
            
        Returns:
            Словарь с результатами: warning_count, should_terminate, message
        """
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        
        if not session:
            logger.warning(f"Session {session_id} not found for activity logging")
            return {"warning_count": 0, "should_terminate": False}
        
        # Добавляем активность в историю
        activity_history = session.activity_history or []
        activity_history.append({
            "type": activity_type,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        })
        
        session.activity_history = activity_history
        
        # SQLAlchemy не отслеживает изменения в JSON полях автоматически
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "activity_history")
        
        # Проверяем на подозрительную активность (переключение вкладок)
        should_terminate = False
        warning_issued = False
        
        if activity_type == "visibility_change" and details.get("hidden") is True:
            # Увеличиваем счетчик предупреждений
            session.warning_count = (session.warning_count or 0) + 1
            warning_issued = True
            
            if session.warning_count > 2:
                # Превышен лимит предупреждений - завершаем интервью
                should_terminate = True
                logger.error(f"Session {session_id} exceeded warning limit ({session.warning_count}), should be terminated")
            else:
                logger.warning(f"Warning {session.warning_count}/2 issued for session {session_id}")
        
        db.commit()
        
        # Проверяем на подозрительную активность
        if len(activity_history) > 0:
            activity_score = self._analyze_activity(activity_history)
            if activity_score > 0.5:
                # Обновляем suspicion_score
                current_score = session.suspicion_score or 0.0
                session.suspicion_score = min(current_score + 0.1, 1.0)
                flag_modified(session, "suspicion_score")
                db.commit()
                logger.warning(f"High activity suspicion detected for session {session_id}: {activity_score}")
        
        return {
            "warning_count": session.warning_count or 0,
            "should_terminate": should_terminate,
            "warning_issued": warning_issued
        }


# Глобальный экземпляр
anticheat_service = AnticheatService()




