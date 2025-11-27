"""
Базовый класс для агентов LangChain
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    # Fallback для старых версий
    from langchain.chat_models import ChatOpenAI

from backend.config import llm_config, get_scibox_config


class BaseAgent(ABC):
    """Базовый класс для всех агентов интервью"""
    
    def __init__(self, agent_name: str, system_prompt: str, model_override: Optional[str] = None, 
                 enable_streaming: Optional[bool] = None, enable_reasoning: Optional[bool] = None):
        self.agent_name = agent_name
        self.system_prompt = system_prompt
        self.model_override = model_override
        self.enable_streaming = enable_streaming  # None = использовать из конфига
        self.enable_reasoning = enable_reasoning  # None = использовать из конфига
        self.llm = self._initialize_llm()
        self.prompt_template = self._create_prompt_template()
    
    def _initialize_llm(self):
        """Инициализация LLM для агента (SciBox через OpenAI-совместимый API)"""
        scibox_config = get_scibox_config()
        
        if scibox_config and scibox_config.get("api_key"):
            # SciBox использует OpenAI-совместимый API, поэтому используем ChatOpenAI с base_url
            # Используем переопределённую модель если указана, иначе из конфига
            model = self.model_override if self.model_override else scibox_config["model"]
            
            # Определяем параметр streaming (приоритет: явно указанный > из конфига)
            streaming = self.enable_streaming if self.enable_streaming is not None else scibox_config.get("stream", False)
            
            try:
                return ChatOpenAI(
                    model=model,
                    temperature=scibox_config["temperature"],
                    max_tokens=scibox_config["max_tokens"],
                    api_key=scibox_config["api_key"],
                    base_url=scibox_config["base_url"],
                    streaming=streaming,
                )
            except Exception:
                pass  # Fallback на мок
        
        # Если API ключи не установлены, возвращаем None - будет использован мок в invoke
        return None
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Создание шаблона промпта"""
        # Определяем, нужно ли добавить маркер /no_think
        scibox_config = get_scibox_config()
        enable_reasoning = self.enable_reasoning if self.enable_reasoning is not None else (
            scibox_config.get("enable_reasoning", False) if scibox_config else False
        )
        
        # Если reasoning отключен, добавляем маркер /no_think в начало system prompt
        system_prompt = self.system_prompt
        if not enable_reasoning and not system_prompt.startswith("/no_think"):
            system_prompt = f"/no_think {system_prompt}"
        
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_prompt),
            HumanMessagePromptTemplate.from_template("{input}"),
        ])
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработка входных данных агентом
        
        Args:
            input_data: Входные данные для обработки
        
        Returns:
            Результат обработки
        """
        pass
    
    def _filter_think_blocks(self, text: str) -> str:
        """
        Удаляет блоки <think>...</think> из текста
        
        Args:
            text: Исходный текст
        
        Returns:
            Текст без блоков think
        """
        import re
        # Удаляем блоки <think>...</think> (включая многострочные)
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # Убираем лишние пустые строки
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
        return cleaned.strip()
    
    async def invoke(self, input_text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Вызов агента с текстовым входом
        
        Args:
            input_text: Входной текст
            context: Дополнительный контекст
        
        Returns:
            Ответ агента (без блоков <think>)
        """
        try:
            # Если LLM не инициализирован (нет API ключей), используем мок
            if self.llm is None:
                from backend.services.llm_client import llm_client
                result = await llm_client.generate(
                    prompt=input_text,
                    system_prompt=self.system_prompt
                )
                return result.get("content", "Демо-режим: API ключи не настроены")
            
            chain = self.prompt_template | self.llm
            
            # Формируем полный вход с контекстом
            full_input = input_text
            if context:
                context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
                full_input = f"{context_str}\n\n{input_text}"
            
            response = await chain.ainvoke({"input": full_input})
            # Фильтруем блоки <think>
            return self._filter_think_blocks(response.content)
        except Exception as e:
            # Fallback на мок при ошибке
            try:
                from backend.services.llm_client import llm_client
                result = await llm_client.generate(
                    prompt=input_text,
                    system_prompt=self.system_prompt
                )
                return result.get("content", f"Ошибка обработки агентом {self.agent_name}: {str(e)}")
            except Exception:
                return f"Ошибка обработки агентом {self.agent_name}: {str(e)}"
    
    async def invoke_stream(self, input_text: str, context: Optional[Dict[str, Any]] = None):
        """
        Вызов агента с потоковой выдачей (с фильтрацией блоков <think>)
        
        Args:
            input_text: Входной текст
            context: Дополнительный контекст
        
        Yields:
            Части ответа агента (для streaming, без блоков <think>)
        """
        try:
            # Если LLM не инициализирован (нет API ключей), используем мок
            if self.llm is None:
                from backend.services.llm_client import llm_client
                result = await llm_client.generate(
                    prompt=input_text,
                    system_prompt=self.system_prompt
                )
                content = result.get("content", "Демо-режим: API ключи не настроены")
                yield self._filter_think_blocks(content)
                return
            
            chain = self.prompt_template | self.llm
            
            # Формируем полный вход с контекстом
            full_input = input_text
            if context:
                context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
                full_input = f"{context_str}\n\n{input_text}"
            
            # Буфер для отслеживания блоков <think>
            buffer = ""
            inside_think = False
            
            # Используем astream для потоковой выдачи
            async for chunk in chain.astream({"input": full_input}):
                if hasattr(chunk, 'content'):
                    content = chunk.content
                else:
                    content = str(chunk)
                
                buffer += content
                
                # Проверяем, не начался ли блок <think>
                if '<think>' in buffer and not inside_think:
                    # Выдаем все до <think>
                    parts = buffer.split('<think>', 1)
                    if parts[0]:
                        yield parts[0]
                    inside_think = True
                    buffer = '<think>' + parts[1] if len(parts) > 1 else '<think>'
                
                # Проверяем, не закончился ли блок </think>
                if inside_think and '</think>' in buffer:
                    # Пропускаем весь блок think и выдаем то, что после него
                    parts = buffer.split('</think>', 1)
                    buffer = parts[1] if len(parts) > 1 else ''
                    inside_think = False
                    if buffer:
                        yield buffer
                        buffer = ""
                elif not inside_think and buffer:
                    # Если не внутри блока think, выдаем контент
                    # Но оставляем небольшой буфер на случай начала <think>
                    if len(buffer) > 10 and '<' not in buffer[-10:]:
                        yield buffer
                        buffer = ""
            
            # Выдаем остаток буфера (если не внутри think)
            if buffer and not inside_think:
                yield buffer
                
        except Exception as e:
            # Fallback на мок при ошибке
            try:
                from backend.services.llm_client import llm_client
                result = await llm_client.generate(
                    prompt=input_text,
                    system_prompt=self.system_prompt
                )
                content = result.get("content", f"Ошибка обработки агентом {self.agent_name}: {str(e)}")
                yield self._filter_think_blocks(content)
            except Exception:
                yield f"Ошибка обработки агентом {self.agent_name}: {str(e)}"

