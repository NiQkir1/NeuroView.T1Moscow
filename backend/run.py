"""
Скрипт для запуска приложения
Использование: python -m backend.run или python backend/run.py
"""
import sys
import os

# Добавление корневой директории в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    import uvicorn
    
    # Определяем режим работы из переменной окружения
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    # Отключаем цветные логи в uvicorn
    os.environ["UVICORN_NO_COLORS"] = "1"
    
    # Используем строку импорта для поддержки reload
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=not is_production,  # Отключаем reload в production
        reload_dirs=[os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend")] if not is_production else None,
        log_config=None  # Используем нашу конфигурацию логирования
    )

