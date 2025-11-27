"""
Task Bank Models v4.2.0 - модели для банка задач
"""
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.models import Base


class TaskCategory(Base):
    """Категория задач"""
    __tablename__ = "task_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)  # Иконка категории
    parent_id = Column(Integer, ForeignKey("task_categories.id"), nullable=True)  # Для вложенных категорий
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Связи
    tasks = relationship("TaskTemplate", back_populates="category")
    parent = relationship("TaskCategory", remote_side=[id])


class TaskTemplate(Base):
    """Шаблон задачи в банке"""
    __tablename__ = "task_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey("task_categories.id"), nullable=True, index=True)
    
    # Метаданные задачи
    task_type = Column(String, nullable=False, index=True)  # coding, theory, system_design, algorithm
    difficulty = Column(String, nullable=False, index=True)  # easy, medium, hard, expert
    topic = Column(String, nullable=True, index=True)  # arrays, strings, trees, etc.
    tags = Column(JSON, nullable=True)  # Список тегов для поиска
    
    # Языки программирования (для coding задач)
    programming_languages = Column(JSON, nullable=True)  # ["python", "javascript", ...]
    
    # Тесты
    test_cases = Column(JSON, nullable=True)  # Базовые тесты
    test_suite = Column(JSON, nullable=True)  # Полный набор тестов (видимые + скрытые)
    
    # Дополнительные материалы
    hints = Column(JSON, nullable=True)  # Подсказки
    solution_template = Column(Text, nullable=True)  # Шаблон решения (стартовый код)
    example_solution = Column(Text, nullable=True)  # Пример решения (скрыт от кандидата)
    explanation = Column(Text, nullable=True)  # Объяснение решения
    
    # Метрики и статистика
    usage_count = Column(Integer, default=0, nullable=False)  # Сколько раз использовалась
    average_score = Column(Float, nullable=True)  # Средняя оценка кандидатов
    average_time = Column(Float, nullable=True)  # Среднее время решения (минуты)
    pass_rate = Column(Float, nullable=True)  # Процент успешных решений
    
    # Качество задачи
    quality_score = Column(Float, nullable=True)  # Оценка качества задачи (0-10)
    is_verified = Column(Boolean, default=False, nullable=False)  # Проверена экспертом
    is_active = Column(Boolean, default=True, nullable=False)  # Активна ли задача
    
    # Авторство
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    category = relationship("TaskCategory", back_populates="tasks")
    creator = relationship("User", foreign_keys=[created_by])

