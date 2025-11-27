"""
Миграция: Добавление недостающих индексов для оптимизации запросов
Дата: 2025-11-26
"""
import sqlite3
from pathlib import Path
import sys

def add_missing_indexes():
    """Добавляет недостающие индексы в существующую базу данных"""
    
    # Путь к базе данных
    db_path = Path(__file__).parent.parent / "neuroview.db"
    
    if not db_path.exists():
        print(f"[ERROR] База данных не найдена: {db_path}")
        print("Запустите приложение сначала для создания БД")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("=" * 60)
        print("Добавление недостающих индексов в базу данных...")
        print("=" * 60)
        
        # Список индексов для создания
        indexes = [
            # Interviews
            ("idx_interviews_access_code", "interviews", "access_code"),
            ("idx_interviews_created_at", "interviews", "created_at"),
            
            # Interview Sessions
            ("idx_interview_sessions_created_at", "interview_sessions", "created_at"),
            ("idx_interview_sessions_completed_at", "interview_sessions", "completed_at"),
            
            # Messages
            ("idx_messages_status", "messages", "status"),
            ("idx_messages_created_at", "messages", "created_at"),
            
            # Interview Invitations
            ("idx_interview_invitations_status", "interview_invitations", "status"),
            ("idx_interview_invitations_created_at", "interview_invitations", "created_at"),
        ]
        
        # Проверяем существующие индексы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        existing_indexes = {row[0] for row in cursor.fetchall()}
        
        created_count = 0
        skipped_count = 0
        
        for index_name, table_name, column_name in indexes:
            if index_name in existing_indexes:
                print(f"[SKIP] Индекс {index_name} уже существует")
                skipped_count += 1
                continue
            
            try:
                # Проверяем, существует ли таблица
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                if not cursor.fetchone():
                    print(f"[WARN] Таблица {table_name} не существует, пропускаем индекс {index_name}")
                    skipped_count += 1
                    continue
                
                # Проверяем, существует ли колонка
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = {row[1] for row in cursor.fetchall()}
                if column_name not in columns:
                    print(f"[WARN] Колонка {column_name} не существует в таблице {table_name}, пропускаем индекс {index_name}")
                    skipped_count += 1
                    continue
                
                # Создаем индекс
                sql = f"CREATE INDEX {index_name} ON {table_name}({column_name})"
                cursor.execute(sql)
                print(f"[OK] Создан индекс: {index_name} на {table_name}({column_name})")
                created_count += 1
                
            except sqlite3.Error as e:
                print(f"[WARN] Ошибка создания индекса {index_name}: {e}")
                skipped_count += 1
        
        # Сохраняем изменения
        conn.commit()
        conn.close()
        
        print("=" * 60)
        print(f"[SUCCESS] Миграция завершена!")
        print(f"   Создано индексов: {created_count}")
        print(f"   Пропущено: {skipped_count}")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_indexes():
    """Проверяет наличие всех необходимых индексов"""
    
    db_path = Path(__file__).parent.parent / "neuroview.db"
    
    if not db_path.exists():
        print(f"[ERROR] База данных не найдена: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("\n" + "=" * 60)
        print("Проверка индексов в базе данных...")
        print("=" * 60)
        
        # Получаем список всех индексов
        cursor.execute("""
            SELECT name, tbl_name, sql 
            FROM sqlite_master 
            WHERE type='index' AND name NOT LIKE 'sqlite_%'
            ORDER BY tbl_name, name
        """)
        
        indexes = cursor.fetchall()
        
        current_table = None
        for name, table, sql in indexes:
            if table != current_table:
                print(f"\nТаблица: {table}")
                current_table = table
            print(f"   [+] {name}")
        
        print("\n" + "=" * 60)
        print(f"Всего индексов: {len(indexes)}")
        print("=" * 60)
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка проверки: {e}")
        return False


if __name__ == "__main__":
    if "--verify" in sys.argv:
        verify_indexes()
    else:
        if add_missing_indexes():
            verify_indexes()

