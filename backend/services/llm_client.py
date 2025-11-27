"""
Клиент для работы с SciBox LLM
"""
import asyncio
from typing import Optional, Dict, Any

import openai

from backend.config import (
    llm_config,
    get_scibox_config,
)


class LLMClient:
    """Клиент для работы с SciBox LLM"""
    
    def __init__(self):
        self.scibox_client: Optional[openai.AsyncOpenAI] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Инициализация клиента SciBox"""
        try:
            scibox_config = get_scibox_config()
            if scibox_config:
                self.scibox_client = openai.AsyncOpenAI(
                    api_key=scibox_config["api_key"],
                    base_url=scibox_config["base_url"],
                    timeout=scibox_config["timeout"],
                )
            else:
                self.scibox_client = None
        except Exception:
            self.scibox_client = None
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Генерация ответа от SciBox LLM
        
        Args:
            prompt: Пользовательский промпт
            system_prompt: Системный промпт
            **kwargs: Дополнительные параметры (temperature, max_tokens, top_p)
        
        Returns:
            Словарь с ответом и метаданными
        """
        for attempt in range(llm_config.retry_attempts):
            try:
                return await self._generate_scibox(prompt, system_prompt, **kwargs)
            except Exception as e:
                if attempt < llm_config.retry_attempts - 1:
                    await asyncio.sleep(llm_config.retry_delay * (attempt + 1))
                    continue
                raise Exception(f"Ошибка генерации после {llm_config.retry_attempts} попыток: {e}")
        
        raise Exception("Не удалось сгенерировать ответ")
    
    async def _generate_scibox(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Генерация через SciBox (OpenAI-совместимый API)"""
        if not self.scibox_client:
            # Используем мок, если клиент не инициализирован
            return await self._generate_mock(prompt, system_prompt, "scibox")
        
        config = get_scibox_config()
        messages = []
        
        if system_prompt:
            # Добавляем маркер /no_think если reasoning отключен
            final_system_prompt = system_prompt
            if not config.get("enable_reasoning", False) and not system_prompt.startswith("/no_think"):
                final_system_prompt = f"/no_think {system_prompt}"
            messages.append({"role": "system", "content": final_system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = await self.scibox_client.chat.completions.create(
            model=config["model"],
            messages=messages,
            temperature=kwargs.get("temperature", config["temperature"]),
            max_tokens=kwargs.get("max_tokens", config["max_tokens"]),
            top_p=kwargs.get("top_p", 0.9),  # SciBox поддерживает top_p
        )
        
        return {
            "content": response.choices[0].message.content,
            "provider": "scibox",
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
        }
    
    async def _generate_mock(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        provider: str = "scibox"
    ) -> Dict[str, Any]:
        """Мок-генерация для работы без API ключей"""
        from backend.services.mock_responses import get_mock_question, get_mock_evaluation
        import json
        
        await asyncio.sleep(0.1)  # Минимальная задержка для имитации сети
        
        # Определяем тип запроса
        prompt_lower = prompt.lower()
        
        # СНАЧАЛА проверяем оценку (потому что "вопрос" может быть в обоих промптах)
        is_evaluation = "оцен" in prompt_lower or "evaluat" in prompt_lower or "ОТВЕТ КАНДИДАТА" in prompt
        
        # Генерация вопроса (только если это НЕ оценка)
        if not is_evaluation and ("сгенерируй" in prompt_lower or "generate" in prompt_lower):
            # Извлекаем тему из промпта
            topic = "programming"
            for t in ["algorithms", "data_structures", "python", "programming"]:
                if t in prompt_lower:
                    topic = t
                    break
            
            question = get_mock_question(topic)
            mock_response = json.dumps({
                "question": question,
                "type": "coding" if "реализуйте" in question.lower() or "напишите" in question.lower() else "theory",
                "expected_keywords": ["массив", "функция", "алгоритм"] if topic == "programming" else [],
                "hints": ["Используйте цикл", "Проверьте граничные случаи"],
            }, ensure_ascii=False)
        
        # Оценка ответа
        elif is_evaluation:
            # Пытаемся извлечь вопрос и ответ из промпта
            question = ""
            answer = ""
            
            # Парсим вопрос
            if "Вопрос:" in prompt:
                parts = prompt.split("Вопрос:")
                if len(parts) > 1:
                    question = parts[1].split("\n")[0].strip()
            
            # Парсим ответ кандидата (разные форматы)
            # Формат: === ОТВЕТ КАНДИДАТА ... === ... === КОНЕЦ ОТВЕТА ===
            import re
            # Ищем текст между маркерами
            match = re.search(r'===\s*ОТВЕТ КАНДИДАТА.*?===\s*\n(.*?)\n===\s*КОНЕЦ', prompt, re.DOTALL | re.IGNORECASE)
            if match:
                answer = match.group(1).strip()
            elif "Ответ кандидата:" in prompt:
                parts = prompt.split("Ответ кандидата:")
                if len(parts) > 1:
                    answer = parts[1].split("\n\n")[0].strip()
            
            if not answer:
                answer = prompt[-300:]  # Fallback
            
            evaluation = get_mock_evaluation(question, answer)
            mock_response = json.dumps(evaluation, ensure_ascii=False)
        
        # Общий ответ для чата
        else:
            # Генерируем более реалистичные ответы для чата
            prompt_lower = prompt.lower()
            
            # Простые ответы на основе ключевых слов
            if any(word in prompt_lower for word in ["привет", "hello", "hi", "здравствуй"]):
                mock_response = "Здравствуйте! К сожалению, LLM сервис сейчас недоступен. Я могу помочь с базовыми вопросами, но для полноценного интервью необходимо настроить API ключ SciBox."
            elif any(word in prompt_lower for word in ["помощь", "help", "подсказка", "hint"]):
                mock_response = "К сожалению, LLM сервис сейчас недоступен. Для получения подсказок и помощи необходимо настроить API ключ SciBox в backend/.env файле."
            elif any(word in prompt_lower for word in ["задача", "task", "вопрос", "question"]):
                mock_response = "К сожалению, LLM сервис сейчас недоступен. Я не могу сгенерировать задачу. Пожалуйста, настройте API ключ SciBox для полной функциональности."
            elif any(word in prompt_lower for word in ["спасибо", "thanks", "thank"]):
                mock_response = "Пожалуйста! К сожалению, из-за недоступности LLM сервиса я не могу полноценно помочь. Настройте API ключ SciBox для продолжения."
            elif len(prompt) < 10 or prompt.isdigit():
                # Короткие сообщения типа "1", "да", "нет"
                mock_response = "Понял. К сожалению, LLM сервис сейчас недоступен. Для полноценного общения необходимо настроить API ключ SciBox."
            else:
                # Общий ответ для других сообщений
                mock_response = "Спасибо за ваше сообщение. К сожалению, LLM сервис сейчас недоступен. Для получения ответов и помощи необходимо настроить API ключ SciBox в backend/.env файле."
        
        return {
            "content": mock_response,
            "provider": f"{provider}-mock",
            "model": "demo-mode",
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(mock_response.split()),
                "total_tokens": len(prompt.split()) + len(mock_response.split()),
            },
        }


# Глобальный экземпляр клиента
llm_client = LLMClient()

