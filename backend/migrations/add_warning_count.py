"""
Миграция для добавления поля warning_count в таблицу interview_sessions
Дата: 2025-11-26
"""
import sqlite3
import os
from pathlib import Path


def upgrade():
    """Добавляет поле warning_count в таблицу interview_sessions"""
    
    # Определяем путь к базе данных
    db_path = Path(__file__).parent.parent / "neuroview.db"
    
    if not db_path.exists():
        print(f"База данных не найдена: {db_path}")
        print("База данных будет создана автоматически при первом запуске")
        return False
    
    print(f"Выполнение миграции базы данных: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Проверяем существующие колонки
        cursor.execute("PRAGMA table_info(interview_sessions)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Добавляем warning_count если его нет
        if 'warning_count' not in existing_columns:
            print("Добавление поля 'warning_count'...")
            cursor.execute("""
                ALTER TABLE interview_sessions 
                ADD COLUMN warning_count INTEGER DEFAULT 0 NOT NULL
            """)
            print("[OK] Поле 'warning_count' успешно добавлено")
        else:
            print("[SKIP] Поле 'warning_count' уже существует, пропускаем")
        
        conn.commit()
        print("\n[SUCCESS] Миграция успешно завершена!")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Ошибка миграции: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Миграция: Добавление поля warning_count")
    print("=" * 60)
    print()
    
    success = upgrade()
    
    if not success:
        exit(1)

