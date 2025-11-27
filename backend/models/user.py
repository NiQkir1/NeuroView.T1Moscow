"""Модели пользователей"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from backend.models import Base


class Role(str, enum.Enum):
    """Роли пользователей"""
    CANDIDATE = "candidate"
    HR = "hr"
    MODERATOR = "moderator"
    ADMIN = "admin"


class RoleType(str, enum.Enum):
    """Типы ролей разработчика"""
    FULLSTACK = "fullstack"
    BACKEND = "backend"
    FRONTEND = "frontend"
    DEVOPS = "devops"
    MOBILE = "mobile"
    DATA_SCIENCE = "data_science"
    QA = "qa"
    OTHER = "other"


class ExperienceLevel(str, enum.Enum):
    """Уровни опыта"""
    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"
    LEAD = "lead"


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(SQLEnum(Role), default=Role.CANDIDATE, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Mercor AI v2.0.0: Расширенный профиль кандидата
    github_username = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    skills = Column(JSON, nullable=True)  # Список навыков: ["Python", "JavaScript", ...]
    skill_matrix = Column(JSON, nullable=True)  # Детальная матрица навыков с уровнями
    work_experience = Column(JSON, nullable=True)  # История работы
    education = Column(JSON, nullable=True)  # Образование
    soft_skills_score = Column(JSON, nullable=True)  # Оценка soft skills
    culture_fit_score = Column(Float, nullable=True)  # Оценка соответствия культуре
    success_prediction = Column(JSON, nullable=True)  # Прогноз успешности
    external_profiles = Column(JSON, nullable=True)  # Данные из внешних источников
    
    # HR Search & Filter v2.0.0: Поля для поиска и фильтрации
    role_type = Column(SQLEnum(RoleType), nullable=True, index=True)  # fullstack, backend, frontend и т.д.
    experience_level = Column(SQLEnum(ExperienceLevel), nullable=True, index=True)  # junior, middle, senior, lead
    programming_languages = Column(JSON, nullable=True)  # ["Python", "JavaScript", "Java", ...]
    
    # v3.0.0: Интеграция с HH.ru
    hh_access_token = Column(String, nullable=True)  # OAuth токен доступа
    hh_refresh_token = Column(String, nullable=True)  # Refresh токен
    hh_token_expires_at = Column(DateTime, nullable=True)  # Время истечения токена
    hh_resume_id = Column(String, nullable=True)  # ID резюме на HH.ru
    hh_metrics = Column(JSON, nullable=True)  # Метрики из HH.ru: просмотры, rate откликов и т.д.
    hh_profile_synced_at = Column(DateTime, nullable=True)  # Время последней синхронизации
    
    # Связи (lazy loading для избежания проблем при загрузке профиля)
    interview_sessions = relationship("InterviewSession", back_populates="candidate", cascade="all, delete-orphan", lazy="select")

