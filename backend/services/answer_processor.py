"""
Сервис для фоновой обработки и структурирования ответов кандидатов
Обрабатывает ответы асинхронно, структурирует их для удобства чтения в отчетах
"""
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from backend.models import Answer, Question
from backend.services.ai_engine import ai_engine
from backend.utils.logger import get_module_logger

logger = get_module_logger("AnswerProcessor")


class AnswerProcessor:
    """Сервис для обработки и структурирования ответов"""
    
    def __init__(self):
        self.ai_engine = ai_engine
        self._processing_queue = asyncio.Queue()
        self._is_processing = False
    
    async def process_answer_async(
        self,
        db: Session,
        answer_id: int,
        question_text: str,
        answer_text: str,
        question_type: str
    ):
        """
        Асинхронная обработка ответа для структурирования
        
        Args:
            db: Сессия БД
            answer_id: ID ответа
            question_text: Текст вопроса
            answer_text: Текст ответа
            question_type: Тип вопроса (introduction, technical, etc.)
        """
        try:
            logger.info(f"[ANSWER_PROCESSOR] Начало фоновой обработки ответа {answer_id}")
            
            # Структурируем ответ через AI
            structured_data = await self._structure_answer(
                question_text=question_text,
                answer_text=answer_text,
                question_type=question_type
            )
            
            # Обновляем ответ в БД с структурированными данными
            answer = db.query(Answer).filter(Answer.id == answer_id).first()
            if answer:
                # Добавляем структурированные данные в evaluation
                if not answer.evaluation:
                    answer.evaluation = {}
                
                answer.evaluation["structured_answer"] = structured_data
                db.commit()
                logger.info(f"[ANSWER_PROCESSOR] Ответ {answer_id} успешно структурирован")
            else:
                logger.warning(f"[ANSWER_PROCESSOR] Ответ {answer_id} не найден в БД")
                
        except Exception as e:
            logger.error(f"[ANSWER_PROCESSOR] Ошибка при обработке ответа {answer_id}: {e}", exc_info=True)
    
    async def _structure_answer(
        self,
        question_text: str,
        answer_text: str,
        question_type: str
    ) -> Dict[str, Any]:
        """
        Структурирование ответа для удобства чтения в отчете
        
        Args:
            question_text: Текст вопроса
            answer_text: Текст ответа
            question_type: Тип вопроса
            
        Returns:
            Структурированные данные ответа
        """
        try:
            # Формируем промпт для структурирования
            prompt = f"""Структурируй ответ кандидата для удобства чтения в отчете.

Вопрос: {question_text}
Ответ кандидата: {answer_text}
Тип вопроса: {question_type}

Твоя задача:
1. Извлечь ключевые моменты из ответа
2. Структурировать информацию в понятном виде
3. Выделить важные детали (опыт, навыки, проекты, достижения)
4. Сократить до сути, сохраняя важное

ПРАВИЛА:
⚠️ НЕ ПРИДУМЫВАЙ информацию - используй ТОЛЬКО то, что написал кандидат
⚠️ Если ответ пустой или односложный - так и укажи
⚠️ Если кандидат пропустил вопрос - укажи "Вопрос пропущен"
⚠️ Сохраняй факты и цифры из оригинального ответа

Формат ответа: JSON с полями:
- summary: краткое резюме ответа (1-2 предложения)
- key_points: массив ключевых моментов (каждый - 1 предложение)
- details: объект с детализированной информацией:
  * experience: упомянутый опыт (если есть)
  * skills: упомянутые навыки (если есть)
  * projects: упомянутые проекты (если есть)
  * achievements: упомянутые достижения (если есть)
- quality: оценка качества ответа (poor/fair/good/excellent)
- original_length: длина оригинального ответа в символах"""

            # Вызываем AI для структурирования
            response = await self.ai_engine.llm_client.generate(
                prompt=prompt,
                system_prompt="Ты эксперт по структурированию информации. Твоя задача - извлекать и организовывать ключевую информацию из текстов."
            )
            
            # Парсим JSON ответ
            try:
                structured_data = json.loads(response.get("content", "{}"))
                structured_data["processed_at"] = datetime.utcnow().isoformat()
                return structured_data
            except json.JSONDecodeError:
                # Если не удалось распарсить JSON, возвращаем базовую структуру
                logger.warning("[ANSWER_PROCESSOR] Не удалось распарсить JSON ответ от AI")
                return {
                    "summary": answer_text[:200] if len(answer_text) > 200 else answer_text,
                    "key_points": [answer_text],
                    "details": {},
                    "quality": "fair",
                    "original_length": len(answer_text),
                    "processed_at": datetime.utcnow().isoformat(),
                    "processing_error": "Failed to parse AI response"
                }
                
        except Exception as e:
            logger.error(f"[ANSWER_PROCESSOR] Ошибка при структурировании ответа: {e}", exc_info=True)
            # Возвращаем базовую структуру при ошибке
            return {
                "summary": answer_text[:200] if len(answer_text) > 200 else answer_text,
                "key_points": [answer_text],
                "details": {},
                "quality": "unknown",
                "original_length": len(answer_text),
                "processed_at": datetime.utcnow().isoformat(),
                "processing_error": str(e)
            }
    
    def schedule_processing(
        self,
        db: Session,
        answer_id: int,
        question_text: str,
        answer_text: str,
        question_type: str
    ):
        """
        Запланировать фоновую обработку ответа
        
        Args:
            db: Сессия БД
            answer_id: ID ответа
            question_text: Текст вопроса
            answer_text: Текст ответа
            question_type: Тип вопроса
        """
        # Создаем фоновую задачу (fire and forget)
        asyncio.create_task(
            self.process_answer_async(
                db=db,
                answer_id=answer_id,
                question_text=question_text,
                answer_text=answer_text,
                question_type=question_type
            )
        )
        logger.info(f"[ANSWER_PROCESSOR] Запланирована обработка ответа {answer_id}")


# Глобальный экземпляр процессора
answer_processor = AnswerProcessor()




