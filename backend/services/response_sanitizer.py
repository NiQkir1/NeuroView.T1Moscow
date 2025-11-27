"""
Санитайзер ответов AI - последняя линия защиты от prompt injection.

Даже если модель обошла системный промпт и попыталась дать ответ/объяснение,
этот модуль перехватит и заблокирует такой ответ.

Принцип: Defense in Depth (многоуровневая защита)
1. Уровень 1: Системный промпт (инструкции модели)
2. Уровень 2: Низкая температура (детерминированность)
3. Уровень 3: Этот санитайзер (постпроцессинг)
"""

import re
from typing import Dict, Any, Tuple, List
from backend.utils.logger import get_module_logger

logger = get_module_logger("ResponseSanitizer")


class ResponseSanitizer:
    """
    Санитайзер для фильтрации нежелательного контента в ответах AI.
    """
    
    # Паттерны, которые указывают на попытку дать ответ/объяснение
    FORBIDDEN_PATTERNS = [
        # Прямые объяснения
        r"давайте\s+(я\s+)?объясню",
        r"давайте\s+(я\s+)?расскажу",
        r"давайте\s+разберем",
        r"позвольте\s+объяснить",
        r"объясню\s+вам",
        r"расскажу\s+вам",
        r"вот\s+как\s+это\s+работает",
        r"это\s+работает\s+так",
        r"суть\s+в\s+том",
        r"простыми\s+словами",
        
        # Ответы на вопросы
        r"правильный\s+ответ",
        r"ответ\s+на\s+ваш\s+вопрос",
        r"отвечая\s+на\s+ваш\s+вопрос",
        r"вот\s+ответ",
        r"ответ\s+такой",
        r"ответ\s+будет",
        
        # Примеры кода
        r"вот\s+пример",
        r"например[,:]",
        r"пример\s+кода",
        r"вот\s+код",
        r"код\s+будет",
        r"можно\s+написать\s+так",
        r"реализация\s+выглядит",
        
        # Код в ответе (блоки кода)
        r"```\s*(python|java|javascript|cpp|c\+\+|go|rust|sql)",
        r"def\s+\w+\s*\(",
        r"class\s+\w+\s*[:\(]",
        r"function\s+\w+\s*\(",
        r"import\s+\w+",
        r"from\s+\w+\s+import",
        
        # Учительский тон
        r"важно\s+понимать",
        r"следует\s+отметить",
        r"обратите\s+внимание",
        r"ключевой\s+момент",
        r"основная\s+идея",
        r"концепция\s+заключается",
        
        # Смена роли (признаки того, что модель "поддалась")
        r"хорошо,\s+я\s+объясню",
        r"ладно,\s+расскажу",
        r"как\s+вы\s+просили",
        r"раз\s+вы\s+настаиваете",
        r"помогу\s+вам\s+разобраться",
        
        # Технические термины в объяснительном контексте
        r"это\s+структура\s+данных",
        r"это\s+алгоритм",
        r"это\s+паттерн",
        r"представляет\s+собой",
        r"используется\s+для",
        r"позволяет\s+решить",
    ]
    
    # Компилируем паттерны для производительности
    COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in FORBIDDEN_PATTERNS]
    
    # Минимальная длина "подозрительного" ответа
    # Короткие ответы типа "0 баллов" безопасны
    SUSPICIOUS_LENGTH_THRESHOLD = 200
    
    # Стандартный безопасный ответ
    SAFE_RESPONSE = {
        "score": 0,
        "correctness": 0,
        "completeness": 0,
        "quality": 0,
        "optimality": 0,
        "feedback": "",
        "is_sanitized": True,
        "sanitize_reason": "Обнаружена попытка обхода ограничений"
    }
    
    @classmethod
    def check_for_violations(cls, text: str) -> Tuple[bool, List[str]]:
        """
        Проверяет текст на наличие запрещенных паттернов.
        
        Args:
            text: Текст для проверки
            
        Returns:
            (is_clean, violations) - True если текст чистый, список нарушений если нет
        """
        if not text or len(text) < 20:
            return True, []
        
        violations = []
        text_lower = text.lower()
        
        for i, pattern in enumerate(cls.COMPILED_PATTERNS):
            if pattern.search(text_lower):
                violations.append(cls.FORBIDDEN_PATTERNS[i])
        
        return len(violations) == 0, violations
    
    @classmethod
    def sanitize_evaluation(cls, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Санитайзит ответ агента оценки.
        
        Если ответ содержит объяснения или подсказки, заменяет его на безопасный.
        
        Args:
            evaluation: Словарь с оценкой от агента
            
        Returns:
            Очищенный словарь с оценкой
        """
        if not evaluation:
            return cls.SAFE_RESPONSE.copy()
        
        # Проверяем feedback
        feedback = evaluation.get("feedback", "")
        is_clean, violations = cls.check_for_violations(feedback)
        
        if not is_clean:
            logger.warning(
                f"[SANITIZER] Обнаружены нарушения в feedback: {violations[:3]}..."
            )
            # Очищаем feedback
            evaluation["feedback"] = ""
            evaluation["is_sanitized"] = True
            evaluation["sanitize_reason"] = f"Удалено объяснение ({len(violations)} нарушений)"
        
        # Проверяем весь ответ (на случай если объяснение в другом поле)
        full_text = str(evaluation)
        if len(full_text) > cls.SUSPICIOUS_LENGTH_THRESHOLD:
            is_clean, violations = cls.check_for_violations(full_text)
            
            if not is_clean:
                logger.warning(
                    f"[SANITIZER] Обнаружены нарушения в полном ответе: {violations[:3]}..."
                )
                # Возвращаем полностью безопасный ответ
                safe = cls.SAFE_RESPONSE.copy()
                # Сохраняем score если он был низким (это хорошо)
                if evaluation.get("score", 100) <= 30:
                    safe["score"] = evaluation["score"]
                return safe
        
        return evaluation
    
    @classmethod
    def sanitize_question(cls, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Санитайзит сгенерированный вопрос.
        
        Убеждается, что в вопросе нет ответа или подсказки.
        
        Args:
            question_data: Данные вопроса
            
        Returns:
            Очищенные данные вопроса
        """
        if not question_data:
            return question_data
        
        question_text = question_data.get("question", "")
        
        # Проверяем, не содержит ли вопрос ответ
        is_clean, violations = cls.check_for_violations(question_text)
        
        if not is_clean:
            logger.warning(
                f"[SANITIZER] Вопрос содержит объяснение: {violations[:2]}..."
            )
            # Это серьезная проблема - вопрос не должен содержать ответ
            # Возвращаем fallback вопрос
            question_data["question"] = "Расскажите о вашем опыте работы с данной технологией."
            question_data["is_sanitized"] = True
        
        return question_data


# Глобальный экземпляр
response_sanitizer = ResponseSanitizer()

