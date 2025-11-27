"""
Миграция базы данных для версии 3.0.0
Добавляет новые поля для HH.ru интеграции, статусов заявок и тестовых заданий
"""
import sqlite3
import os
from pathlib import Path

def migrate_database():
    """Выполнение миграции базы данных"""
    
    # Определяем путь к базе данных
    db_path = Path(__file__).parent.parent / "neuroview.db"
    
    if not db_path.exists():
        print(f"База данных не найдена: {db_path}")
        print("База данных будет создана автоматически при первом запуске")
        return
    
    print(f"Выполнение миграции базы данных: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Проверяем существующие колонки в таблице users
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Добавляем колонки для HH.ru интеграции
        hh_columns = [
            ("hh_access_token", "VARCHAR"),
            ("hh_refresh_token", "VARCHAR"),
            ("hh_token_expires_at", "DATETIME"),
            ("hh_resume_id", "VARCHAR"),
            ("hh_metrics", "JSON"),
            ("hh_profile_synced_at", "DATETIME"),
        ]
        
        for column_name, column_type in hh_columns:
            if column_name not in existing_columns:
                print(f"  Добавление колонки users.{column_name}...")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
            else:
                print(f"  Колонка users.{column_name} уже существует")
        
        # Проверяем колонки в таблице interview_sessions
        cursor.execute("PRAGMA table_info(interview_sessions)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Добавляем колонку для статуса заявки
        if "application_status" not in existing_columns:
            print("  Добавление колонки interview_sessions.application_status...")
            cursor.execute("ALTER TABLE interview_sessions ADD COLUMN application_status VARCHAR")
        else:
            print("  Колонка interview_sessions.application_status уже существует")
        
        # Проверяем существование таблицы test_tasks
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='test_tasks'
        """)
        
        if not cursor.fetchone():
            print("  Создание таблицы test_tasks...")
            cursor.execute("""
                CREATE TABLE test_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    title VARCHAR NOT NULL,
                    description TEXT NOT NULL,
                    task_type VARCHAR NOT NULL,
                    requirements JSON,
                    deadline DATETIME,
                    status VARCHAR NOT NULL DEFAULT 'pending',
                    solution TEXT,
                    solution_files JSON,
                    score FLOAT,
                    feedback TEXT,
                    reviewed_by INTEGER,
                    reviewed_at DATETIME,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES interview_sessions(id),
                    FOREIGN KEY (reviewed_by) REFERENCES users(id)
                )
            """)
            print("  Таблица test_tasks создана")
        else:
            print("  Таблица test_tasks уже существует")
        
        conn.commit()
        print("\n✅ Миграция успешно завершена!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Ошибка при миграции: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_database()



