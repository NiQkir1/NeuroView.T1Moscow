"""
Migration: Add Task Bank Tables v4.2.0 (Simplified)
"""
import sqlite3
import os

def migrate():
    """Применяет миграцию"""
    # Путь к БД
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'neuroview.db')
    
    print(f"Connecting to database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Создаем таблицу категорий
        print("Creating table: task_categories...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR NOT NULL UNIQUE,
                description TEXT,
                icon VARCHAR,
                parent_id INTEGER,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES task_categories(id)
            )
        """)
        
        # 2. Создаем таблицу шаблонов задач
        print("Creating table: task_templates...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR NOT NULL,
                description TEXT NOT NULL,
                category_id INTEGER,
                task_type VARCHAR NOT NULL,
                difficulty VARCHAR NOT NULL,
                topic VARCHAR,
                tags TEXT,
                programming_languages TEXT,
                test_cases TEXT,
                test_suite TEXT,
                hints TEXT,
                solution_template TEXT,
                example_solution TEXT,
                explanation TEXT,
                usage_count INTEGER NOT NULL DEFAULT 0,
                average_score REAL,
                average_time REAL,
                pass_rate REAL,
                quality_score REAL,
                is_verified INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_by INTEGER,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES task_categories(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        
        # 3. Создаем индексы
        print("Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_templates_task_type 
            ON task_templates(task_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_templates_difficulty 
            ON task_templates(difficulty)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_templates_topic 
            ON task_templates(topic)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_templates_category 
            ON task_templates(category_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_templates_created_at 
            ON task_templates(created_at)
        """)
        
        # 4. Добавляем начальные категории
        print("Adding initial categories...")
        categories = [
            ('Алгоритмы', 'Алгоритмические задачи', '🧮'),
            ('Структуры данных', 'Работа со структурами данных', '📊'),
            ('Backend', 'Backend разработка', '⚙️'),
            ('Frontend', 'Frontend разработка', '🎨'),
            ('База данных', 'SQL и базы данных', '🗄️'),
            ('Системный дизайн', 'Проектирование систем', '🏗️'),
            ('Python', 'Задачи на Python', '🐍'),
            ('JavaScript', 'Задачи на JavaScript', '📜'),
            ('Java', 'Задачи на Java', '☕'),
            ('C++', 'Задачи на C++', '⚡'),
        ]
        
        for name, description, icon in categories:
            cursor.execute("""
                INSERT OR IGNORE INTO task_categories (name, description, icon) 
                VALUES (?, ?, ?)
            """, (name, description, icon))
        
        conn.commit()
        print("\nMigration task_bank v4.2.0 successfully applied!")
        print(f"Categories created: {len(categories)}")
        
    except Exception as e:
        conn.rollback()
        print(f"\nMigration error: {e}")
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

