"""
Миграция: Добавление индексов для оптимизации запросов
Дата: 2025-11-26
Цель: Ускорение выполнения частых запросов к БД
"""
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir.parent))

from sqlalchemy import text
from backend.database import engine, SessionLocal
from backend.utils.logger import get_module_logger

logger = get_module_logger("Migration.Indexes")


def add_database_indexes():
    """Добавление индексов для оптимизации производительности"""
    
    logger.info("=" * 60)
    logger.info("Миграция: Добавление индексов БД")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Список индексов для добавления
        indexes = [
            # Индексы для interview_sessions
            ("idx_sessions_status_created", "interview_sessions", ["status", "created_at"]),
            ("idx_sessions_candidate_status", "interview_sessions", ["candidate_id", "status"]),
            ("idx_sessions_interview_status", "interview_sessions", ["interview_id", "status"]),
            
            # Индексы для questions
            ("idx_questions_session_order", "questions", ["session_id", "order"]),
            
            # Индексы для answers
            ("idx_answers_question", "answers", ["question_id"]),
            ("idx_answers_created", "answers", ["created_at"]),
            
            # Индексы для messages (invitations)
            ("idx_invitations_interview_hr", "interview_invitations", ["interview_id", "hr_id"]),
            ("idx_invitations_candidate", "interview_invitations", ["candidate_id"]),
            
            # Индексы для test_tasks
            ("idx_testtasks_session_status", "test_tasks", ["session_id", "status"]),
        ]
        
        with engine.connect() as conn:
            for index_name, table_name, columns in indexes:
                try:
                    # Проверяем, существует ли уже индекс
                    check_query = text(f"""
                        SELECT COUNT(*) as cnt FROM sqlite_master 
                        WHERE type='index' AND name=:index_name
                    """)
                    result = conn.execute(check_query, {"index_name": index_name}).fetchone()
                    
                    if result and result[0] > 0:
                        logger.info(f"Индекс {index_name} уже существует, пропускаем")
                        continue
                    
                    # Создаем индекс
                    columns_str = ", ".join(columns)
                    create_index = text(f"""
                        CREATE INDEX {index_name} ON {table_name} ({columns_str})
                    """)
                    
                    logger.info(f"Создание индекса {index_name} на {table_name}({columns_str})...")
                    conn.execute(create_index)
                    conn.commit()
                    logger.info(f"✓ Индекс {index_name} создан")
                    
                except Exception as e:
                    logger.warning(f"Не удалось создать индекс {index_name}: {e}")
                    # Продолжаем с другими индексами
                    continue
        
        logger.info("=" * 60)
        logger.info("Миграция успешно завершена!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Добавленные оптимизации:")
        logger.info("  • Индексы для быстрого поиска сессий по статусу")
        logger.info("  • Индексы для связей candidate-session-interview")
        logger.info("  • Индексы для упорядоченных выборок")
        logger.info("  • Ускорение запросов приглашений и тестовых заданий")
        logger.info("")
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении миграции: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        add_database_indexes()
        print("\n✅ Миграция успешно выполнена!")
    except Exception as e:
        print(f"\n❌ Ошибка миграции: {e}")
        sys.exit(1)

