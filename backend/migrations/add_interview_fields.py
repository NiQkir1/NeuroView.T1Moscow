"""
Миграция: Добавление полей position, level, programming_languages, timer в таблицу interviews

Добавляет новые поля для удобного доступа к конфигурации интервью
"""

import sys
import os

# Добавляем корневую директорию проекта в путь
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, project_root)

from sqlalchemy import create_engine, text
from backend.database import SQLALCHEMY_DATABASE_URL
from backend.utils.logger import get_module_logger

logger = get_module_logger("Migration_AddInterviewFields")


def upgrade():
    """Добавление новых полей в таблицу interviews"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            logger.info("Starting migration: add_interview_fields")
            
            # Добавляем поле position
            try:
                conn.execute(text("""
                    ALTER TABLE interviews
                    ADD COLUMN position TEXT;
                """))
                logger.info("✓ Added column: position")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    logger.info("✓ Column 'position' already exists, skipping")
                else:
                    raise
            
            # Добавляем поле level
            try:
                conn.execute(text("""
                    ALTER TABLE interviews
                    ADD COLUMN level TEXT;
                """))
                logger.info("✓ Added column: level")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    logger.info("✓ Column 'level' already exists, skipping")
                else:
                    raise
            
            # Добавляем поле programming_languages (JSON)
            try:
                conn.execute(text("""
                    ALTER TABLE interviews
                    ADD COLUMN programming_languages TEXT;
                """))
                logger.info("✓ Added column: programming_languages")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    logger.info("✓ Column 'programming_languages' already exists, skipping")
                else:
                    raise
            
            # Добавляем поле timer (JSON)
            try:
                conn.execute(text("""
                    ALTER TABLE interviews
                    ADD COLUMN timer TEXT;
                """))
                logger.info("✓ Added column: timer")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    logger.info("✓ Column 'timer' already exists, skipping")
                else:
                    raise
            
            conn.commit()
            logger.info("✅ Migration completed successfully!")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Migration failed: {e}")
            raise


def downgrade():
    """Откат миграции (удаление полей)"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            logger.info("Starting downgrade: add_interview_fields")
            
            # SQLite не поддерживает DROP COLUMN напрямую
            # Нужно пересоздавать таблицу, что рискованно
            logger.warning("⚠ SQLite doesn't support DROP COLUMN directly")
            logger.warning("Manual downgrade required if needed")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Downgrade failed: {e}")
            raise


if __name__ == "__main__":
    print("Running migration: add_interview_fields")
    upgrade()
    print("Migration completed!")

