"""
Migration: Add Task Bank Tables v4.2.0

Добавляет таблицы для банка задач:
- task_categories: категории задач
- task_templates: шаблоны задач
"""
import sys
import os

# Добавляем родительскую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

def migrate():
    """Применяет миграцию"""
    with engine.connect() as conn:
        # 1. Создаем таблицу категорий
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS task_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR NOT NULL UNIQUE,
                description TEXT,
                icon VARCHAR,
                parent_id INTEGER,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES task_categories(id)
            );
        """))
        
        # 2. Создаем таблицу шаблонов задач
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS task_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR NOT NULL,
                description TEXT NOT NULL,
                category_id INTEGER,
                task_type VARCHAR NOT NULL,
                difficulty VARCHAR NOT NULL,
                topic VARCHAR,
                tags JSON,
                programming_languages JSON,
                test_cases JSON,
                test_suite JSON,
                hints JSON,
                solution_template TEXT,
                example_solution TEXT,
                explanation TEXT,
                usage_count INTEGER NOT NULL DEFAULT 0,
                average_score REAL,
                average_time REAL,
                pass_rate REAL,
                quality_score REAL,
                is_verified BOOLEAN NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_by INTEGER,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES task_categories(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            );
        """))
        
        # 3. Создаем индексы
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_task_templates_task_type 
            ON task_templates(task_type);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_task_templates_difficulty 
            ON task_templates(difficulty);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_task_templates_topic 
            ON task_templates(topic);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_task_templates_category 
            ON task_templates(category_id);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_task_templates_created_at 
            ON task_templates(created_at);
        """))
        
        # 4. Добавляем начальные категории
        conn.execute(text("""
            INSERT OR IGNORE INTO task_categories (name, description, icon) VALUES
                ('Алгоритмы', 'Алгоритмические задачи', '🧮'),
                ('Структуры данных', 'Работа со структурами данных', '📊'),
                ('Backend', 'Backend разработка', '⚙️'),
                ('Frontend', 'Frontend разработка', '🎨'),
                ('База данных', 'SQL и базы данных', '🗄️'),
                ('Системный дизайн', 'Проектирование систем', '🏗️'),
                ('Python', 'Задачи на Python', '🐍'),
                ('JavaScript', 'Задачи на JavaScript', '📜'),
                ('Java', 'Задачи на Java', '☕'),
                ('C++', 'Задачи на C++', '⚡');
        """))
        
        conn.commit()
        print("✅ Миграция task_bank v4.2.0 успешно применена")

if __name__ == "__main__":
    migrate()

