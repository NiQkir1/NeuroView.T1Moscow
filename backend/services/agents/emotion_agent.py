"""
Агент для анализа эмоционального состояния кандидата
Анализирует текст ответов и получает данные от GigaAM emo
"""
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.services.agents.base_agent import BaseAgent


class EmotionAgent(BaseAgent):
    """Агент для анализа эмоционального состояния кандидата"""
    
    SYSTEM_PROMPT = """Ты опытный психолог-аналитик, специализирующийся на анализе эмоционального состояния кандидатов на собеседовании.
Твоя задача:
1. Анализировать текстовые ответы кандидата на предмет эмоционального состояния
2. Интегрировать данные от GigaAM emo (анализ голоса/видео)
3. Делать выводы о текущем эмоциональном состоянии кандидата
4. Оценивать влияние эмоций на качество ответов
5. Предоставлять рекомендации для отчета

Эмоциональные состояния, которые ты анализируешь:
- Уверенность/неуверенность
- Стресс/напряжение
- Энтузиазм/мотивация
- Спокойствие/тревожность
- Усталость/энергичность

Формат ответа: JSON с полями:
- overall_state: общее эмоциональное состояние
- confidence_level: уровень уверенности (0-10)
- stress_level: уровень стресса (0-10)
- engagement_level: уровень вовлеченности (0-10)
- emotions_detected: список обнаруженных эмоций
- text_analysis: анализ текста
- voice_analysis: анализ голоса (из GigaAM emo)
- combined_analysis: объединенный анализ
- recommendations: рекомендации для отчета"""
    
    def __init__(self, model_override=None):
        super().__init__("EmotionAgent", self.SYSTEM_PROMPT, model_override=model_override)
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализ эмоционального состояния
        
        Args:
            input_data: {
                "text": str,  # Текстовый ответ кандидата
                "emotions": dict,  # Данные от GigaAM emo
                "context": dict (опционально)  # Контекст интервью
            }
        
        Returns:
            Результат анализа эмоций
        """
        text = input_data.get("text", "")
        emotions = input_data.get("emotions", {})  # Данные от GigaAM emo
        context = input_data.get("context", {})
        
        # Формируем промпт для анализа
        emotions_str = json.dumps(emotions, ensure_ascii=False) if emotions else "Нет данных"
        context_str = json.dumps(context, ensure_ascii=False) if context else "Нет контекста"
        
        prompt = f"""Проанализируй эмоциональное состояние кандидата на основе текстового ответа и данных от GigaAM emo.

Текстовый ответ кандидата:
{text}

Данные от GigaAM emo (анализ голоса/видео):
{emotions_str}

Контекст интервью:
{context_str}

Выполни комплексный анализ:
1. Проанализируй текст на предмет эмоциональных маркеров
2. Интегрируй данные от GigaAM emo
3. Сделай вывод о текущем эмоциональном состоянии
4. Оцени влияние эмоций на качество ответа
5. Предоставь рекомендации для отчета

Формат ответа: JSON с полями:
- overall_state: общее эмоциональное состояние (confident, stressed, engaged, calm, tired, etc.)
- confidence_level: уровень уверенности (0-10)
- stress_level: уровень стресса (0-10)
- engagement_level: уровень вовлеченности (0-10)
- emotions_detected: массив обнаруженных эмоций с их интенсивностью
- text_analysis: детальный анализ текста
- voice_analysis: анализ данных от GigaAM emo
- combined_analysis: объединенный анализ текста и голоса
- impact_on_performance: влияние эмоций на качество ответа
- recommendations: рекомендации для HR/интервьюера"""
        
        response = await self.invoke(prompt)
        
        # Парсинг JSON ответа
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Базовый анализ, если не удалось распарсить JSON
            result = {
                "overall_state": "neutral",
                "confidence_level": 5,
                "stress_level": 5,
                "engagement_level": 5,
                "emotions_detected": [],
                "text_analysis": response,
                "voice_analysis": emotions_str,
                "combined_analysis": "Не удалось выполнить полный анализ",
                "impact_on_performance": "Неизвестно",
                "recommendations": [],
            }
        
        return {
            "overall_state": result.get("overall_state", "neutral"),
            "confidence_level": result.get("confidence_level", 5),
            "stress_level": result.get("stress_level", 5),
            "engagement_level": result.get("engagement_level", 5),
            "emotions_detected": result.get("emotions_detected", []),
            "text_analysis": result.get("text_analysis", ""),
            "voice_analysis": result.get("voice_analysis", emotions_str),
            "combined_analysis": result.get("combined_analysis", ""),
            "impact_on_performance": result.get("impact_on_performance", ""),
            "recommendations": result.get("recommendations", []),
            "analyzed_at": datetime.utcnow().isoformat(),
        }
    
    async def analyze_interview_session(
        self,
        answers: List[Dict[str, Any]],
        emotions_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Анализ всей сессии интервью
        
        Args:
            answers: Список ответов кандидата
            emotions_history: История эмоций от GigaAM emo
        
        Returns:
            Общий анализ сессии
        """
        # Объединяем все ответы
        all_text = "\n\n".join([answer.get("text", "") for answer in answers])
        
        # Объединяем все эмоции
        all_emotions = {}
        if emotions_history:
            # Агрегируем эмоции (можно использовать среднее, максимум и т.д.)
            for emotion_data in emotions_history:
                for key, value in emotion_data.items():
                    if key not in all_emotions:
                        all_emotions[key] = []
                    all_emotions[key].append(value)
            
            # Вычисляем средние значения
            for key in all_emotions:
                values = all_emotions[key]
                if isinstance(values[0], (int, float)):
                    all_emotions[key] = sum(values) / len(values)
        
        return await self.process({
            "text": all_text,
            "emotions": all_emotions,
            "context": {
                "total_answers": len(answers),
                "session_type": "full_interview",
            }
        })














