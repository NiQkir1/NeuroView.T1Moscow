"""
Утилита для структурированного логирования
"""
import logging
import sys
import os
import re
from datetime import datetime
from typing import Optional


def remove_ansi_codes(text: str) -> str:
    """
    Удаляет ANSI escape-коды из текста
    
    Args:
        text: Текст с возможными ANSI кодами
        
    Returns:
        Текст без ANSI кодов
    """
    if not text:
        return text
    
    # Паттерн для удаления ANSI escape-кодов
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', str(text))


class SimpleFormatter(logging.Formatter):
    """Простой форматтер без цветов с удалением ANSI кодов"""
    
    def format(self, record):
        # Форматируем время
        record.asctime = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Форматируем сообщение
        formatted = super().format(record)
        
        # Удаляем ANSI escape-коды
        return remove_ansi_codes(formatted)


def setup_logger(
    name: str = "NeuroView",
    level: int = logging.INFO,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Настройка структурированного логгера
    
    Args:
        name: Имя логгера
        level: Уровень логирования
        format_string: Кастомный формат (опционально)
    
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Удаляем существующие обработчики
    logger.handlers.clear()
    
    # Создаем обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Формат по умолчанию - простой и читаемый
    if format_string is None:
        format_string = (
            "%(asctime)s | %(levelname)-8s | NeuroView Backend | %(message)s"
        )
    
    # Используем простой форматтер без цветов
    formatter = SimpleFormatter(format_string)
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Предотвращаем дублирование логов
    logger.propagate = False
    
    return logger


# Глобальный логгер для приложения
app_logger = setup_logger("NeuroView", logging.INFO)

# Логгеры для разных модулей
def get_module_logger(module_name: str) -> logging.Logger:
    """Получить логгер для модуля"""
    return logging.getLogger(f"NeuroView.{module_name}")


def configure_uvicorn_logging():
    """
    Настройка логирования для uvicorn (отключение цветов и ANSI кодов)
    """
    import logging
    
    # Настраиваем логгер uvicorn
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    
    # Настраиваем логгер access
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    
    # Создаем обработчики с нашим форматтером
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    format_string = "%(asctime)s | %(levelname)-8s | Uvicorn | %(message)s"
    formatter = SimpleFormatter(format_string)
    handler.setFormatter(formatter)
    
    # Применяем к обоим логгерам
    uvicorn_logger.addHandler(handler)
    access_logger.addHandler(handler)
    
    # Отключаем распространение
    uvicorn_logger.propagate = False
    access_logger.propagate = False

