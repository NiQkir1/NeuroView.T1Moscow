"""
Конфигуратор для подключения к SciBox LLM
"""
import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """Конфигурация для SciBox LLM"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # SciBox настройки
    scibox_api_key: Optional[str] = Field(
        default=None,
        description="API ключ для SciBox LLM сервиса"
    )
    scibox_base_url: str = Field(
        default="https://llm.t1v.scibox.tech/v1",
        description="Базовый URL для SciBox API"
    )
    scibox_model: str = Field(
        default="qwen3-32b-awq",
        description="Модель SciBox для использования"
    )
    scibox_temperature: float = Field(
        default=0.2,  # Низкая температура для строгого следования промпту
        description="Температура для генерации (0-2). Низкие значения = более детерминированный вывод"
    )
    scibox_max_tokens: int = Field(
        default=2000,
        description="Максимальное количество токенов"
    )
    scibox_timeout: int = Field(
        default=60,
        description="Таймаут запроса в секундах"
    )
    scibox_stream: bool = Field(
        default=True,
        description="Включить потоковую выдачу (streaming)"
    )
    scibox_enable_reasoning: bool = Field(
        default=False,
        description="Включить reasoning (внутренние рассуждения модели)"
    )
    
    # Общие настройки
    retry_attempts: int = Field(
        default=3,
        description="Количество попыток повтора при ошибке"
    )
    retry_delay: float = Field(
        default=1.0,
        description="Задержка между попытками в секундах"
    )


# Глобальный экземпляр конфигурации
llm_config = LLMConfig()


def get_scibox_config() -> dict:
    """Получить конфигурацию для SciBox"""
    if not llm_config.scibox_api_key or llm_config.scibox_api_key == "your_scibox_api_key_here":
        return None  # API ключ не установлен, будет использован мок
    
    return {
        "api_key": llm_config.scibox_api_key,
        "base_url": llm_config.scibox_base_url,
        "model": llm_config.scibox_model,
        "temperature": llm_config.scibox_temperature,
        "max_tokens": llm_config.scibox_max_tokens,
        "timeout": llm_config.scibox_timeout,
        "stream": llm_config.scibox_stream,
        "enable_reasoning": llm_config.scibox_enable_reasoning,
    }

