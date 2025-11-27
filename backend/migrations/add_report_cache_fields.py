"""
Миграция: Добавление полей для кеширования отчетов
Дата: 2025-11-26
Цель: Ускорение генерации и загрузки PDF отчетов
"""
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir.parent))

from sqlalchemy import Column, String, JSON, text
from backend.database import engine, SessionLocal
from backend.models import Base, InterviewSession
from backend.utils.logger import get_module_logger

logger = get_module_logger("Migration.ReportCache")


def add_report_cache_fields():
    """Добавление полей для кеширования отчетов в таблицу interview_sessions"""
    
    logger.info("=" * 60)
    logger.info("Миграция: Добавление полей кеширования отчетов")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Проверяем, существуют ли уже поля
        from sqlalchemy import inspect
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('interview_sessions')]
        
        fields_to_add = []
        if 'cached_pdf_path' not in columns:
            fields_to_add.append('cached_pdf_path')
        if 'ai_evaluation' not in columns:
            fields_to_add.append('ai_evaluation')
        
        if not fields_to_add:
            logger.info("Поля кеширования уже существуют, миграция не требуется")
            return
        
        logger.info(f"Добавляем поля: {', '.join(fields_to_add)}")
        
        # Добавляем поля через ALTER TABLE
        with engine.connect() as conn:
            if 'cached_pdf_path' in fields_to_add:
                logger.info("Добавление поля cached_pdf_path...")
                conn.execute(text(
                    "ALTER TABLE interview_sessions ADD COLUMN cached_pdf_path VARCHAR"
                ))
                conn.commit()
                logger.info("✓ Поле cached_pdf_path добавлено")
            
            if 'ai_evaluation' in fields_to_add:
                logger.info("Добавление поля ai_evaluation...")
                conn.execute(text(
                    "ALTER TABLE interview_sessions ADD COLUMN ai_evaluation JSON"
                ))
                conn.commit()
                logger.info("✓ Поле ai_evaluation добавлено")
        
        logger.info("=" * 60)
        logger.info("Миграция успешно завершена!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Новые возможности:")
        logger.info("  • PDF отчеты теперь кешируются для быстрого доступа")
        logger.info("  • AI оценки сохраняются в БД для повторного использования")
        logger.info("  • Значительно ускорена загрузка отчетов")
        logger.info("")
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении миграции: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        add_report_cache_fields()
        print("\n✅ Миграция успешно выполнена!")
    except Exception as e:
        print(f"\n❌ Ошибка миграции: {e}")
        sys.exit(1)

