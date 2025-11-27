"""
Сервис для детекции использования AI-помощников в ответах кандидатов
"""
import re
from typing import Dict, Any, List


class AIDetectionService:
    """Сервис для детекции использования AI-помощников"""
    
    # Типичные фразы AI-моделей (русский и английский)
    AI_PHRASES = [
        # Русский
        "как я уже упоминал",
        "в контексте",
        "следует отметить",
        "важно понимать",
        "необходимо подчеркнуть",
        "стоит отметить",
        "следует обратить внимание",
        "важно отметить",
        "необходимо отметить",
        "в данном контексте",
        "в рамках данного вопроса",
        "исходя из вышесказанного",
        # Английский
        "as i mentioned",
        "in the context of",
        "it's worth noting",
        "it's important to understand",
        "it should be noted",
        "it is worth noting",
        "in this context",
        "within the framework",
        "based on the above",
        "it is important to note",
    ]
    
    # Паттерны слишком идеальных формулировок
    PERFECT_PATTERNS = [
        r"во-первых.*во-вторых.*в-третьих",
        r"с одной стороны.*с другой стороны",
        r"firstly.*secondly.*thirdly",
        r"on one hand.*on the other hand",
        r"в первую очередь.*во вторую очередь.*в третью очередь",
    ]
    
    # Фразы, указывающие на отсутствие личного опыта
    GENERIC_PHRASES = [
        "как правило",
        "обычно",
        "как известно",
        "generally",
        "usually",
        "as is known",
        "typically",
    ]
    
    def detect_ai_usage(self, answer: str, question: str = "") -> Dict[str, Any]:
        """
        Детекция использования AI в ответе
        
        Args:
            answer: Ответ кандидата
            question: Текст вопроса (опционально)
        
        Returns:
            Словарь с результатами детекции
        """
        if not answer or len(answer.strip()) < 10:
            return {
                "ai_probability": 0.0,
                "indicators": [],
                "is_suspicious": False,
                "confidence": "low"
            }
        
        score = 0.0
        indicators = []
        answer_lower = answer.lower()
        
        # 1. Проверка на типичные фразы AI
        ai_phrases_found = []
        for phrase in self.AI_PHRASES:
            if phrase.lower() in answer_lower:
                ai_phrases_found.append(phrase)
                score += 0.08  # Каждая фраза добавляет 8%
        
        if ai_phrases_found:
            indicators.append({
                "type": "ai_phrases",
                "phrases": ai_phrases_found,
                "count": len(ai_phrases_found),
                "severity": "medium" if len(ai_phrases_found) < 3 else "high"
            })
        
        # 2. Проверка на слишком структурированные ответы
        perfect_structure_count = 0
        for pattern in self.PERFECT_PATTERNS:
            matches = len(re.findall(pattern, answer, re.IGNORECASE | re.DOTALL))
            if matches > 0:
                perfect_structure_count += matches
                score += 0.15 * matches
        
        if perfect_structure_count > 0:
            indicators.append({
                "type": "perfect_structure",
                "count": perfect_structure_count,
                "severity": "high"
            })
        
        # 3. Проверка на несоответствие сложности вопроса и ответа
        if question:
            question_complexity = self._analyze_complexity(question)
            answer_complexity = self._analyze_complexity(answer)
            
            if answer_complexity > question_complexity * 1.5 and question_complexity > 0.3:
                score += 0.12
                indicators.append({
                    "type": "complexity_mismatch",
                    "question_complexity": round(question_complexity, 2),
                    "answer_complexity": round(answer_complexity, 2),
                    "severity": "medium"
                })
        
        # 4. Проверка на отсутствие личного опыта
        personal_indicators = ["я", "мне", "мой", "в моем", "я работал", "я использовал", 
                              "i", "my", "me", "i worked", "i used", "i have"]
        has_personal = any(indicator in answer_lower for indicator in personal_indicators)
        
        generic_phrases_count = sum(1 for phrase in self.GENERIC_PHRASES if phrase in answer_lower)
        
        if not has_personal and len(answer) > 100:
            score += 0.10
            indicators.append({
                "type": "no_personal_experience",
                "severity": "low"
            })
        
        if generic_phrases_count > 2:
            score += 0.08
            indicators.append({
                "type": "too_many_generic_phrases",
                "count": generic_phrases_count,
                "severity": "medium"
            })
        
        # 5. Проверка на слишком идеальную грамматику и структуру
        sentence_count = answer.count('.') + answer.count('!') + answer.count('?')
        if sentence_count > 0:
            avg_sentence_length = len(answer.split()) / sentence_count
            # Слишком длинные предложения (более 25 слов) - признак AI
            if avg_sentence_length > 25:
                score += 0.10
                indicators.append({
                    "type": "overly_complex_sentences",
                    "avg_length": round(avg_sentence_length, 1),
                    "severity": "medium"
                })
        
        # 6. Проверка на повторяющиеся структуры
        # AI часто использует одинаковые конструкции
        sentences = re.split(r'[.!?]+', answer)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        if len(sentences) > 3:
            # Проверяем на похожие начала предложений
            sentence_starts = [s.split()[0:3] for s in sentences[:5]]
            unique_starts = len(set(str(s) for s in sentence_starts))
            if len(sentence_starts) > unique_starts * 1.5:
                score += 0.08
                indicators.append({
                    "type": "repetitive_structure",
                    "severity": "low"
                })
        
        # Нормализуем score до 1.0
        final_score = min(score, 1.0)
        
        # Определяем уровень уверенности
        if final_score < 0.3:
            confidence = "low"
        elif final_score < 0.6:
            confidence = "medium"
        else:
            confidence = "high"
        
        return {
            "ai_probability": round(final_score, 3),
            "indicators": indicators,
            "is_suspicious": final_score > 0.5,
            "confidence": confidence,
            "analysis_date": self._get_timestamp()
        }
    
    def _analyze_complexity(self, text: str) -> float:
        """
        Анализ сложности текста
        
        Returns:
            Оценка сложности от 0.0 до 1.0
        """
        if not text or len(text.strip()) == 0:
            return 0.0
        
        words = text.split()
        sentences = text.count('.') + text.count('!') + text.count('?')
        
        if len(words) == 0:
            return 0.0
        
        # Средняя длина предложения
        if sentences > 0:
            avg_sentence_length = len(words) / sentences
        else:
            avg_sentence_length = len(words)
        
        # Сложные слова (длинные слова)
        complex_words = sum(1 for word in words if len(word) > 8)
        complex_ratio = complex_words / len(words) if words else 0
        
        # Комбинированная метрика сложности
        complexity = (
            min(avg_sentence_length / 25.0, 1.0) * 0.6 +
            min(complex_ratio * 2, 1.0) * 0.4
        )
        
        return min(complexity, 1.0)
    
    def _get_timestamp(self) -> str:
        """Получение текущего timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()


# Глобальный экземпляр
ai_detection_service = AIDetectionService()




