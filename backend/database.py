"""Настройка базы данных"""
import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from backend.models import Base

# Определяем абсолютный путь к базе данных
# База данных будет в папке backend
BASE_DIR = Path(__file__).parent
DATABASE_PATH = BASE_DIR / "neuroview.db"

# SQLite для локальной разработки
# Используем абсолютный путь, чтобы база данных всегда создавалась в одном месте
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH.absolute()}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Только для SQLite
)

# ВАЖНО: Включаем внешние ключи для SQLite
# Без этого каскадное удаление не будет работать
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Включает внешние ключи для SQLite при каждом подключении"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Инициализация базы данных (создание таблиц)"""
    # create_all() не пересоздает существующие таблицы, только создает новые
    # Это безопасно вызывать при каждом запуске
    Base.metadata.create_all(bind=engine)
    
    # Миграция: добавляем недостающие столбцы в существующие таблицы
    _migrate_db()


def _migrate_db():
    """Миграция базы данных: добавление новых столбцов в существующие таблицы"""
    from sqlalchemy import text, inspect
    
    inspector = inspect(engine)
    
    # Проверяем и добавляем столбцы в interview_sessions
    if 'interview_sessions' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('interview_sessions')]
        
        # Добавляем current_stage, если его нет
        if 'current_stage' not in columns:
            try:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN current_stage VARCHAR"))
                    conn.commit()
            except Exception as e:
                # Игнорируем ошибки, если столбец уже существует или таблица не существует
                pass
        
        # Добавляем stage_progress, если его нет
        if 'stage_progress' not in columns:
            try:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN stage_progress TEXT"))
                    conn.commit()
            except Exception as e:
                pass
        
        # Добавляем emotion_history, если его нет
        if 'emotion_history' not in columns:
            try:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN emotion_history TEXT"))
                    conn.commit()
            except Exception as e:
                pass
    
    # Проверяем и добавляем столбцы в interviews
    if 'interviews' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('interviews')]
        
        # Добавляем hr_prompt, если его нет
        if 'hr_prompt' not in columns:
            try:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE interviews ADD COLUMN hr_prompt TEXT"))
                    conn.commit()
            except Exception as e:
                pass
        
        # Добавляем interview_config, если его нет
        if 'interview_config' not in columns:
            try:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE interviews ADD COLUMN interview_config TEXT"))
                    conn.commit()
            except Exception as e:
                pass
    
    # Mercor AI v2.0.0: Миграция для таблицы users - добавление новых полей профиля
    if 'users' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        # Список новых полей для добавления
        new_fields = [
            ('github_username', 'VARCHAR'),
            ('linkedin_url', 'VARCHAR'),
            ('skills', 'TEXT'),  # JSON хранится как TEXT в SQLite
            ('skill_matrix', 'TEXT'),
            ('work_experience', 'TEXT'),
            ('education', 'TEXT'),
            ('soft_skills_score', 'TEXT'),
            ('culture_fit_score', 'REAL'),  # Float в SQLite
            ('success_prediction', 'TEXT'),
            ('external_profiles', 'TEXT'),
        ]
        
        for field_name, field_type in new_fields:
            if field_name not in columns:
                try:
                    with engine.connect() as conn:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {field_name} {field_type}"))
                        conn.commit()
                except Exception as e:
                    # Игнорируем ошибки, если столбец уже существует
                    pass
        
        # HR Search & Filter v2.0.0: Добавляем новые поля для поиска
        hr_search_fields = [
            ('role_type', 'VARCHAR'),
            ('experience_level', 'VARCHAR'),
            ('programming_languages', 'TEXT'),
        ]
        
        for field_name, field_type in hr_search_fields:
            if field_name not in columns:
                try:
                    with engine.connect() as conn:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {field_name} {field_type}"))
                        conn.commit()
                except Exception as e:
                    pass
        
        # v3.0.0: Добавляем поля для HH.ru интеграции
        hh_fields = [
            ('hh_access_token', 'VARCHAR'),
            ('hh_refresh_token', 'VARCHAR'),
            ('hh_token_expires_at', 'DATETIME'),
            ('hh_resume_id', 'VARCHAR'),
            ('hh_metrics', 'TEXT'),  # JSON хранится как TEXT в SQLite
            ('hh_profile_synced_at', 'DATETIME'),
        ]
        
        for field_name, field_type in hh_fields:
            if field_name not in columns:
                try:
                    with engine.connect() as conn:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {field_name} {field_type}"))
                        conn.commit()
                except Exception as e:
                    pass
    
    # v3.0.0: Добавляем application_status в interview_sessions
    if 'interview_sessions' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('interview_sessions')]
        
        if 'application_status' not in columns:
            try:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN application_status VARCHAR"))
                    conn.commit()
            except Exception as e:
                pass
        
        # Античит поля для interview_sessions
        anticheat_fields = [
            ('activity_history', 'TEXT'),  # JSON хранится как TEXT в SQLite
            ('suspicion_score', 'FLOAT DEFAULT 0.0'),
            ('device_fingerprint', 'VARCHAR'),
            ('ip_address', 'VARCHAR'),
            ('user_agent', 'VARCHAR'),
            ('concurrent_sessions', 'TEXT'),  # JSON хранится как TEXT в SQLite
            ('ai_detection_results', 'TEXT'),  # JSON хранится как TEXT в SQLite
            ('typing_metrics', 'TEXT'),  # JSON хранится как TEXT в SQLite
        ]
        
        for field_name, field_type in anticheat_fields:
            if field_name not in columns:
                try:
                    with engine.connect() as conn:
                        conn.execute(text(f"ALTER TABLE interview_sessions ADD COLUMN {field_name} {field_type}"))
                        conn.commit()
                except Exception as e:
                    pass
    
    # v3.0.0: Создаем таблицу test_tasks, если её нет
    # Обычно она создается через Base.metadata.create_all(), но на всякий случай проверяем
    if 'test_tasks' not in inspector.get_table_names():
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE test_tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER NOT NULL,
                        title VARCHAR NOT NULL,
                        description TEXT NOT NULL,
                        task_type VARCHAR NOT NULL,
                        requirements TEXT,
                        deadline DATETIME,
                        status VARCHAR NOT NULL DEFAULT 'pending',
                        solution TEXT,
                        solution_files TEXT,
                        score REAL,
                        feedback TEXT,
                        reviewed_by INTEGER,
                        reviewed_at DATETIME,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES interview_sessions(id),
                        FOREIGN KEY (reviewed_by) REFERENCES users(id)
                    )
                """))
                conn.commit()
        except Exception as e:
            # Игнорируем ошибки, если таблица уже существует
            pass
    
    # Античит поля для answers
    if 'answers' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('answers')]
        
        anticheat_answer_fields = [
            ('time_to_answer', 'REAL'),
            ('typing_speed', 'REAL'),
            ('activity_during_answer', 'TEXT'),  # JSON хранится как TEXT в SQLite
        ]
        
        for field_name, field_type in anticheat_answer_fields:
            if field_name not in columns:
                try:
                    with engine.connect() as conn:
                        conn.execute(text(f"ALTER TABLE answers ADD COLUMN {field_name} {field_type}"))
                        conn.commit()
                except Exception as e:
                    pass
    
    # Античит поля для questions
    if 'questions' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('questions')]
        
        if 'shown_at' not in columns:
            try:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE questions ADD COLUMN shown_at DATETIME"))
                    conn.commit()
            except Exception as e:
                pass
    
    # Chat & Invitations v2.0.0: Создаем таблицы для чата и приглашений
    # Таблицы messages и interview_invitations будут созданы автоматически через Base.metadata.create_all()
    # Но можно добавить проверку и создание вручную, если нужно


def get_db() -> Generator[Session, None, None]:
    """Dependency для получения сессии БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

