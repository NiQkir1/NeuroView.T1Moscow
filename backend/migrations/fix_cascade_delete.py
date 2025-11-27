"""
Миграция для исправления каскадного удаления
Исправляет проблему с удалением пользователей, у которых есть связанные записи
"""
import sqlite3
import os
import sys

# Добавляем путь к корневой директории проекта
# Путь от migrations -> backend -> корень
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, root_dir)

from backend.database import SessionLocal, engine
from backend.models import Base
from sqlalchemy import text


def backup_database():
    """Создание резервной копии БД"""
    import shutil
    from datetime import datetime
    
    # Определяем путь к БД относительно текущей директории
    if os.path.exists("backend/neuroview.db"):
        db_path = "backend/neuroview.db"
        backup_dir = "backend"
    elif os.path.exists("neuroview.db"):
        db_path = "neuroview.db"
        backup_dir = "."
    else:
        print("[!] База данных не найдена!")
        return None
    
    if os.path.exists(db_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{backup_dir}/neuroview_backup_{timestamp}.db"
        shutil.copy(db_path, backup_path)
        print(f"[+] Создана резервная копия: {backup_path}")
        return backup_path
    return None


def migrate_cascade_delete():
    """Миграция для добавления каскадного удаления"""
    print("\n" + "=" * 80)
    print("  МИГРАЦИЯ: Исправление каскадного удаления v4.1.1")
    print("=" * 80)
    
    # Создаем резервную копию
    backup_path = backup_database()
    
    db = SessionLocal()
    try:
        # Временно отключаем проверку внешних ключей для миграции
        db.execute(text("PRAGMA foreign_keys = OFF"))
        db.commit()
        
        # Для SQLite нужно пересоздать таблицы с новыми внешними ключами
        # Так как SQLite не поддерживает ALTER TABLE для изменения FK
        
        print("\n[1/6] Создание временных таблиц...")
        
        # Сохраняем данные из messages
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS messages_backup AS 
            SELECT * FROM messages
        """))
        
        # Сохраняем данные из interview_invitations
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS interview_invitations_backup AS 
            SELECT * FROM interview_invitations
        """))
        
        db.commit()
        print("[+] Временные таблицы созданы")
        
        print("\n[2/6] Удаление старых таблиц...")
        
        # Удаляем старые таблицы
        db.execute(text("DROP TABLE IF EXISTS messages"))
        db.execute(text("DROP TABLE IF EXISTS interview_invitations"))
        
        db.commit()
        print("[+] Старые таблицы удалены")
        
        print("\n[3/6] Создание новых таблиц с каскадным удалением...")
        
        # Создаем новую таблицу messages с CASCADE
        db.execute(text("""
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                recipient_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                status VARCHAR NOT NULL DEFAULT 'sent',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                read_at DATETIME,
                FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        
        # Создаем индексы для messages
        db.execute(text("CREATE INDEX ix_messages_sender_id ON messages (sender_id)"))
        db.execute(text("CREATE INDEX ix_messages_recipient_id ON messages (recipient_id)"))
        db.execute(text("CREATE INDEX ix_messages_status ON messages (status)"))
        db.execute(text("CREATE INDEX ix_messages_created_at ON messages (created_at)"))
        
        # Создаем новую таблицу interview_invitations с CASCADE
        db.execute(text("""
            CREATE TABLE interview_invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interview_id INTEGER NOT NULL,
                candidate_id INTEGER NOT NULL,
                hr_id INTEGER,
                message TEXT,
                status VARCHAR NOT NULL DEFAULT 'pending',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                responded_at DATETIME,
                expires_at DATETIME,
                FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE,
                FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (hr_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """))
        
        # Создаем индексы для interview_invitations
        db.execute(text("CREATE INDEX ix_interview_invitations_interview_id ON interview_invitations (interview_id)"))
        db.execute(text("CREATE INDEX ix_interview_invitations_candidate_id ON interview_invitations (candidate_id)"))
        db.execute(text("CREATE INDEX ix_interview_invitations_hr_id ON interview_invitations (hr_id)"))
        db.execute(text("CREATE INDEX ix_interview_invitations_status ON interview_invitations (status)"))
        db.execute(text("CREATE INDEX ix_interview_invitations_created_at ON interview_invitations (created_at)"))
        
        db.commit()
        print("[+] Новые таблицы созданы")
        
        print("\n[4/6] Восстановление данных messages...")
        
        # Восстанавливаем данные messages
        db.execute(text("""
            INSERT INTO messages 
                (id, sender_id, recipient_id, message_text, status, created_at, read_at)
            SELECT 
                id, sender_id, recipient_id, message_text, status, created_at, read_at
            FROM messages_backup
        """))
        
        db.commit()
        
        # Проверяем количество восстановленных записей
        result = db.execute(text("SELECT COUNT(*) FROM messages")).fetchone()
        print(f"[+] Восстановлено {result[0]} сообщений")
        
        print("\n[5/6] Восстановление данных interview_invitations...")
        
        # Восстанавливаем данные interview_invitations
        db.execute(text("""
            INSERT INTO interview_invitations 
                (id, interview_id, candidate_id, hr_id, message, status, created_at, responded_at, expires_at)
            SELECT 
                id, interview_id, candidate_id, hr_id, message, status, created_at, responded_at, expires_at
            FROM interview_invitations_backup
        """))
        
        db.commit()
        
        # Проверяем количество восстановленных записей
        result = db.execute(text("SELECT COUNT(*) FROM interview_invitations")).fetchone()
        print(f"[+] Восстановлено {result[0]} приглашений")
        
        print("\n[6/6] Очистка временных таблиц...")
        
        # Удаляем временные таблицы
        db.execute(text("DROP TABLE IF EXISTS messages_backup"))
        db.execute(text("DROP TABLE IF EXISTS interview_invitations_backup"))
        
        db.commit()
        print("[+] Временные таблицы удалены")
        
        # Включаем обратно проверку внешних ключей
        db.execute(text("PRAGMA foreign_keys = ON"))
        db.commit()
        print("\n[+] Проверка внешних ключей включена")
        
        print("\n" + "=" * 80)
        print("  [OK] МИГРАЦИЯ УСПЕШНО ЗАВЕРШЕНА")
        print("=" * 80)
        print("\nТеперь при удалении пользователя:")
        print("  - Все его сообщения будут автоматически удалены")
        print("  - Все приглашения на интервью будут удалены")
        print("  - HR_ID в приглашениях будет установлен в NULL")
        
        if backup_path:
            print(f"\nРезервная копия сохранена в: {backup_path}")
        
    except Exception as e:
        print(f"\n[X] Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        
        if backup_path and os.path.exists(backup_path):
            print(f"\n[!] Восстановите БД из резервной копии: {backup_path}")
    
    finally:
        db.close()


if __name__ == "__main__":
    # Определяем путь к БД
    if os.path.exists("backend/neuroview.db"):
        db_path = "backend/neuroview.db"
    elif os.path.exists("neuroview.db"):
        db_path = "neuroview.db"
    else:
        print("[X] База данных не найдена!")
        print("   Убедитесь, что вы запускаете скрипт из корневой директории проекта")
        sys.exit(1)
    
    # Проверяем включены ли внешние ключи в SQLite
    print(f"Проверка поддержки внешних ключей в {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys")
    fk_enabled = cursor.fetchone()[0]
    conn.close()
    
    if not fk_enabled:
        print("[!] ВНИМАНИЕ: Внешние ключи отключены в SQLite!")
        print("   Миграция будет выполнена, но каскадное удаление")
        print("   не будет работать на уровне БД.")
        print("   Убедитесь, что в коде включены внешние ключи:")
        print("   PRAGMA foreign_keys = ON")
    
    migrate_cascade_delete()

