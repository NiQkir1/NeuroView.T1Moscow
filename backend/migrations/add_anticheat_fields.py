"""
Миграция для добавления полей античита
Добавляет поля для мониторинга активности, детекции AI и множественных устройств
"""
import sqlite3
import os
from pathlib import Path


def upgrade():
    """Добавление полей античита"""
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
        # Проверяем существующие колонки
        cursor.execute("PRAGMA table_info(interview_sessions)")
        existing_session_columns = [row[1] for row in cursor.fetchall()]
        
        cursor.execute("PRAGMA table_info(answers)")
        existing_answer_columns = [row[1] for row in cursor.fetchall()]
        
        cursor.execute("PRAGMA table_info(questions)")
        existing_question_columns = [row[1] for row in cursor.fetchall()]
        
        # Добавляем поля в interview_sessions
        session_fields = [
            ("activity_history", "JSON"),
            ("suspicion_score", "FLOAT DEFAULT 0.0"),
            ("device_fingerprint", "VARCHAR"),
            ("ip_address", "VARCHAR"),
            ("user_agent", "VARCHAR"),
            ("concurrent_sessions", "JSON"),
            ("ai_detection_results", "JSON"),
            ("typing_metrics", "JSON"),
        ]
        
        for field_name, field_type in session_fields:
            if field_name not in existing_session_columns:
                print(f"  Добавление колонки interview_sessions.{field_name}...")
                cursor.execute(f"ALTER TABLE interview_sessions ADD COLUMN {field_name} {field_type}")
            else:
                print(f"  Колонка interview_sessions.{field_name} уже существует")
        
        # Добавляем поля в answers
        answer_fields = [
            ("time_to_answer", "FLOAT"),
            ("typing_speed", "FLOAT"),
            ("activity_during_answer", "JSON"),
        ]
        
        for field_name, field_type in answer_fields:
            if field_name not in existing_answer_columns:
                print(f"  Добавление колонки answers.{field_name}...")
                cursor.execute(f"ALTER TABLE answers ADD COLUMN {field_name} {field_type}")
            else:
                print(f"  Колонка answers.{field_name} уже существует")
        
        # Добавляем поле в questions
        if "shown_at" not in existing_question_columns:
            print("  Добавление колонки questions.shown_at...")
            cursor.execute("ALTER TABLE questions ADD COLUMN shown_at DATETIME")
        else:
            print("  Колонка questions.shown_at уже существует")
        
        conn.commit()
        print("\n[OK] Миграция завершена успешно!")
    except Exception as e:
        print(f"\n[ERROR] Ошибка при выполнении миграции: {e}")
        conn.rollback()
    finally:
        conn.close()


def downgrade():
    """Удаление полей античита"""
    db_path = Path(__file__).parent.parent / "neuroview.db"
    
    if not db_path.exists():
        print(f"База данных не найдена: {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # SQLite не поддерживает DROP COLUMN напрямую, нужно пересоздать таблицу
        print("⚠ SQLite не поддерживает DROP COLUMN. Откат миграции требует пересоздания таблиц.")
        print("⚠ Рекомендуется сделать backup базы данных перед откатом.")
        conn.commit()
    except Exception as e:
        print(f"\n❌ Ошибка при откате миграции: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()

