"""Модели собеседований"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from backend.models import Base


class InterviewStatus(str, enum.Enum):
    """Статусы собеседования"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ApplicationStatus(str, enum.Enum):
    """Статусы заявки кандидата (v3.0.0)"""
    ACTIVE = "active"           # Активная заявка в процессе рассмотрения
    COMPLETED = "completed"     # Успешно пройденное ИИ-интервью
    TEST_TASK = "test_task"     # Отправлено тестовое задание
    FINALIST = "finalist"       # Кандидат в финальном отборе
    OFFER = "offer"             # Получено предложение о работе
    REJECTED = "rejected"        # Отклоненная заявка


class QuestionType(str, enum.Enum):
    """Типы вопросов"""
    CODING = "coding"
    THEORY = "theory"
    SYSTEM_DESIGN = "system_design"
    BEHAVIORAL = "behavioral"


class Interview(Base):
    """Модель шаблона собеседования"""
    __tablename__ = "interviews"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    topics = Column(JSON, nullable=True)  # Список тем
    stages = Column(JSON, nullable=True)  # Этапы интервью: introduction, softSkills, technical, liveCoding
    access_code = Column(String, nullable=True, index=True)  # Код доступа для кандидата
    difficulty = Column(String, default="medium", nullable=False)  # easy, medium, hard
    duration_minutes = Column(Integer, default=60, nullable=False)
    position = Column(String, nullable=True)  # Позиция: frontend, backend, devops, fullstack
    level = Column(String, nullable=True)  # Уровень: junior, middle, senior
    programming_languages = Column(JSON, nullable=True)  # Языки программирования
    timer = Column(JSON, nullable=True)  # Настройки таймера: {enabled: bool, technical_minutes: int, liveCoding_minutes: int}
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Новые поля для конфигурации интервью
    hr_prompt = Column(Text, nullable=True)  # Промпт от HR о вакансии и требованиях
    interview_config = Column(JSON, nullable=True)  # Конфигурация: языки, уровень, количество вопросов и т.д.
    
    # Связи
    sessions = relationship("InterviewSession", back_populates="interview")


class InterviewSession(Base):
    """Модель сессии собеседования"""
    __tablename__ = "interview_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(SQLEnum(InterviewStatus), default=InterviewStatus.SCHEDULED, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    total_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # v3.0.0: Статус заявки кандидата
    application_status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.ACTIVE, nullable=True)
    
    # Текущая стадия интервью
    current_stage = Column(String, default="introduction", nullable=True)  # introduction, technical, liveCoding
    stage_progress = Column(JSON, nullable=True)  # Прогресс по стадиям: {"introduction": {"questions_asked": 2, "completed": false}, ...}
    emotion_history = Column(JSON, nullable=True)  # История эмоций от EmotionAgent
    
    # Античит поля
    activity_history = Column(JSON, nullable=True)  # История активности пользователя
    suspicion_score = Column(Float, default=0.0, nullable=False)  # Оценка подозрительности (0-1)
    device_fingerprint = Column(String, nullable=True)  # Уникальный отпечаток устройства
    ip_address = Column(String, nullable=True)  # IP-адрес
    user_agent = Column(String, nullable=True)  # User-Agent браузера
    concurrent_sessions = Column(JSON, nullable=True)  # Информация о других активных сессиях
    ai_detection_results = Column(JSON, nullable=True)  # Результаты детекции AI
    typing_metrics = Column(JSON, nullable=True)  # Метрики печати
    warning_count = Column(Integer, default=0, nullable=False)  # Счетчик предупреждений (максимум 2)
    
    # Кеширование отчетов (для оптимизации производительности)
    cached_pdf_path = Column(String, nullable=True)  # Путь к кешированному PDF отчету
    ai_evaluation = Column(JSON, nullable=True)  # Кешированная AI оценка кандидата
    
    # Связи
    interview = relationship("Interview", back_populates="sessions")
    candidate = relationship("User", back_populates="interview_sessions")
    questions = relationship("Question", back_populates="session", cascade="all, delete-orphan")
    test_tasks = relationship("TestTask", back_populates="session", cascade="all, delete-orphan")


class Question(Base):
    """Модель вопроса в сессии"""
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(SQLEnum(QuestionType), nullable=False)
    topic = Column(String, nullable=True)
    difficulty = Column(String, nullable=True)
    expected_keywords = Column(JSON, nullable=True)
    hints = Column(JSON, nullable=True)
    order = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    shown_at = Column(DateTime, nullable=True)  # Время показа вопроса пользователю (для расчета time_to_answer)
    
    # Связи
    session = relationship("InterviewSession", back_populates="questions")
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")


class Answer(Base):
    """Модель ответа кандидата"""
    __tablename__ = "answers"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    answer_text = Column(Text, nullable=True)
    code_solution = Column(Text, nullable=True)  # Для coding вопросов
    score = Column(Float, nullable=True)
    evaluation = Column(JSON, nullable=True)  # Детальная оценка от AI
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Античит поля для ответов
    time_to_answer = Column(Float, nullable=True)  # Время в секундах от показа вопроса до ответа
    typing_speed = Column(Float, nullable=True)  # Скорость печати (символов/минуту)
    activity_during_answer = Column(JSON, nullable=True)  # Активность во время ответа
    
    # Связи
    question = relationship("Question", back_populates="answers")


class TestTask(Base):
    """Модель тестового задания (v3.0.0)"""
    __tablename__ = "test_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    task_type = Column(String, nullable=False)  # coding, design, essay, algorithm, etc.
    requirements = Column(JSON, nullable=True)  # Дополнительные требования
    deadline = Column(DateTime, nullable=True)
    status = Column(String, default="pending", nullable=False)  # pending, in_progress, completed, reviewed
    solution = Column(Text, nullable=True)  # Решение кандидата
    solution_files = Column(JSON, nullable=True)  # Файлы решения (если есть)
    score = Column(Float, nullable=True)  # Оценка решения
    feedback = Column(Text, nullable=True)  # Обратная связь от HR
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто проверил
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    session = relationship("InterviewSession", back_populates="test_tasks")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

