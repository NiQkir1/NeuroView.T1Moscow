"""Главный файл FastAPI приложения"""
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import String, func
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel
from datetime import datetime, timedelta
import logging
import sys
from pathlib import Path

from backend.database import get_db, init_db
from backend.utils.logger import setup_logger, get_module_logger

# Настройка логирования
app_logger = setup_logger("NeuroView.API", logging.INFO)
logger = get_module_logger("API")
from backend.models import (
    Interview, InterviewSession, User, Role, Question, Answer, TestTask,
    ApplicationStatus
)
from backend.models.interview import InterviewStatus, QuestionType
from backend.models.user import RoleType, ExperienceLevel
from backend.models.message import Message, MessageStatus, InterviewInvitation
from backend.models.task_bank import TaskTemplate
from backend.services.ai_engine import ai_engine
from backend.services.interview_service import interview_service
from backend.services.code_executor import code_executor
from backend.utils.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token
)

# Инициализация приложения
app = FastAPI(
    title="NeuroView API",
    description="API для платформы AI-собеседований с функциями v3.0.0: HH.ru интеграция, тестовые задания, расширенные статусы",
    version="3.0.0"
)

# Настройка логирования uvicorn (отключаем цвета)
import os
os.environ.setdefault("UVICORN_NO_COLORS", "1")

# Настраиваем логирование uvicorn
from backend.utils.logger import configure_uvicorn_logging
configure_uvicorn_logging()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type"],
)

# Security
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


# Dependency для получения текущего пользователя
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Получение текущего пользователя из JWT токена"""
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Не загружаем связанные объекты, чтобы избежать проблем с новыми полями
    # SQLAlchemy будет использовать lazy loading только при необходимости
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Опциональное получение текущего пользователя.
    Если токен не передан, возвращаем None. Если токен недействителен — выбрасываем 401.
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


# Dependency для проверки роли admin
async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Проверка что пользователь является администратором"""
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user


async def get_hr_or_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Проверка что пользователь является HR или администратором"""
    if current_user.role not in [Role.ADMIN, Role.HR]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user


# Инициализация БД и логирование при старте
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("NeuroView API запускается...")
    logger.info("Версия: 3.0.0")
    logger.info("=" * 60)
    
    # Инициализация БД
    init_db()
    logger.info("База данных инициализирована")
    
    # Создаем пользователя admin если его нет
    db = next(get_db())
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@neuroview.com",
                hashed_password=get_password_hash("admin"),
                role=Role.ADMIN,
                full_name="Administrator"
            )
            db.add(admin_user)
            db.commit()
            logger.info("Пользователь admin создан")
        else:
            logger.info("Пользователь admin уже существует")
    except Exception as e:
        logger.error(f"Ошибка при создании admin пользователя: {e}")
    finally:
        db.close()
    
    logger.info("NeuroView API успешно запущен")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("=" * 60)
    logger.info("NeuroView API останавливается...")
    logger.info("=" * 60)


# Health check
@app.get("/health")
async def health_check():
    """Проверка работоспособности API"""
    from backend.config import get_scibox_config
    
    scibox_config = get_scibox_config()
    has_api_key = scibox_config is not None
    
    return {
        "status": "ok",
        "service": "neuroview-api",
        "mode": "demo" if not has_api_key else "production",
        "message": "Демо-режим: SciBox API ключ не настроен" if not has_api_key else "SciBox API ключ настроен",
        "provider": "scibox"
    }


# Auth endpoints
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@app.post("/api/auth/register", response_model=LoginResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    # Проверяем, существует ли пользователь с таким именем
    existing_user_by_username = db.query(User).filter(User.username == request.username).first()
    if existing_user_by_username:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Проверяем, существует ли пользователь с таким email (если email указан)
    if request.email:
        existing_user_by_email = db.query(User).filter(User.email == request.email).first()
        if existing_user_by_email:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Создаем нового пользователя
    hashed_password = get_password_hash(request.password)
    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hashed_password,
        full_name=request.full_name,
        role=Role.CANDIDATE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Создаем токен
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return LoginResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        )
    )


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Вход в систему"""
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    # Проверка is_active только для не-админов
    if not user.is_active and user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="User is inactive")
    
    # Создаем токен
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return LoginResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        )
    )


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Получение информации о текущем пользователе"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat()
    )


# Admin endpoints
@app.get("/api/admin/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Получение списка всех пользователей (только для админа)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        )
        for user in users
    ]


class UpdateUserRoleRequest(BaseModel):
    role: str


@app.patch("/api/admin/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    request: UpdateUserRoleRequest,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Обновление роли пользователя (только для админа)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Проверяем что роль валидна
    try:
        new_role = Role(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {request.role}")
    
    # Не позволяем менять роль админа
    if user.role == Role.ADMIN and new_role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Cannot change admin role")
    
    user.role = new_role
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at.isoformat()
    )


@app.get("/api/admin/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Получение информации о пользователе (только для админа)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at.isoformat()
    )


@app.delete("/api/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Удаление пользователя (только для админа)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Не позволяем удалять самого себя
    if user.id == admin_user.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя. Используйте другой аккаунт администратора.")
    
    # Не позволяем удалять других администраторов
    if user.role == Role.ADMIN:
        raise HTTPException(status_code=403, detail="Нельзя удалять администраторов. Сначала измените роль пользователя.")
    
    try:
        # Удаляем все сессии кандидата, чтобы одновременно удалить отчеты и связанные данные
        sessions = db.query(InterviewSession).filter(InterviewSession.candidate_id == user.id).all()
        for session in sessions:
            db.delete(session)
        
        # Отвязываем сущности, где достаточно обнулить ссылку на пользователя
        db.query(Interview).filter(Interview.created_by == user.id).update({Interview.created_by: None})
        db.query(TestTask).filter(TestTask.reviewed_by == user.id).update({TestTask.reviewed_by: None})
        db.query(TaskTemplate).filter(TaskTemplate.created_by == user.id).update({TaskTemplate.created_by: None})
        db.flush()
        
        # Удаляем пользователя (сессии уже удалены, отчеты исчезают вместе с ними)
        db.delete(user)
        db.commit()
        
        logger.info(f"Admin {admin_user.username} (ID: {admin_user.id}) deleted user {user.username} (ID: {user.id})")
        
        return {"message": "Пользователь успешно удален"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении пользователя: {str(e)}")


# User profile with interview reports
class InterviewReport(BaseModel):
    id: int
    interview_id: int
    interview_title: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    total_score: Optional[float]
    created_at: str
    questions_count: int
    answered_count: int
    candidate_name: Optional[str] = None
    candidate_position: Optional[str] = None


class UserProfileResponse(BaseModel):
    user: UserResponse
    interview_reports: List[InterviewReport]


@app.get("/api/admin/users/{user_id}/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: int,
    current_user: User = Depends(get_hr_or_admin_user),
    db: Session = Depends(get_db)
):
    """Получение профиля пользователя с отчетами о собеседованиях (для HR и админа)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Получаем все сессии собеседований пользователя с eager loading
    sessions = db.query(InterviewSession).options(
        joinedload(InterviewSession.interview),
        joinedload(InterviewSession.questions).joinedload(Question.answers)
    ).filter(InterviewSession.candidate_id == user_id).all()
    
    reports = []
    for session in sessions:
        # Используем загруженные связи
        interview = session.interview
        
        # Получаем вопросы и ответы (уже загружены)
        questions = session.questions
        answered_count = sum(1 for q in questions if q.answers)
        
        # Формируем имя кандидата и должность
        candidate_name = user.full_name if user.full_name else user.username
        candidate_position = interview.title if interview else "Позиция не указана"
        
        reports.append(InterviewReport(
            id=session.id,
            interview_id=session.interview_id,
            interview_title=interview.title if interview else "Unknown",
            status=session.status.value if hasattr(session.status, 'value') else str(session.status),
            started_at=session.started_at.isoformat() if session.started_at else None,
            completed_at=session.completed_at.isoformat() if session.completed_at else None,
            total_score=session.total_score,
            created_at=session.created_at.isoformat() if session.created_at else None,
            questions_count=len(questions),
            answered_count=answered_count,
            candidate_name=candidate_name,
            candidate_position=candidate_position
        ))
    
    return UserProfileResponse(
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        ),
        interview_reports=reports
    )


# All reports endpoint
class FullReport(BaseModel):
    id: int
    interview_id: int
    interview_title: str
    candidate_id: int
    candidate_username: str
    candidate_full_name: Optional[str]
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    total_score: Optional[float]
    created_at: str
    questions_count: int
    answered_count: int


@app.get("/api/admin/reports", response_model=List[FullReport])
async def get_all_reports(
    sort_by: str = "created_at",  # created_at, username
    sort_order: str = "desc",  # asc, desc
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Получение всех отчетов о собеседованиях (только для админа)"""
    try:
        # Получаем все сессии
        query = db.query(InterviewSession)
        
        # Применяем сортировку
        if sort_by == "username":
            # Сортировка по имени пользователя требует join
            query = query.join(User, InterviewSession.candidate_id == User.id)
            if sort_order == "asc":
                query = query.order_by(User.username.asc())
            else:
                query = query.order_by(User.username.desc())
        else:  # sort_by == "created_at"
            if sort_order == "asc":
                query = query.order_by(InterviewSession.created_at.asc())
            else:
                query = query.order_by(InterviewSession.created_at.desc())
        
        # Используем eager loading для оптимизации
        query = query.options(
            joinedload(InterviewSession.candidate),
            joinedload(InterviewSession.interview),
            joinedload(InterviewSession.questions).joinedload(Question.answers)
        )
        sessions = query.all()
    except Exception as e:
        # Если ошибка из-за отсутствия столбцов, возвращаем пустой список
        # (миграция должна была добавить их, но на всякий случай обрабатываем)
        error_str = str(e).lower()
        if "no such column" in error_str or "operationalerror" in error_str:
            # Пытаемся выполнить миграцию и повторить запрос
            try:
                from backend.database import _migrate_db
                _migrate_db()
                # Повторяем запрос после миграции
                query = db.query(InterviewSession)
                if sort_by == "created_at":
                    if sort_order == "asc":
                        query = query.order_by(InterviewSession.created_at.asc())
                    else:
                        query = query.order_by(InterviewSession.created_at.desc())
                query = query.options(
                    joinedload(InterviewSession.candidate),
                    joinedload(InterviewSession.interview),
                    joinedload(InterviewSession.questions).joinedload(Question.answers)
                )
                sessions = query.all()
            except Exception:
                # Если миграция не помогла, возвращаем пустой список
                return []
        else:
            raise HTTPException(status_code=500, detail=f"Ошибка загрузки отчетов: {str(e)}")
    
    reports = []
    for session in sessions:
        # Используем загруженные связи
        candidate = session.candidate
        interview = session.interview
        
        # Получаем вопросы и ответы (уже загружены)
        questions = session.questions
        answered_count = sum(1 for q in questions if q.answers)
        
        reports.append(FullReport(
            id=session.id,
            interview_id=session.interview_id,
            interview_title=interview.title if interview else "Unknown",
            candidate_id=session.candidate_id,
            candidate_username=candidate.username if candidate else "Unknown",
            candidate_full_name=candidate.full_name if candidate else None,
            status=session.status.value if hasattr(session.status, 'value') else str(session.status),
            started_at=session.started_at.isoformat() if session.started_at else None,
            completed_at=session.completed_at.isoformat() if session.completed_at else None,
            total_score=session.total_score,
            created_at=session.created_at.isoformat() if session.created_at else None,
            questions_count=len(questions),
            answered_count=answered_count
        ))
    
    return reports


# AI Engine endpoints
@app.post("/api/ai/generate-question")
async def generate_question(
    topic: str,
    difficulty: str = "medium",
    db: Session = Depends(get_db)
):
    """Генерация вопроса для собеседования"""
    try:
        question = await ai_engine.generate_question(
            topic=topic,
            difficulty=difficulty
        )
        return question
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class EvaluateAnswerRequest(BaseModel):
    """Запрос на оценку ответа кандидата"""
    question: str
    answer: str
    expected_keywords: Optional[List[str]] = None
    code: Optional[str] = None
    language: Optional[str] = None
    test_cases: Optional[List[Dict[str, Any]]] = None  # Тестовые случаи для кода
    run_tests: Optional[bool] = True  # Запускать ли тесты


@app.post("/api/ai/evaluate-answer")
async def evaluate_answer(
    request: EvaluateAnswerRequest,
    db: Session = Depends(get_db)
):
    """Оценка ответа кандидата (для тренировочного режима и быстрой оценки)
    
    Логика оценки кода:
    1. Если код пустой или не связан с задачей - 0 баллов
    2. Если код не запускается из-за ошибок:
       - Оценить задумку/логику
       - Если хорошая задумка - до 50 баллов
    3. Если код запускается:
       - Оценить прохождение тестов
       - Оценить качество кода
       - Итоговая оценка на основе всех факторов
    """
    from backend.services.agents import coding_agent
    
    try:
        question = request.question
        answer = request.answer
        code = request.code
        language = request.language
        test_cases = request.test_cases or []
        
        # Если answer выглядит как код (содержит def, function, class и т.д.), 
        # автоматически определяем его как код
        is_code = code is not None or any(keyword in answer for keyword in [
            'def ', 'function ', 'class ', 'public ', 'private ', 
            'import ', 'from ', '#include', 'package ', 'using ',
            'console.log', 'print(', 'System.out', 'cout <<'
        ])
        
        # Определяем язык программирования если не указан
        if is_code and not language:
            if 'def ' in answer or 'import ' in answer or 'print(' in answer:
                language = 'python'
            elif 'function ' in answer or 'const ' in answer or 'let ' in answer or 'console.log' in answer:
                language = 'javascript'
            elif 'public static void main' in answer or 'System.out' in answer:
                language = 'java'
            elif '#include' in answer or 'cout <<' in answer:
                language = 'cpp'
            else:
                language = 'python'  # По умолчанию
        
        # Если это код, используем CodingAgent для полной оценки
        if is_code:
            code_to_evaluate = code or answer
            
            # Проверяем, пустой ли код или не связан с задачей
            code_stripped = code_to_evaluate.strip()
            code_lines = [line.strip() for line in code_stripped.split('\n') 
                         if line.strip() and not line.strip().startswith('#') 
                         and not line.strip().startswith('//')]
            actual_code_content = '\n'.join(code_lines)
            
            # Если код слишком короткий - 0 баллов
            if len(actual_code_content) < 20:
                return {
                    "score": 0,
                    "correctness": 0,
                    "completeness": 0,
                    "quality": 0,
                    "optimality": 0,
                    "feedback": "Код не предоставлен или слишком короткий. Пожалуйста, напишите полное решение задачи.",
                    "strengths": [],
                    "improvements": ["Предоставьте полное решение задачи"],
                    "test_results": [],
                    "tests_passed": 0,
                    "tests_total": len(test_cases)
                }
            
            # Проверяем, содержит ли код только заглушки
            default_patterns = ["// Start writing code here", "def solution():\n    pass", "pass"]
            is_stub = any(pattern in code_to_evaluate for pattern in default_patterns) and len(actual_code_content) < 60
            
            if is_stub:
                return {
                    "score": 0,
                    "correctness": 0,
                    "completeness": 0,
                    "quality": 0,
                    "optimality": 0,
                    "feedback": "Код содержит только заглушку. Пожалуйста, реализуйте решение задачи.",
                    "strengths": [],
                    "improvements": ["Напишите полное решение задачи"],
                    "test_results": [],
                    "tests_passed": 0,
                    "tests_total": len(test_cases)
                }
            
            # Оцениваем код через CodingAgent
            try:
                evaluation = await coding_agent.process({
                    "action": "evaluate_code",
                    "question": question,
                    "code": code_to_evaluate,
                    "language": language or "python",
                    "test_cases": test_cases,
                })
                
                # Преобразуем результат в стандартный формат
                return {
                    "score": evaluation.get("score", 0),
                    "correctness": evaluation.get("correctness", 0),
                    "completeness": evaluation.get("readability", 5),
                    "quality": evaluation.get("readability", 5),
                    "optimality": evaluation.get("efficiency", 5),
                    "feedback": evaluation.get("feedback", ""),
                    "strengths": evaluation.get("strengths", []),
                    "improvements": evaluation.get("improvements", []),
                    "test_results": evaluation.get("test_results", []),
                    "tests_passed": evaluation.get("tests_passed", 0),
                    "tests_total": evaluation.get("tests_total", 0),
                    "tests_passed_ratio": evaluation.get("tests_passed_ratio", 0),
                    "avg_execution_time": evaluation.get("avg_execution_time", 0),
                    "quality_analysis": evaluation.get("quality_analysis"),
                }
            except Exception as e:
                logger.error(f"Ошибка при оценке кода через CodingAgent: {e}")
                # Fallback на базовую оценку через ai_engine
                evaluation = await ai_engine.evaluate_answer(
                    question=question,
                    answer=answer,
                    expected_keywords=request.expected_keywords,
                    code=code_to_evaluate,
                    language=language,
                    question_type='coding'
                )
                return evaluation
        else:
            # Для текстовых ответов используем обычную оценку
            evaluation = await ai_engine.evaluate_answer(
                question=question,
                answer=answer,
                expected_keywords=request.expected_keywords,
                code=None,
                language=None,
                question_type=None
            )
            return evaluation
    except Exception as e:
        logger.error(f"Ошибка в evaluate_answer: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Interview endpoints
@app.get("/api/interviews")
async def get_interviews(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Получение списка собеседований"""
    interviews = db.query(Interview).offset(skip).limit(limit).all()
    return interviews


@app.get("/api/interviews/{interview_id}")
async def get_interview(
    interview_id: int,
    db: Session = Depends(get_db)
):
    """Получение собеседования по ID"""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview


@app.get("/api/interviews/by-code/{code}")
async def get_interview_by_code(
    code: str,
    db: Session = Depends(get_db)
):
    """Получение собеседования по коду доступа"""
    # Нормализуем код: убираем пробелы и приводим к верхнему регистру
    from sqlalchemy import func
    normalized_code = code.strip().upper()
    interview = db.query(Interview).filter(
        func.upper(func.trim(Interview.access_code)) == normalized_code
    ).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview


@app.get("/api/sessions/{session_id}")
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение сессии собеседования с проверкой прав доступа"""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Проверка прав доступа
    has_access = False
    
    if current_user.role == Role.ADMIN:
        # Администратор видит все сессии
        has_access = True
    elif current_user.role == Role.HR:
        # HR видит только сессии интервью, которые он создал или отправил приглашения
        interview = session.interview
        if interview and interview.created_by == current_user.id:
            has_access = True
        else:
            # Проверяем приглашения
            invitation = db.query(InterviewInvitation).filter(
                InterviewInvitation.interview_id == session.interview_id,
                InterviewInvitation.hr_id == current_user.id
            ).first()
            if invitation:
                has_access = True
    else:
        # Кандидаты видят только свои сессии
        if session.candidate_id == current_user.id:
            has_access = True
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Not enough permissions to access this session")
    
    return session


@app.post("/api/sessions/{session_id}/complete")
async def complete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Завершение сессии собеседования"""
    try:
        # Проверяем, что сессия принадлежит текущему пользователю
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id,
            InterviewSession.candidate_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Завершаем сессию
        completed_session = await interview_service.complete_session(
            db=db,
            session_id=session_id
        )
        
        return {
            "message": "Session completed successfully",
            "session_id": completed_session.id,
            "status": completed_session.status.value if hasattr(completed_session.status, 'value') else str(completed_session.status),
            "total_score": completed_session.total_score,
            "completed_at": completed_session.completed_at.isoformat() if completed_session.completed_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/report/pdf")
async def get_session_pdf_report(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Генерация и скачивание PDF отчета для сессии интервью"""
    try:
        from backend.services.report_service import report_service
        
        logger.info(f"Запрос PDF отчета для сессии {session_id} (пользователь: {current_user.username}, роль: {current_user.role})")
        
        # Проверяем права доступа
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        if not session:
            logger.warning(f"Сессия {session_id} не найдена")
            raise HTTPException(status_code=404, detail="Session not found")
        
        logger.info(f"Сессия {session_id} найдена: candidate_id={session.candidate_id}, interview_id={session.interview_id}, status={session.status}")
        
        # Проверка прав доступа
        has_access = False
        if current_user.role == Role.ADMIN:
            has_access = True
        elif current_user.role == Role.HR:
            interview = session.interview
            if interview and interview.created_by == current_user.id:
                has_access = True
            else:
                from backend.models.message import InterviewInvitation
                invitation = db.query(InterviewInvitation).filter(
                    InterviewInvitation.interview_id == session.interview_id,
                    InterviewInvitation.hr_id == current_user.id
                ).first()
                if invitation:
                    has_access = True
        else:
            if session.candidate_id == current_user.id:
                has_access = True
        
        if not has_access:
            logger.warning(f"Пользователь {current_user.username} (ID: {current_user.id}, роль: {current_user.role}) не имеет доступа к сессии {session_id}")
            raise HTTPException(status_code=403, detail="Not enough permissions to access this session")
        
        logger.info(f"Доступ разрешен для пользователя {current_user.username}")
        
        # Генерация PDF отчета
        try:
            # Если PDF генератор был недоступен, пытаемся переинициализировать
            if not report_service.pdf_available:
                logger.info("Попытка переинициализации PDF генератора...")
                # Пытаемся импортировать reportlab напрямую
                try:
                    import reportlab
                    import sys
                    logger.info(f"reportlab обнаружен (версия: {reportlab.Version}, Python: {sys.executable})")
                    # Переинициализируем сервис
                    from backend.services.report_service import reinitialize_report_service
                    reinitialize_report_service()
                    logger.info("PDF генератор переинициализирован")
                except ImportError as import_err:
                    logger.error(f"reportlab не найден: {import_err}")
                    raise HTTPException(
                        status_code=503,
                        detail=f"PDF генератор недоступен. reportlab не установлен в {sys.executable}. Установите: pip install reportlab>=4.0.0"
                    )
            
            if not report_service.pdf_available:
                raise HTTPException(
                    status_code=503,
                    detail="PDF генератор недоступен. Установите reportlab: pip install reportlab>=4.0.0"
                )
            
            logger.info(f"Генерация PDF отчета для сессии {session_id}...")
            pdf_path = report_service.generate_pdf_report(db, session_id)
            logger.info(f"PDF отчет успешно создан: {pdf_path}")
            
            # Проверяем существование файла (используем абсолютный путь)
            pdf_file = Path(pdf_path).resolve()
            if not pdf_file.exists():
                logger.error(f"PDF файл не найден по пути: {pdf_file}")
                raise HTTPException(
                    status_code=500,
                    detail=f"PDF файл не найден: {pdf_path}"
                )
            
            logger.info(f"PDF файл найден: {pdf_file} (размер: {pdf_file.stat().st_size} байт)")
            
            # Формируем имя файла для скачивания
            candidate_name = session.candidate.full_name or session.candidate.username if session.candidate else "Unknown"
            
            # Создаем ASCII-безопасное имя для параметра filename (для совместимости)
            import re
            safe_name_ascii = re.sub(r'[^\w\s-]', '', candidate_name)
            safe_name_ascii = re.sub(r'[-\s]+', '_', safe_name_ascii)
            # Транслитерация кириллицы в латиницу для ASCII-безопасного имени
            def transliterate(text):
                """Простая транслитерация кириллицы в латиницу"""
                cyrillic_to_latin = {
                    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
                    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
                    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
                    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
                    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
                    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
                    'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
                    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
                    'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
                    'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
                }
                return ''.join(cyrillic_to_latin.get(c, c) for c in text)
            
            safe_name_ascii = transliterate(safe_name_ascii)
            ascii_filename = f"report_{safe_name_ascii}_{session_id}.pdf"
            
            # Оригинальное имя с кириллицей для заголовка
            original_filename = f"report_{candidate_name}_{session_id}.pdf"
            # Очищаем от недопустимых символов для имени файла
            safe_original = "".join(c if c.isalnum() or c in (' ', '-', '_', '.') else '_' for c in original_filename)
            
            # Кодируем имя файла для заголовка Content-Disposition (RFC 5987)
            import urllib.parse
            encoded_filename = urllib.parse.quote(safe_original.encode('utf-8'))
            content_disposition = f'attachment; filename="{ascii_filename}"; filename*=UTF-8\'\'{encoded_filename}'
            
            # Возвращаем файл с ASCII-безопасным именем в параметре filename
            # и правильным кодированием в заголовке Content-Disposition
            return FileResponse(
                path=str(pdf_file),
                filename=ascii_filename,  # ASCII-безопасное имя для совместимости
                media_type="application/pdf",
                headers={
                    "Content-Disposition": content_disposition,
                    "Content-Type": "application/pdf"
                }
            )
        except ImportError as e:
            logger.error(f"PDF генератор недоступен: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"PDF генератор недоступен: {str(e)}. Установите reportlab: pip install reportlab>=4.0.0"
            )
    except ValueError as e:
        logger.error(f"ValueError при генерации PDF отчета для сессии {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Ошибка валидации данных: {str(e)}")
    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error(f"Файл не найден при генерации PDF отчета для сессии {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка доступа к файлу отчета: {str(e)}")
    except PermissionError as e:
        logger.error(f"Ошибка прав доступа при генерации PDF отчета для сессии {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка прав доступа к файлу отчета: {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка при генерации PDF отчета для сессии {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации PDF: {str(e)}")


@app.post("/api/admin/reports/reinitialize")
async def reinitialize_report_service_endpoint(
    current_user: User = Depends(get_current_user),
):
    """Переинициализация сервиса отчетов (для админов)"""
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Только администраторы могут переинициализировать сервис")
    
    try:
        from backend.services.report_service import reinitialize_report_service
        reinitialize_report_service()
        
        from backend.services.report_service import report_service
        if report_service.pdf_available:
            return {
                "success": True,
                "message": "PDF генератор успешно переинициализирован",
                "pdf_available": True
            }
        else:
            return {
                "success": False,
                "message": "PDF генератор недоступен. Установите reportlab: pip install reportlab>=4.0.0",
                "pdf_available": False
            }
    except Exception as e:
        logger.error(f"Ошибка переинициализации сервиса отчетов: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка переинициализации: {str(e)}")


@app.get("/api/sessions/{session_id}/report/json")
async def get_session_json_report(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение JSON отчета для сессии интервью"""
    try:
        logger.info(f"Запрос JSON отчета для сессии {session_id} (пользователь: {current_user.username})")
        from backend.services.report_service import report_service
        
        # Проверяем права доступа
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Проверка прав доступа
        has_access = False
        if current_user.role == Role.ADMIN:
            has_access = True
        elif current_user.role == Role.HR:
            interview = session.interview
            if interview and interview.created_by == current_user.id:
                has_access = True
            else:
                from backend.models.message import InterviewInvitation
                invitation = db.query(InterviewInvitation).filter(
                    InterviewInvitation.interview_id == session.interview_id,
                    InterviewInvitation.hr_id == current_user.id
                ).first()
                if invitation:
                    has_access = True
        else:
            if session.candidate_id == current_user.id:
                has_access = True
        
        if not has_access:
            raise HTTPException(status_code=403, detail="Not enough permissions to access this session")
        
        # Экспортируем данные в JSON
        json_data = report_service.export_session_to_json(db, session_id)
        logger.info(f"JSON отчет успешно сгенерирован для сессии {session_id}")
        
        return json_data
    except ValueError as e:
        logger.warning(f"Сессия {session_id} не найдена: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при генерации JSON отчета для сессии {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interviews/{interview_id}/complete")
async def complete_interview_by_id(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Завершение сессии собеседования по interview_id (находит активную сессию для текущего пользователя)"""
    try:
        # Находим активную сессию для этого интервью и пользователя
        # Ищем сессии со статусом IN_PROGRESS, SCHEDULED или даже COMPLETED (на случай повторного вызова)
        session = db.query(InterviewSession).filter(
            InterviewSession.interview_id == interview_id,
            InterviewSession.candidate_id == current_user.id
        ).order_by(InterviewSession.created_at.desc()).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found for this interview")
        
        # Если сессия уже завершена, просто возвращаем её
        if session.status == InterviewStatus.COMPLETED:
            return {
                "message": "Session already completed",
                "session_id": session.id,
                "interview_id": session.interview_id,
                "status": session.status.value if hasattr(session.status, 'value') else str(session.status),
                "total_score": session.total_score,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None
            }
        
        # Завершаем сессию
        completed_session = await interview_service.complete_session(
            db=db,
            session_id=session.id
        )
        
        return {
            "message": "Session completed successfully",
            "session_id": completed_session.id,
            "interview_id": completed_session.interview_id,
            "status": completed_session.status.value if hasattr(completed_session.status, 'value') else str(completed_session.status),
            "total_score": completed_session.total_score,
            "completed_at": completed_session.completed_at.isoformat() if completed_session.completed_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/user/sessions")
async def get_user_sessions(
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение истории интервью пользователя с проверкой прав доступа"""
    try:
        query = db.query(InterviewSession)
        
        # Проверка прав доступа
        if current_user.role == Role.ADMIN:
            # Администратор видит все сессии
            if user_id:
                query = query.filter(InterviewSession.candidate_id == user_id)
        elif current_user.role == Role.HR:
            # HR видит только сессии интервью, которые он создал или отправил приглашения
            # Находим все интервью, созданные этим HR
            hr_interviews = db.query(Interview).filter(Interview.created_by == current_user.id).all()
            hr_interview_ids = [inv.id for inv in hr_interviews]
            
            # Находим все приглашения, отправленные этим HR
            hr_invitations = db.query(InterviewInvitation).filter(InterviewInvitation.hr_id == current_user.id).all()
            invitation_interview_ids = [inv.interview_id for inv in hr_invitations]
            
            # Объединяем ID интервью
            allowed_interview_ids = list(set(hr_interview_ids + invitation_interview_ids))
            
            if allowed_interview_ids:
                query = query.filter(InterviewSession.interview_id.in_(allowed_interview_ids))
            else:
                # Если HR не создал ни одного интервью и не отправил приглашений, возвращаем пустой список
                return []
        else:
            # Кандидаты видят только свои сессии
            query = query.filter(InterviewSession.candidate_id == current_user.id)
            # Игнорируем user_id для кандидатов - они видят только свои данные
        
        # Используем eager loading только для базовых связей
        query = query.options(
            joinedload(InterviewSession.interview),
            joinedload(InterviewSession.candidate)
        )
        sessions = query.order_by(InterviewSession.created_at.desc()).offset(skip).limit(limit).all()
        
        result = []
        for session in sessions:
            # Используем загруженные связи
            interview = session.interview
            candidate = session.candidate
            
            # Подсчитываем статистику без загрузки всех данных
            questions_count = db.query(Question).filter(Question.session_id == session.id).count()
            
            # Получаем количество ответов и среднюю оценку одним запросом
            answers_stats = db.query(
                func.count(Answer.id).label('count'),
                func.avg(Answer.score).label('avg_score')
            ).join(Question).filter(Question.session_id == session.id).first()
            
            answered_count = answers_stats.count if answers_stats else 0
            avg_score = answers_stats.avg_score if answers_stats and answers_stats.avg_score else 0
            
            # Извлекаем позицию и уровень из interview_config
            position = None
            level = None
            if interview and interview.interview_config:
                position = interview.interview_config.get("position")
                level = interview.interview_config.get("level")
            
            # Если позиция не найдена в interview_config, используем difficulty как уровень
            if not level and interview:
                level = interview.difficulty
            
            result.append({
                "id": session.id,
                "interview_id": session.interview_id,
                "status": session.status.value if hasattr(session.status, 'value') else str(session.status),
                "application_status": session.application_status.value if session.application_status else None,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "total_score": session.total_score or avg_score,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "questions_count": questions_count,
                "answered_count": answered_count,
                "candidate_name": candidate.full_name or candidate.username if candidate else None,
                "position": position,
                "difficulty": level or (interview.difficulty if interview else None),
                "summary": {
                    "average_score": round(avg_score, 2) if avg_score else 0,
                    "total_questions": questions_count,
                    "answered_questions": answered_count,
                    "answers": []  # Не загружаем детали ответов для списка (оптимизация)
                }
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CreateInterviewRequest(BaseModel):
    title: str
    description: Optional[str] = None
    topics: Optional[List[str]] = None
    difficulty: str = "medium"
    duration_minutes: int = 60
    position: Optional[str] = None
    question_count: int = 5
    stages: Optional[Dict[str, Any]] = None
    access_code: Optional[str] = None
    hr_prompt: Optional[str] = None  # Промпт от HR о вакансии
    timer: Optional[Dict[str, Any]] = None  # Настройки таймера: {enabled: bool, technical_minutes: int, liveCoding_minutes: int}
    interview_config: Optional[Dict[str, Any]] = None  # Конфигурация: языки, уровень, количество вопросов
    candidate_id: Optional[int] = None  # ID кандидата для отправки приглашения
    invitation_message: Optional[str] = None  # Персональное сообщение для кандидата

class CodeVerificationRequest(BaseModel):
    code: str

@app.post("/api/interviews")
async def create_interview(
    request: CreateInterviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создание нового собеседования"""
    try:
        # Формируем interview_config из request, если не передан напрямую
        interview_config = request.interview_config if request.interview_config else {}
        
        # Если конфигурация пустая или недостаточная, создаем минимальную
        if not interview_config or not interview_config.get('position'):
            default_config = {
                "level": request.difficulty,  # Можно сделать отдельное поле
                "position": request.position or "fullstack",
                "programming_languages": request.topics or ["python"],  # Можно сделать отдельное поле
                "question_count": request.question_count,
                "questions_per_stage": {
                    "introduction": request.question_count // 3 if request.question_count >= 3 else 1,
                    "technical": request.question_count // 3 if request.question_count >= 3 else 1,
                    "liveCoding": request.question_count - 2 * (request.question_count // 3) if request.question_count >= 3 else 1,
                }
            }
            # Обновляем конфигурацию, сохраняя переданные поля
            for key, value in default_config.items():
                if key not in interview_config:
                    interview_config[key] = value
        
        # Добавляем настройки таймера в interview_config
        if request.timer:
            interview_config['timer'] = request.timer
        
        # ВАЖНО: Добавляем stages в interview_config для правильного определения активных стадий
        if request.stages:
            interview_config['stages'] = request.stages
        
        # Генерируем access_code если не передан
        access_code = request.access_code
        if not access_code:
            import random
            import string
            access_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Извлекаем данные из interview_config для отдельных полей
        position = interview_config.get('position', request.position)
        level = interview_config.get('level')
        programming_languages = interview_config.get('programming_languages', [])
        
        interview = await interview_service.create_interview(
            db=db,
            title=request.title,
            description=request.description,
            topics=request.topics,
            stages=request.stages,
            access_code=access_code,
            difficulty=request.difficulty,
            duration_minutes=request.duration_minutes,
            position=position,
            level=level,
            programming_languages=programming_languages,
            timer=request.timer,
            hr_prompt=request.hr_prompt,
            interview_config=interview_config,
            created_by=current_user.id if current_user else None,
        )
        
        # Chat & Invitations v2.0.0: Отправка приглашения кандидату, если указан
        if request.candidate_id and current_user and current_user.role in [Role.HR, Role.ADMIN]:
            from backend.services.message_service import invitation_service
            await invitation_service.create_invitation(
                db=db,
                interview_id=interview.id,
                candidate_id=request.candidate_id,
                hr_id=current_user.id,
                message=request.invitation_message,
                expires_in_days=7
            )
        
        # Возвращаем JSON вместо SQLAlchemy объекта
        return {
            "id": interview.id,
            "title": interview.title,
            "description": interview.description,
            "topics": interview.topics,
            "difficulty": interview.difficulty,
            "duration_minutes": interview.duration_minutes,
            "code": interview.access_code,
            "position": request.position,
            "created_at": interview.created_at.isoformat() if interview.created_at else None,
            "interview_config": interview.interview_config,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/interviews/{interview_id}/verify-code")
async def verify_interview_code(
    interview_id: int,
    request: CodeVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Проверка кода доступа к интервью и создание сессии"""
    try:
        interview = db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        valid = False
        if not interview.access_code:
            # Если код не установлен, доступ разрешен
            valid = True
        elif interview.access_code and request.code:
            # Нормализуем коды: убираем пробелы и приводим к верхнему регистру
            normalized_code = request.code.strip().upper()
            normalized_access_code = interview.access_code.strip().upper()
            if normalized_access_code == normalized_code:
                valid = True
        
        if valid and current_user:
            # Создаем сессию, если её еще нет
            existing_session = db.query(InterviewSession).filter(
                InterviewSession.interview_id == interview_id,
                InterviewSession.candidate_id == current_user.id,
                InterviewSession.status.in_([InterviewStatus.IN_PROGRESS, InterviewStatus.SCHEDULED])
            ).first()
            
            if not existing_session:
                session = await interview_service.start_session(
                    db=db,
                    interview_id=interview_id,
                    candidate_id=current_user.id
                )
                return {"valid": True, "message": "Access granted", "session_id": session.id}
            else:
                return {"valid": True, "message": "Access granted", "session_id": existing_session.id}
        
        if valid:
            return {"valid": True, "message": "Access granted"}
        else:
            return {"valid": False, "message": "Invalid access code"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interviews/{interview_id}/use-code")
async def use_interview_code(
    interview_id: int,
    db: Session = Depends(get_db)
):
    """Использование кода доступа (удаление кода, делаем одноразовым)"""
    try:
        interview = db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        # Удаляем код доступа после использования
        interview.access_code = None
        db.commit()
        
        return {"message": "Code used successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/questions")
async def generate_question_for_session(
    session_id: int,
    topic: str = None,
    db: Session = Depends(get_db)
):
    """Генерация вопроса для сессии"""
    try:
        question = await interview_service.generate_question_for_session(
            db=db,
            session_id=session_id,
            topic=topic
        )
        return question
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SubmitAnswerRequest(BaseModel):
    answer_text: Optional[str] = None
    code_solution: Optional[str] = None
    emotions: Optional[Dict[str, Any]] = None  # Данные от GigaAM emo
    time_to_answer: Optional[float] = None  # Время в секундах от показа вопроса до ответа
    typing_metrics: Optional[Dict[str, Any]] = None  # Метрики печати
    activity_during_answer: Optional[List[Dict[str, Any]]] = None  # Активность во время ответа

@app.post("/api/questions/{question_id}/answers")
async def submit_answer(
    question_id: int,
    request: SubmitAnswerRequest,
    db: Session = Depends(get_db)
):
    """Отправка ответа на вопрос"""
    try:
        logger.info(f"[SUBMIT_ANSWER] Начало обработки ответа на вопрос {question_id}")
        logger.info(f"[SUBMIT_ANSWER] answer_text: {request.answer_text[:100] if request.answer_text else 'None'}...")
        logger.info(f"[SUBMIT_ANSWER] code_solution: {request.code_solution[:100] if request.code_solution else 'None'}...")
        
        from backend.services.anticheat_service import anticheat_service
        from backend.services.ai_detection import ai_detection_service
        
        # Получаем вопрос для детекции AI
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            logger.error(f"[SUBMIT_ANSWER] Вопрос {question_id} не найден")
            raise HTTPException(status_code=404, detail=f"Вопрос {question_id} не найден")
        
        answer_content = request.answer_text or request.code_solution or ""
        logger.info(f"[SUBMIT_ANSWER] Длина ответа: {len(answer_content)} символов")
        
        # Детекция AI-помощников
        ai_detection = None
        if answer_content and len(answer_content) > 20:
            try:
                ai_detection = ai_detection_service.detect_ai_usage(
                    answer_content,
                    question.question_text if question else ""
                )
                logger.info(f"[SUBMIT_ANSWER] AI detection completed")
            except Exception as e:
                logger.warning(f"[SUBMIT_ANSWER] Ошибка AI detection: {e}")
        
        logger.info(f"[SUBMIT_ANSWER] Вызов interview_service.submit_answer...")
        answer = await interview_service.submit_answer(
            db=db,
            question_id=question_id,
            answer_text=request.answer_text,
            code_solution=request.code_solution,
            emotions=request.emotions,
            time_to_answer=request.time_to_answer,
            typing_metrics=request.typing_metrics,
            activity_during_answer=request.activity_during_answer
        )
        logger.info(f"[SUBMIT_ANSWER] Ответ обработан успешно, score: {answer.score}")
        
        # Сохраняем античит данные в ответ
        if request.time_to_answer:
            answer.time_to_answer = request.time_to_answer
        if request.typing_metrics:
            answer.typing_speed = request.typing_metrics.get("typingSpeed")
        if request.activity_during_answer:
            answer.activity_during_answer = request.activity_during_answer
        
        # Сохраняем результаты детекции AI в сессию
        if (ai_detection or request.typing_metrics) and question:
            from sqlalchemy.orm.attributes import flag_modified
            session = question.session
            
            if ai_detection:
                session.ai_detection_results = ai_detection
                flag_modified(session, "ai_detection_results")
            
            if request.typing_metrics:
                # Обновляем метрики печати (сохраняем последние для анализа паттернов)
                # В идеале можно было бы хранить историю, но текущая реализация античита
                # анализирует только текущие метрики
                session.typing_metrics = {
                    "average_speed": request.typing_metrics.get("typingSpeed"),
                    "variance": request.typing_metrics.get("variance"),
                    "average_interval": request.typing_metrics.get("averageInterval"),
                    "total_keystrokes": request.typing_metrics.get("totalKeystrokes")
                }
                flag_modified(session, "typing_metrics")
            
            db.commit()
        
        db.commit()
        logger.info(f"[SUBMIT_ANSWER] Ответ успешно сохранен в БД")
        
        # Формируем ответ в правильном формате
        response = {
            "id": answer.id,
            "question_id": answer.question_id,
            "answer_text": answer.answer_text,
            "code_solution": answer.code_solution,
            "score": answer.score,
            "evaluation": answer.evaluation,
            "created_at": answer.created_at.isoformat() if answer.created_at else None,
            "time_to_answer": answer.time_to_answer,
            "typing_speed": answer.typing_speed,
        }
        logger.info(f"[SUBMIT_ANSWER] Возвращаем ответ: {response}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SUBMIT_ANSWER] Ошибка при обработке ответа: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/code/execute")
async def execute_code(
    code: str,
    language: str = "python",
    input_data: str = None
):
    """Безопасное выполнение кода"""
    try:
        result = await code_executor.execute(
            code=code,
            language=language,
            input_data=input_data
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Античит endpoints
class ActivityLogRequest(BaseModel):
    type: str
    timestamp: float
    details: Optional[Dict[str, Any]] = None

@app.post("/api/sessions/{session_id}/activity")
async def log_activity(
    session_id: int,
    request: ActivityLogRequest,
    db: Session = Depends(get_db)
):
    """Логирование активности пользователя"""
    try:
        from backend.services.anticheat_service import anticheat_service
        
        result = await anticheat_service.log_activity(
            session_id=session_id,
            activity_type=request.type,
            details=request.details or {},
            db=db
        )
        
        return {
            "logged": True,
            "warning_count": result.get("warning_count", 0),
            "should_terminate": result.get("should_terminate", False),
            "warning_issued": result.get("warning_issued", False)
        }
    except Exception as e:
        logger.error(f"Error logging activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class DeviceFingerprintRequest(BaseModel):
    fingerprint: str

@app.post("/api/sessions/{session_id}/register-device")
async def register_device(
    session_id: int,
    request: DeviceFingerprintRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Регистрация устройства и проверка на множественные сессии"""
    try:
        from backend.services.anticheat_service import anticheat_service
        
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Проверяем, что пользователь имеет доступ к сессии
        if session.candidate_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Получаем IP-адрес
        ip_address = http_request.client.host if http_request.client else "unknown"
        if http_request.headers.get("x-forwarded-for"):
            ip_address = http_request.headers.get("x-forwarded-for").split(",")[0].strip()
        
        # Проверяем на другие активные сессии с другим fingerprint
        other_sessions = db.query(InterviewSession).filter(
            InterviewSession.candidate_id == session.candidate_id,
            InterviewSession.status == InterviewStatus.IN_PROGRESS,
            InterviewSession.id != session_id,
            InterviewSession.device_fingerprint.isnot(None),
            InterviewSession.device_fingerprint != request.fingerprint
        ).all()
        
        concurrent_session_ids = [s.id for s in other_sessions]
        
        # Сохраняем информацию об устройстве
        session.device_fingerprint = request.fingerprint
        session.ip_address = ip_address
        session.user_agent = "unknown"  # Можно добавить из headers если нужно
        
        if concurrent_session_ids:
            session.concurrent_sessions = concurrent_session_ids
            session.suspicion_score = min((session.suspicion_score or 0.0) + 0.2, 1.0)
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(session, "concurrent_sessions")
            flag_modified(session, "suspicion_score")
        
        db.commit()
        
        return {
            "registered": True,
            "concurrent_sessions_detected": len(concurrent_session_ids) > 0,
            "concurrent_session_ids": concurrent_session_ids
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering device: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/anticheat-analysis")
async def get_anticheat_analysis(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение анализа античита для сессии"""
    try:
        from backend.services.anticheat_service import anticheat_service
        
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Проверка прав доступа
        if current_user.role not in [Role.ADMIN, Role.HR]:
            if session.candidate_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied")
        
        analysis = await anticheat_service.analyze_session(session_id, db)
        
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting anticheat analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ChatMessageRequest(BaseModel):
    message: str
    conversation_history: Optional[List[dict]] = []
    question_context: Optional[str] = None
    interview_config: Optional[Dict[str, Any]] = None


class TrainingChatMessage(BaseModel):
    role: str
    content: str


class TrainingReportRequest(BaseModel):
    conversation_history: List[TrainingChatMessage]
    interview_config: Optional[Dict[str, Any]] = None


_TRAINING_QUESTION_MARKERS = [
    "**первый вопрос:**",
    "**следующий вопрос:**",
    "**вопрос:**",
    "**question:**",
    "**задача:**",
]


def _extract_training_question(text: str) -> Optional[str]:
    if not text:
        return None
    lowered = text.lower()
    for marker in _TRAINING_QUESTION_MARKERS:
        idx = lowered.find(marker)
        if idx != -1:
            start = idx + len(marker)
            question_part = text[start:].strip()
            # Удаляем лишние звездочки/пробелы
            question_part = question_part.lstrip("*").strip()
            # Ограничиваемся первым абзацем
            separator = "\n\n"
            if separator in question_part:
                question_part = question_part.split(separator, 1)[0].strip()
            return question_part if question_part else None
    return None


def _classify_training_stage(text: str) -> str:
    if not text:
        return "introduction"
    lower_text = text.lower()
    if "[live_coding]" in lower_text or "лайвкодинг" in lower_text or "live coding" in lower_text:
        return "liveCoding"
    
    technical_keywords = [
        "алгоритм", "сложность", "структура данных", "function", "код", "code",
        "реализуйте", "implement", "напишите", "напишите код", "write code", "data structure",
        "performance", "оптимиз", "memory", "big o", "время выполнения"
    ]
    soft_keywords = [
        "команда", "team", "конфликт", "conflict", "коммуникац", "communication",
        "лидер", "leader", "мотивац", "motivation", "soft skills", "отношения"
    ]
    introduction_keywords = [
        "расскажите", "project", "проект", "опыт", "experience", "достижен", "achievement",
        "образование", "education", "career", "карьер"
    ]
    
    if any(keyword in lower_text for keyword in technical_keywords):
        return "technical"
    if any(keyword in lower_text for keyword in soft_keywords):
        return "softSkills"
    if any(keyword in lower_text for keyword in introduction_keywords):
        return "introduction"
    
    return "introduction"


def _resolve_training_topic(config: Dict[str, Any]) -> str:
    topics = config.get("topics") or config.get("required_skills") or []
    if isinstance(topics, list) and topics:
        return str(topics[0])
    if isinstance(topics, str) and topics:
        return topics
    return "general"


def _build_training_pairs(messages: List[TrainingChatMessage]) -> List[Dict[str, Any]]:
    pairs: List[Dict[str, Any]] = []
    for msg in messages:
        role = (msg.role or "").lower()
        content = msg.content or ""
        if role == "assistant":
            question_text = _extract_training_question(content)
            if question_text:
                stage = _classify_training_stage(content)
                pairs.append({
                    "question_text": question_text,
                    "stage": stage,
                    "raw": content,
                    "answer_text": None,
                })
        elif role == "user":
            if pairs and pairs[-1]["answer_text"] is None:
                pairs[-1]["answer_text"] = content.strip()
    return [pair for pair in pairs if pair.get("answer_text")]


async def _evaluate_training_answer(
    stage: str,
    question_text: str,
    answer_text: str,
    config: Dict[str, Any],
    session_key: str
) -> Tuple[float, Dict[str, Any]]:
    """Вспомогательная функция оценки ответов для тренировочных отчетов"""
    if not answer_text or len(answer_text.strip()) < 5:
        return 0.0, {
            "score": 0,
            "correctness": 0,
            "completeness": 0,
            "quality": 0,
            "feedback": "Ответ не предоставлен или слишком короткий.",
            "strengths": [],
            "improvements": ["Предоставьте развернутый ответ на вопрос."],
        }
    
    try:
        from backend.services.agents import general_agent, technical_agent
        
        if stage in ["introduction", "softSkills"]:
            question_type = "experience" if stage == "introduction" else "team"
            result = await general_agent.process({
                "action": "evaluate_answer",
                "question": question_text,
                "answer": answer_text,
                "question_type": question_type,
                "interview_config": config,
            })
            base_score = float(result.get("evaluation", 5) or 5)
            score = base_score * 10
            evaluation_payload = {
                "score": score,
                "correctness": base_score,
                "completeness": base_score,
                "quality": base_score,
                "feedback": result.get("feedback", ""),
                "strengths": result.get("strengths", []),
                "improvements": result.get("improvements", []),
                "extracted_info": result.get("extracted_info", {}),
            }
            return score, evaluation_payload
        
        topic = _resolve_training_topic(config)
        result = await technical_agent.process({
            "action": "evaluate_answer",
            "question": question_text,
            "answer": answer_text,
            "topic": topic,
            "session_id": session_key,
        })
        score = float(result.get("score") or (result.get("evaluation", 5) * 10))
        base_eval = float(result.get("evaluation", score / 10))
        evaluation_payload = {
            "score": score,
            "correctness": base_eval,
            "completeness": result.get("completeness", base_eval),
            "quality": base_eval,
            "feedback": result.get("feedback", ""),
            "strengths": result.get("strengths", []),
            "improvements": result.get("improvements", []),
            "keywords_found": result.get("keywords_found", []),
            "keywords_missed": result.get("keywords_missed", []),
            "understanding_level": result.get("understanding_level", "intermediate"),
        }
        return score, evaluation_payload
    except Exception as e:
        logger.warning(f"Не удалось оценить тренировочный ответ: {e}")
        return 0.0, {
            "score": 0,
            "correctness": 0,
            "completeness": 0,
            "quality": 0,
            "feedback": "Не удалось автоматически оценить ответ.",
            "strengths": [],
            "improvements": ["Пожалуйста, повторите попытку позже."],
        }


@app.post("/api/training/report")
async def generate_training_report(
    request: TrainingReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Генерация отчета по тренировочному интервью на основе истории сообщений"""
    if not request.conversation_history:
        raise HTTPException(status_code=400, detail="Conversation history is empty")
    
    config = request.interview_config or {}
    
    try:
        duration_minutes = config.get("duration_minutes")
        if duration_minutes is None:
            timer_config = config.get("timer") or {}
            duration_minutes = timer_config.get("technical_minutes") or 60
        try:
            duration_minutes = int(duration_minutes)
        except (TypeError, ValueError):
            duration_minutes = 60
        
        programming_languages = (
            config.get("programming_languages")
            or config.get("programmingLanguages")
            or []
        )
        
        interview = Interview(
            title=f"Training Interview {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            description="Автоматически созданное тренировочное интервью",
            topics=config.get("topics"),
            stages=config.get("stages"),
            difficulty=config.get("difficulty", "medium"),
            duration_minutes=duration_minutes,
            position=config.get("position"),
            level=config.get("level"),
            programming_languages=programming_languages,
            hr_prompt=config.get("hrPrompt"),
            interview_config=config,
            created_by=current_user.id
        )
        db.add(interview)
        db.commit()
        db.refresh(interview)
        
        session = InterviewSession(
            interview_id=interview.id,
            candidate_id=current_user.id,
            status=InterviewStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
            current_stage="introduction"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        qa_pairs = _build_training_pairs(request.conversation_history)
        if not qa_pairs:
            raise HTTPException(status_code=400, detail="Недостаточно данных для генерации отчета")
        
        session_key = f"training_{session.id}"
        question_type_map = {
            "introduction": QuestionType.BEHAVIORAL,
            "softSkills": QuestionType.BEHAVIORAL,
            "technical": QuestionType.THEORY,
            "liveCoding": QuestionType.CODING,
        }
        
        for idx, pair in enumerate(qa_pairs, start=1):
            stage = pair.get("stage", "technical")
            question_type = question_type_map.get(stage, QuestionType.THEORY)
            question = Question(
                session_id=session.id,
                question_text=pair["question_text"],
                question_type=question_type,
                topic=stage,
                difficulty=interview.difficulty,
                expected_keywords=[],
                order=idx,
                shown_at=session.started_at
            )
            db.add(question)
            db.flush()
            
            score_value, evaluation_payload = await _evaluate_training_answer(
                stage=stage,
                question_text=pair["question_text"],
                answer_text=pair["answer_text"],
                config=config,
                session_key=session_key
            )
            
            answer = Answer(
                question_id=question.id,
                answer_text=pair["answer_text"],
                score=score_value,
                evaluation=evaluation_payload
            )
            db.add(answer)
        
        db.commit()
        
        answers = db.query(Answer).join(Question).filter(
            Question.session_id == session.id
        ).all()
        scores = [ans.score for ans in answers if ans.score is not None]
        session.total_score = sum(scores) / len(scores) if scores else 0.0
        session.status = InterviewStatus.COMPLETED
        session.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(session)
        
        from backend.services.report_service import report_service
        from backend.services.agents.report_agent import report_agent
        
        interview_data = report_service.export_session_to_json(db, session.id)
        evaluation_result = await report_agent.evaluate_candidate(
            interview_data=interview_data,
            interview_config=config
        )
        session.ai_evaluation = evaluation_result
        db.commit()
        
        pdf_path = None
        try:
            pdf_path = report_service.generate_pdf_report(db, session.id, force_regenerate=True)
        except ImportError:
            logger.warning("reportlab не установлен, PDF отчет не сгенерирован")
        except Exception as e:
            logger.warning(f"Не удалось сгенерировать PDF отчет для тренировки: {e}")
        
        return {
            "message": "Training report generated",
            "session_id": session.id,
            "report_path": pdf_path,
            "total_score": session.total_score,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка генерации тренировочного отчета: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/message")
async def chat_message(
    request: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Отправка сообщения в чат с AI-интервьюером"""
    import re
    from backend.services.mock_responses import detect_injection
    
    try:
        message_lower = request.message.lower().strip()
        
        def resolve_topic(config: Dict[str, Any]) -> str:
            topics = config.get("topics") or config.get("required_skills") or []
            if isinstance(topics, list) and topics:
                return str(topics[0])
            if isinstance(topics, str) and topics:
                return topics
            return "algorithms"
        
        def resolve_language(config: Dict[str, Any]) -> str:
            languages = (
                config.get("programming_languages")
                or config.get("programmingLanguages")
                or ["python"]
            )
            if isinstance(languages, list) and languages:
                return str(languages[0])
            if isinstance(languages, str) and languages:
                return languages
            return "python"
        
        def format_live_coding_question(task_data: Dict[str, Any], config: Dict[str, Any]) -> str:
            import json as json_module

            def parse_json_like(payload: Any) -> Optional[Any]:
                if not isinstance(payload, str):
                    return None
                cleaned = re.sub(r'<think>.*?</think>', '', payload, flags=re.DOTALL).strip()
                code_match = re.search(r'```json\s*(.*?)\s*```', cleaned, re.DOTALL)
                if code_match:
                    cleaned = code_match.group(1).strip()
                if not cleaned:
                    return None
                if not cleaned.lstrip().startswith(("{", "[")):
                    return None
                variants = [cleaned]
                normalized_quotes = cleaned.replace("“", '"').replace("”", '"')
                if normalized_quotes != cleaned:
                    variants.append(normalized_quotes)
                for variant in variants:
                    try:
                        return json_module.loads(variant, strict=False)
                    except json_module.JSONDecodeError:
                        continue
                return None

            def ensure_task_dict(payload: Any) -> Dict[str, Any]:
                if isinstance(payload, dict):
                    return payload
                parsed = parse_json_like(str(payload))
                if isinstance(parsed, dict):
                    return parsed
                return {"question": str(payload).strip()}

            task_payload = ensure_task_dict(task_data)

            question_text: Any = task_payload.get("question") or task_payload.get("task") or ""
            embedded_tests: Optional[List[Dict[str, Any]]] = None
            if isinstance(question_text, (dict, list)):
                question_text = json_module.dumps(question_text, ensure_ascii=False, indent=2)
            elif isinstance(question_text, str):
                potential_payload = parse_json_like(question_text)
                if isinstance(potential_payload, dict) and potential_payload.get("question"):
                    question_text = potential_payload.get("question", "").strip()
                    embedded_tests = potential_payload.get("test_cases") or potential_payload.get("tests")
                question_text = re.sub(r'<think>.*?</think>', '', question_text, flags=re.DOTALL)
                question_text = question_text.replace("\\n", "\n").strip()

            test_cases: Any = (
                task_payload.get("test_cases")
                or task_payload.get("tests")
                or embedded_tests
                or []
            )
            if isinstance(test_cases, str):
                parsed_cases = parse_json_like(test_cases)
                if isinstance(parsed_cases, list):
                    test_cases = parsed_cases
                else:
                    test_cases = []

            tests_block = ""
            if isinstance(test_cases, list) and test_cases:
                formatted_cases = []
                for idx, case in enumerate(test_cases, start=1):
                    input_data = case.get("input") or case.get("input_data") or case.get("input_example") or ""
                    expected = case.get("expected_output") or case.get("output") or case.get("expected") or ""
                    description = case.get("description")
                    entry = f"{idx}. Input: {input_data} -> Output: {expected}"
                    if description:
                        entry += f" ({description})"
                    formatted_cases.append(entry.strip())
                tests_block = "\n\nТестовые случаи:\n" + "\n".join(formatted_cases)

            language_hint = task_payload.get("language") or resolve_language(config)
            prefix = f"[LIVE_CODING]\nЯзык по умолчанию: {language_hint}\n\n"
            return f"{prefix}**Задача лайвкодинга:**\n{question_text}{tests_block}".strip()
        
        # === ПРОВЕРКА НА PROMPT INJECTION ===
        if detect_injection(request.message):
            # Попытка манипуляции - отказываем
            return {
                "response": "Пожалуйста, отвечайте на вопрос по существу. Интервьюер не отвечает на вопросы кандидата и не дает подсказок.",
                "role": "assistant"
            }
        
        # === ПОДСЧЕТ ЗАДАННЫХ ВОПРОСОВ И ОПРЕДЕЛЕНИЕ ТЕКУЩЕГО ЭТАПА ===
        from backend.services.interview_stage_manager import InterviewStageManager
        
        STAGE_ORDER = ["introduction", "softSkills", "technical", "liveCoding"]
        config = request.interview_config or {}
        
        def is_question_message(content: str) -> bool:
            if not content:
                return False
            lowered = content.lower()
            base_markers = ["**первый вопрос:**", "**следующий вопрос:**"]
            live_markers = ["**задача лайвкодинга:**", "live coding task", "[live_coding]"]
            return any(marker in lowered for marker in base_markers) or any(marker in lowered for marker in live_markers)
        
        def compute_stage_requirements(cfg: Dict[str, Any]) -> Dict[str, int]:
            stage_progress_template = InterviewStageManager.initialize_stage_progress(cfg or {})
            requirements: Dict[str, int] = {}
            for stage in STAGE_ORDER:
                stage_info = stage_progress_template.get(stage, {})
                requirements[stage] = stage_info.get("questions_required", 0) or 0
            return requirements
        
        def build_stage_progress(
            history: List[Dict[str, Any]],
            requirements: Dict[str, int],
            stage_sequence: List[str]
        ) -> Tuple[Dict[str, int], int]:
            counts = {stage: 0 for stage in STAGE_ORDER}
            total_questions = 0
            
            active_sequence = [stage for stage in stage_sequence if requirements.get(stage, 0) > 0]
            if not active_sequence:
                active_sequence = [stage for stage in STAGE_ORDER if requirements.get(stage, 0) > 0]
            if not active_sequence:
                active_sequence = ["technical"]
            
            def advance(index: int) -> int:
                while index < len(active_sequence) and requirements.get(active_sequence[index], 0) == 0:
                    index += 1
                return index
            
            stage_index = advance(0)
            
            for msg in history or []:
                if msg.get("role") != "assistant":
                    continue
                content = msg.get("content", "")
                if not is_question_message(content):
                    continue
                total_questions += 1
                current_idx = min(stage_index, len(active_sequence) - 1)
                stage_key = active_sequence[current_idx]
                counts[stage_key] += 1
                
                required = requirements.get(stage_key, 0)
                if required and counts[stage_key] >= required and stage_index < len(active_sequence) - 1:
                    stage_index = advance(stage_index + 1)
            
            return counts, total_questions
        
        def get_current_stage(
            requirements: Dict[str, int],
            questions_by_stage: Dict[str, int]
        ) -> str:
            stage_order = [stage for stage in STAGE_ORDER if requirements.get(stage, 0) > 0]
            if not stage_order:
                stage_order = STAGE_ORDER
            
            for stage in stage_order:
                required = requirements.get(stage, 0)
                if required == 0:
                    continue
                if questions_by_stage.get(stage, 0) < required:
                    return stage
            
            return stage_order[-1] if stage_order else "introduction"
        
        stage_requirements = compute_stage_requirements(config)
        stage_sequence = InterviewStageManager.get_stage_sequence(config)
        questions_by_stage, questions_asked = build_stage_progress(
            request.conversation_history or [],
            stage_requirements,
            stage_sequence
        )
        
        if request.question_context and questions_asked == 0:
            inferred_stage = get_current_stage(stage_requirements, questions_by_stage)
            questions_by_stage[inferred_stage] += 1
            questions_asked = 1
        
        current_stage = get_current_stage(stage_requirements, questions_by_stage)
        
        # Получаем общий лимит вопросов (сумма всех этапов)
        questions_per_stage = config.get("questions_per_stage", {}) or config.get("questionsPerStage", {})
        questions_limit = None
        if questions_per_stage:
            total = 0
            for stage_count in questions_per_stage.values():
                if isinstance(stage_count, int):
                    total += stage_count
                elif isinstance(stage_count, list):
                    total += len(stage_count)
            questions_limit = total if total > 0 else None
        
        # === ПРОВЕРКА НА ПРОПУСК / "НЕ ЗНАЮ" ===
        # Эта проверка должна быть ДО проверки на запросы помощи
        # Проверяем пропуск независимо от наличия question_context
        # Если есть контекст вопроса ИЛИ в истории есть вопросы - значит это ответ на вопрос
        has_question_context = bool(request.question_context)
        has_questions_in_history = questions_asked > 0
        
        if has_question_context or has_questions_in_history:
            skip_keywords = [
                "не знаю", "незнаю", "не знаю ответа", "не знаю ответ", "не знаю на данный вопрос",
                "не знаю на этот вопрос", "не знаю на вопрос", "не могу ответить", "не помню", 
                "забыл", "дальше", "далее", "следующий", "следующий вопрос", "пропустить", 
                "скип", "skip", "next", "pass", "idk", "dunno", "без понятия", 
                "затрудняюсь ответить", "no answer", "хз"
            ]
            
            message_normalized = message_lower.strip().rstrip(".,!?")
            is_skip_answer = (
                any(kw in message_normalized for kw in skip_keywords) or
                message_normalized in skip_keywords or
                any(message_normalized.startswith(kw) for kw in skip_keywords) or
                any(message_normalized.endswith(kw) for kw in skip_keywords)
            )
            
            if is_skip_answer:
                # При пропуске учитываем текущий вопрос (он уже задан, поэтому questions_asked уже включает его)
                # Проверяем лимит вопросов: если уже задано >= лимита, не генерируем следующий
                if questions_limit is not None and questions_asked >= questions_limit:
                    return {
                        "response": "Вы ответили на все запланированные вопросы. Тренировка завершена.",
                        "role": "assistant",
                        "score": 0,
                        "training_completed": True,
                        "question_answered": True,
                        "is_skip": True,
                        "questions_asked": questions_asked  # Итоговое количество
                    }
                
                # Ставим 0 баллов и генерируем следующий вопрос на основе текущего этапа
                from backend.services.agents import technical_agent, general_agent
                import json as json_module
                
                score = 0
                next_difficulty = 5  # Сохраняем текущую сложность
                
                # Генерируем вопрос на основе текущего этапа (current_stage уже определен выше)
                if current_stage in ["introduction", "softSkills"]:
                    # Генерируем вопрос знакомства/софт-скиллов
                    question_type = "experience" if current_stage == "introduction" else "team"
                    next_question_data = await general_agent.process({
                        "action": "generate_question",
                        "question_type": question_type,
                        "context": {},
                        "interview_config": config,
                        "hr_prompt": config.get("hrPrompt", ""),
                    })
                    next_question = next_question_data.get("question", "")
                else:
                    topic = resolve_topic(config)
                    if current_stage == "liveCoding":
                        from backend.services.agents import coding_agent
                        next_question_data = await coding_agent.process({
                            "action": "generate_task",
                            "topic": topic,
                            "difficulty": config.get("difficulty", "medium"),
                            "interview_config": config,
                            "hr_prompt": config.get("hrPrompt", ""),
                        })
                        next_question = format_live_coding_question(next_question_data, config)
                    else:
                        next_question_data = await technical_agent.process({
                            "action": "generate_question",
                            "topic": topic,
                            "difficulty": next_difficulty,
                            "interview_config": config,
                            "session_id": "chat_session"
                        })
                        next_question = next_question_data.get("question", "")
                
                if current_stage != "liveCoding":
                    next_question = next_question_data.get("question", "") if current_stage in ["introduction", "softSkills"] else next_question
                    if next_question:
                        next_question = re.sub(r'<think>.*?</think>', '', next_question, flags=re.DOTALL)
                        if '```json' in next_question or '"question"' in next_question:
                            json_match = re.search(r'```json\s*(.*?)\s*```', next_question, re.DOTALL)
                            if json_match:
                                try:
                                    parsed = json_module.loads(json_match.group(1))
                                    next_question = parsed.get("question", next_question)
                                except:
                                    pass
                            else:
                                json_match = re.search(r'\{[^{}]*"question"\s*:\s*"([^"]+)"[^{}]*\}', next_question)
                                if json_match:
                                    next_question = json_match.group(1)
                        next_question = next_question.strip()
                        next_question = re.sub(r'\n\s*\n\s*\n', '\n\n', next_question)
                
                # Формируем ответ - просто переходим к следующему вопросу
                if next_question:
                    response_text = f"Переходим к следующему вопросу.\n\n**Следующий вопрос:**\n{next_question}"
                else:
                    response_text = "Переходим к следующему вопросу."
                
                return {
                    "response": response_text,
                    "role": "assistant",
                    "score": 0,
                    "next_difficulty": next_difficulty,
                    "question_answered": True,  # Вопрос был отвечен (пропущен), счетчик увеличен
                    "is_skip": True,  # Маркер пропуска
                    "questions_asked": questions_asked + 1  # Явно указываем количество заданных вопросов после пропуска
                }
        
        # === ПРОВЕРКА НА ЗАПРОСЫ ПОМОЩИ ===
        help_keywords = [
            "ответь", "ответить", "скажи ответ", "подскажи", "помоги",
            "объясни", "расскажи", "покажи решение", "дай ответ",
            "answer", "help me", "tell me", "explain", "give me",
            "как ответить", "что ответить"
        ]
        if any(kw in message_lower for kw in help_keywords):
            return {
                "response": "Я интервьюер и не могу давать ответы или подсказки. Пожалуйста, дайте свой ответ на вопрос. Если не знаете ответ, можете сказать 'не знаю' и мы перейдем к следующему вопросу.",
                "role": "assistant"
            }
        
        # === ПРОВЕРКА НА ГОТОВНОСТЬ (начало интервью) ===
        ready_keywords = ["готов", "ready", "да", "yes", "начнем", "start", "поехали", "давай", "го", "go", "ок", "ok", "начинаем", "begin"]
        is_ready_response = any(kw in message_lower for kw in ready_keywords) and len(message_lower) < 50
        
        if is_ready_response:
            # Проверяем лимит вопросов (если уже заданы все вопросы, не начинаем)
            if questions_limit is not None and questions_asked >= questions_limit:
                return {
                    "response": "Вы уже ответили на все запланированные вопросы. Тренировка завершена.",
                    "role": "assistant",
                    "training_completed": True
                }
            # Кандидат готов - генерируем первый вопрос на основе текущего этапа
            from backend.services.agents import technical_agent, general_agent
            import json as json_module
            
            # Текущий этап уже определен выше (current_stage)
            # Выбираем агента в зависимости от текущего этапа
            if current_stage in ["introduction", "softSkills"]:
                # Для знакомства и софт-скиллов используем general_agent
                question_type = "experience" if current_stage == "introduction" else "team"
                question_data = await general_agent.process({
                    "action": "generate_question",
                    "question_type": question_type,
                    "context": {},
                    "interview_config": config,
                    "hr_prompt": config.get("hrPrompt", ""),
                })
                question_text = question_data.get("question", "")
            elif current_stage == "liveCoding":
                from backend.services.agents import coding_agent
                topic = resolve_topic(config)
                question_data = await coding_agent.process({
                    "action": "generate_task",
                    "topic": topic,
                    "difficulty": config.get("difficulty", "medium"),
                    "interview_config": config,
                    "hr_prompt": config.get("hrPrompt", ""),
                })
                question_text = format_live_coding_question(question_data, config)
            else:
                # Для технических вопросов используем technical_agent
                topic = "python"
                difficulty = 5
                if config:
                    topics = config.get('topics', [])
                    if topics:
                        topic = topics[0]
                    level = config.get('level', 'middle')
                    if level == 'junior':
                        difficulty = 3
                    elif level == 'senior':
                        difficulty = 7
                
                question_data = await technical_agent.process({
                    "action": "generate_question",
                    "topic": topic,
                    "difficulty": difficulty,
                    "interview_config": config,
                    "session_id": "chat_session"
                })
                question_text = question_data.get("question", "")
            
            # Очистка от <think> блоков и JSON формата
            if question_text and current_stage != "liveCoding":
                # Удаляем блоки <think>...</think>
                question_text = re.sub(r'<think>.*?</think>', '', question_text, flags=re.DOTALL)
                # Пытаемся извлечь вопрос из JSON если он там
                if '```json' in question_text or '"question"' in question_text:
                    # Извлекаем JSON
                    json_match = re.search(r'```json\s*(.*?)\s*```', question_text, re.DOTALL)
                    if json_match:
                        try:
                            parsed = json_module.loads(json_match.group(1))
                            question_text = parsed.get("question", question_text)
                        except:
                            pass
                    else:
                        # Попробуем найти JSON без markdown
                        json_match = re.search(r'\{[^{}]*"question"\s*:\s*"([^"]+)"[^{}]*\}', question_text)
                        if json_match:
                            question_text = json_match.group(1)
                # Убираем лишние пробелы и переносы
                question_text = question_text.strip()
                question_text = re.sub(r'\n\s*\n\s*\n', '\n\n', question_text)
                
                return {
                    "response": f"Отлично! Начинаем собеседование.\n\n**Первый вопрос:**\n{question_text}",
                    "role": "assistant",
                    "question_generated": True
                }
            elif question_text:
                return {
                    "response": f"Отлично! Переходим к лайвкодингу.\n\n{question_text}",
                    "role": "assistant",
                    "question_generated": True
                }
        
        # === ОБЫЧНЫЙ ОТВЕТ КАНДИДАТА - ОЦЕНИВАЕМ И ГЕНЕРИРУЕМ СЛЕДУЮЩИЙ ВОПРОС ===
        # Если есть контекст вопроса, значит кандидат отвечает на него
        # Проверка на skip уже выполнена выше, поэтому здесь обрабатываем только нормальные ответы
        if request.question_context and len(request.message) > 5:
            from backend.services.agents import technical_agent, general_agent
            import json as json_module
            
            # Используем текущий этап для выбора агента (current_stage уже определен выше)
            if current_stage in ["introduction", "softSkills"]:
                # Вопрос знакомства/софт-скиллов - используем general_agent
                eval_result = await general_agent.process({
                    "action": "evaluate_answer",
                    "question": request.question_context,
                    "answer": request.message,
                    "interview_config": config,
                })
                
                score = eval_result.get("evaluation", 5)
                next_difficulty = 5  # Для общих вопросов сложность не меняется
                
                # Генерируем следующий вопрос на основе текущего этапа
                question_type = "experience" if current_stage == "introduction" else "team"
                next_question_data = await general_agent.process({
                    "action": "generate_question",
                    "question_type": question_type,
                    "context": {},
                    "interview_config": config,
                    "hr_prompt": config.get("hrPrompt", ""),
                })
            else:
                if current_stage == "liveCoding":
                    language_hint = resolve_language(config)
                    return {
                        "response": (
                            "Для задач лайвкодинга используйте редактор кода справа: "
                            "напишите решение, нажмите «Отправить», а затем сообщите, когда будете готовы продолжить.\n"
                            f"Подсказка: базовый язык — {language_hint}."
                        ),
                        "role": "assistant",
                        "score": None,
                        "question_answered": False,
                        "questions_asked": questions_asked
                    }
                # Технический вопрос - используем technical_agent
                eval_result = await technical_agent.process({
                    "action": "evaluate_answer",
                    "question": request.question_context,
                    "answer": request.message,
                    "topic": "python",
                    "session_id": "chat_session"
                })
                
                score = eval_result.get("evaluation", 5)
                next_difficulty = eval_result.get("next_difficulty", 5)
                
                # Генерируем следующий технический вопрос
                topic = "python"
                if config:
                    topics = config.get('topics', [])
                    if topics:
                        topic = topics[0]
                
                next_question_data = await technical_agent.process({
                    "action": "generate_question",
                    "topic": topic,
                    "difficulty": next_difficulty,
                    "interview_config": config,
                    "session_id": "chat_session"
                })
            
            next_question = next_question_data.get("question", "")
            
            # Очистка от <think> блоков и JSON формата
            if next_question:
                next_question = re.sub(r'<think>.*?</think>', '', next_question, flags=re.DOTALL)
                if '```json' in next_question or '"question"' in next_question:
                    json_match = re.search(r'```json\s*(.*?)\s*```', next_question, re.DOTALL)
                    if json_match:
                        try:
                            parsed = json_module.loads(json_match.group(1))
                            next_question = parsed.get("question", next_question)
                        except:
                            pass
                    else:
                        json_match = re.search(r'\{[^{}]*"question"\s*:\s*"([^"]+)"[^{}]*\}', next_question)
                        if json_match:
                            next_question = json_match.group(1)
                next_question = next_question.strip()
                next_question = re.sub(r'\n\s*\n\s*\n', '\n\n', next_question)
            
            # Формируем ответ
            if score >= 7:
                feedback = "Хороший ответ."
            elif score >= 5:
                feedback = "Ответ засчитан."
            else:
                feedback = "Ответ принят."
            
            if next_question:
                response_text = f"{feedback} Переходим к следующему вопросу.\n\n**Следующий вопрос:**\n{next_question}"
            else:
                response_text = f"{feedback}"
            
            return {
                "response": response_text,
                "role": "assistant",
                "score": score * 10,
                "next_difficulty": next_difficulty,
                "question_answered": True,  # Вопрос был отвечен
                "questions_asked": questions_asked + 1  # Явно указываем количество заданных вопросов
            }
        
        # === FALLBACK: Общий ответ интервьюера ===
        # Используем строгий промпт для интервьюера
        # ВАЖНО: Проверка на пропуск уже выполнена выше, но на всякий случай проверяем еще раз
        # Если в истории есть вопросы и сообщение содержит ключевые слова пропуска - обрабатываем как пропуск
        if questions_asked > 0:
            skip_keywords_fallback = [
                "не знаю", "незнаю", "не знаю ответа", "пропустить", "скип", "skip", 
                "next", "pass", "idk", "дальше", "далее", "хз"
            ]
            message_normalized_fallback = message_lower.strip().rstrip(".,!?")
            is_skip_fallback = any(kw in message_normalized_fallback for kw in skip_keywords_fallback)
            
            if is_skip_fallback:
                # Обрабатываем как пропуск
                if questions_limit is not None and questions_asked >= questions_limit:
                    return {
                        "response": "Вы ответили на все запланированные вопросы. Тренировка завершена.",
                        "role": "assistant",
                        "score": 0,
                        "training_completed": True,
                        "question_answered": True,
                        "is_skip": True,
                        "questions_asked": questions_asked
                    }
                
                # Генерируем следующий вопрос
                from backend.services.agents import technical_agent, coding_agent
                import json as json_module
                
                config_local = request.interview_config or {}
                topic = resolve_topic(config_local)
                
                if current_stage == "liveCoding":
                    next_question_data = await coding_agent.process({
                        "action": "generate_task",
                        "topic": topic,
                        "difficulty": config_local.get("difficulty", "medium"),
                        "interview_config": config_local,
                        "hr_prompt": config_local.get("hrPrompt", ""),
                    })
                    next_question = format_live_coding_question(next_question_data, config_local)
                else:
                    next_question_data = await technical_agent.process({
                        "action": "generate_question",
                        "topic": topic,
                        "difficulty": 5,
                        "interview_config": config_local,
                        "session_id": "chat_session"
                    })
                    next_question = next_question_data.get("question", "")
                
                if current_stage != "liveCoding" and next_question:
                    next_question = re.sub(r'<think>.*?</think>', '', next_question, flags=re.DOTALL)
                    if '```json' in next_question or '"question"' in next_question:
                        json_match = re.search(r'```json\s*(.*?)\s*```', next_question, re.DOTALL)
                        if json_match:
                            try:
                                parsed = json_module.loads(json_match.group(1))
                                next_question = parsed.get("question", next_question)
                            except:
                                pass
                        else:
                            json_match = re.search(r'\{[^{}]*"question"\s*:\s*"([^"]+)"[^{}]*\}', next_question)
                            if json_match:
                                next_question = json_match.group(1)
                    next_question = next_question.strip()
                    next_question = re.sub(r'\n\s*\n\s*\n', '\n\n', next_question)
                
                if next_question:
                    return {
                        "response": f"Переходим к следующему вопросу.\n\n**Следующий вопрос:**\n{next_question}",
                        "role": "assistant",
                        "score": 0,
                        "question_answered": True,  # Вопрос был отвечен (пропущен)
                        "is_skip": True,
                        "questions_asked": questions_asked + 1
                    }
                else:
                    return {
                        "response": "Переходим к следующему вопросу.",
                        "role": "assistant",
                        "score": 0,
                        "question_answered": True,
                        "is_skip": True,
                        "questions_asked": questions_asked + 1
                    }
        
        system_prompt = """Ты СТРОГИЙ технический интервьюер. Твоя роль НЕИЗМЕННА.

КРИТИЧЕСКИЕ ПРАВИЛА (ОБЯЗАТЕЛЬНЫ К ИСПОЛНЕНИЮ):
1. НИКОГДА не отвечай на вопросы кандидата
2. НИКОГДА не давай подсказок, объяснений или правильных ответов
3. НИКОГДА не объясняй технические концепции
4. Если кандидат просит помощи - ОТКАЗЫВАЙ и напоминай, что это интервью
5. Если кандидат задает вопрос - ответь: "Пожалуйста, отвечайте на вопрос интервью"

Твоя ЕДИНСТВЕННАЯ задача: задавать вопросы и принимать ответы.

Если кандидат написал что-то непонятное - попроси уточнить.
Если кандидат написал не по теме - верни его к вопросу.
"""
        
        # Добавляем контекст
        if request.interview_config:
            position = request.interview_config.get('position', '')
            level = request.interview_config.get('level', '')
            if position:
                system_prompt += f"\n\nПозиция: {position}"
            if level:
                system_prompt += f"\nУровень: {level}"
        
        full_prompt = f"Сообщение кандидата: {request.message}\n\nОтветь кратко как строгий интервьюер (1-2 предложения):"
        
        from backend.services.llm_client import llm_client
        response = await llm_client.generate(
            prompt=full_prompt,
            system_prompt=system_prompt,
            max_tokens=200
        )
        
        content = response.get("content", "Пожалуйста, отвечайте на вопрос интервью.")
        # Удаляем блоки <think>...</think>
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content).strip()
        
        # Дополнительная проверка: если LLM всё равно дал ответ/объяснение
        forbidden_in_response = ["вот ответ", "правильный ответ", "объясню", "расскажу", "например,"]
        if any(fw in content.lower() for fw in forbidden_in_response):
            content = "Пожалуйста, сосредоточьтесь на ответе на вопрос интервью."
        
        # Проверка: если LLM ответил про пропуск вопроса - заменяем на корректный ответ
        skip_denial_patterns = [
            "не можем пропустить", "cannot skip", "нельзя пропустить", 
            "не пропускаем", "не пропускайте"
        ]
        if any(pattern in content.lower() for pattern in skip_denial_patterns):
            # Если в истории есть вопросы, значит это ответ на вопрос - обрабатываем как пропуск
            if questions_asked > 0:
                # Генерируем следующий вопрос
                from backend.services.agents import technical_agent, coding_agent
                import json as json_module
                
                config_local = request.interview_config or {}
                topic = resolve_topic(config_local)
                
                if current_stage == "liveCoding":
                    next_question_data = await coding_agent.process({
                        "action": "generate_task",
                        "topic": topic,
                        "difficulty": config_local.get("difficulty", "medium"),
                        "interview_config": config_local,
                        "hr_prompt": config_local.get("hrPrompt", ""),
                    })
                    next_question = format_live_coding_question(next_question_data, config_local)
                else:
                    next_question_data = await technical_agent.process({
                        "action": "generate_question",
                        "topic": topic,
                        "difficulty": 5,
                        "interview_config": config_local,
                        "session_id": "chat_session"
                    })
                    next_question = next_question_data.get("question", "")
                
                if current_stage != "liveCoding" and next_question:
                    next_question = re.sub(r'<think>.*?</think>', '', next_question, flags=re.DOTALL)
                    if '```json' in next_question or '"question"' in next_question:
                        json_match = re.search(r'```json\s*(.*?)\s*```', next_question, re.DOTALL)
                        if json_match:
                            try:
                                parsed = json_module.loads(json_match.group(1))
                                next_question = parsed.get("question", next_question)
                            except:
                                pass
                        else:
                            json_match = re.search(r'\{[^{}]*"question"\s*:\s*"([^"]+)"[^{}]*\}', next_question)
                            if json_match:
                                next_question = json_match.group(1)
                    next_question = next_question.strip()
                    next_question = re.sub(r'\n\s*\n\s*\n', '\n\n', next_question)
                
                if next_question:
                    content = f"Переходим к следующему вопросу.\n\n**Следующий вопрос:**\n{next_question}"
                else:
                    content = "Переходим к следующему вопросу."
        
        return {
            "response": content,
            "role": "assistant"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.post("/api/candidates/{user_id}/profile/update")
async def update_candidate_profile(
    user_id: int,
    github_username: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновление профиля кандидата с данными из внешних источников"""
    try:
        from backend.services.candidate_profiler import candidate_profiler
        
        # Проверка прав доступа
        if current_user.id != user_id and current_user.role not in [Role.ADMIN, Role.HR]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        user = await candidate_profiler.update_candidate_profile(
            db=db,
            user_id=user_id,
            github_username=github_username,
            linkedin_url=linkedin_url
        )
        
        return {
            "message": "Profile updated successfully",
            "user_id": user.id,
            "skills": user.skills,
            "skill_matrix": user.skill_matrix
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/candidates/{user_id}/soft-skills")
async def get_soft_skills_analysis(
    user_id: int,
    session_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение анализа soft skills кандидата"""
    try:
        from backend.services.soft_skills_analyzer import soft_skills_analyzer
        
        # Проверка прав доступа
        if current_user.id != user_id and current_user.role not in [Role.ADMIN, Role.HR]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        if session_id:
            analysis = await soft_skills_analyzer.analyze_session(db, session_id)
        else:
            # Анализ всех сессий кандидата
            from backend.models.interview import InterviewSession
            sessions = db.query(InterviewSession).filter(
                InterviewSession.candidate_id == user_id,
                InterviewSession.status == InterviewStatus.COMPLETED
            ).all()
            
            if not sessions:
                raise HTTPException(status_code=404, detail="No completed sessions found")
            
            # Анализируем последнюю сессию
            latest_session = max(sessions, key=lambda s: s.completed_at or s.created_at)
            analysis = await soft_skills_analyzer.analyze_session(db, latest_session.id)
        
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/explanation")
async def get_evaluation_explanation(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение объяснения оценки сессии (Explainable AI) с проверкой прав доступа"""
    try:
        # Проверяем права доступа к сессии
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        has_access = False
        if current_user.role == Role.ADMIN:
            has_access = True
        elif current_user.role == Role.HR:
            interview = session.interview
            if interview and interview.created_by == current_user.id:
                has_access = True
            else:
                invitation = db.query(InterviewInvitation).filter(
                    InterviewInvitation.interview_id == session.interview_id,
                    InterviewInvitation.hr_id == current_user.id
                ).first()
                if invitation:
                    has_access = True
        else:
            if session.candidate_id == current_user.id:
                has_access = True
        
        if not has_access:
            raise HTTPException(status_code=403, detail="Not enough permissions to access this session")
        
        from backend.services.explainability_engine import explainability_engine
        
        explanation = explainability_engine.explain_session_score(db, session_id)
        
        return explanation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/candidates/{user_id}/prediction")
async def get_success_prediction(
    user_id: int,
    job_requirements: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение прогноза успешности кандидата"""
    try:
        from backend.services.prediction_engine import prediction_engine
        
        # Проверка прав доступа
        if current_user.id != user_id and current_user.role not in [Role.ADMIN, Role.HR]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        prediction = await prediction_engine.predict_success(
            db=db,
            user_id=user_id,
            job_requirements=job_requirements
        )
        
        return prediction
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/candidates/{user_id}/profile")
async def get_candidate_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение расширенного профиля кандидата"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Проверка прав доступа
        if current_user.id != user_id and current_user.role not in [Role.ADMIN, Role.HR]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "github_username": user.github_username,
            "linkedin_url": user.linkedin_url,
            "skills": user.skills,
            "skill_matrix": user.skill_matrix,
            "soft_skills_score": user.soft_skills_score,
            "success_prediction": user.success_prediction,
            "external_profiles": user.external_profiles,
            "role_type": user.role_type.value if user.role_type else None,
            "experience_level": user.experience_level.value if user.experience_level else None,
            "programming_languages": user.programming_languages,
            # v3.0.0: Данные из HH.ru
            "work_experience": user.work_experience,
            "education": user.education,
            "hh_metrics": user.hh_metrics,
            "hh_resume_id": user.hh_resume_id,
            "hh_profile_synced_at": user.hh_profile_synced_at.isoformat() if user.hh_profile_synced_at else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HR Search & Filter v2.0.0 ====================

@app.get("/api/hr/candidates/search")
async def search_candidates(
    search: Optional[str] = None,
    programming_languages: Optional[str] = None,  # Comma-separated: "Python,JavaScript"
    role_type: Optional[str] = None,  # fullstack, backend, frontend, etc.
    experience_level: Optional[str] = None,  # junior, middle, senior, lead
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Поиск и фильтрация кандидатов для HR"""
    try:
        # Проверка прав доступа
        if current_user.role not in [Role.ADMIN, Role.HR]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        logger.info(f"[HR_SEARCH] Request params: search='{search}', programming_languages={programming_languages}, role_type={role_type}, experience_level={experience_level}")
        logger.info(f"[HR_SEARCH] Search type: {type(search)}, value: {repr(search)}")
        
        # Базовый запрос - только кандидаты
        # Не фильтруем по is_active, чтобы показать всех кандидатов
        query = db.query(User).filter(User.role == Role.CANDIDATE)
        
        # Логируем количество кандидатов до фильтров
        total_before_filters = query.count()
        logger.info(f"Total candidates before filters: {total_before_filters}")
        
        # Поиск по нику, имени, email
        if search:
            search_trimmed = search.strip()
            if search_trimmed:
                from sqlalchemy import func, or_
                
                logger.info(f"[SEARCH] Starting search with term: '{search_trimmed}'")
                
                # Простой и надежный поиск: используем LIKE для частичного совпадения
                # SQLite LIKE регистронезависимый для ASCII символов
                search_pattern = f"%{search_trimmed}%"
                
                # Поиск по username (основной приоритет)
                username_condition = func.lower(User.username).like(func.lower(search_pattern))
                
                # Поиск по full_name и email (дополнительно)
                full_name_condition = func.lower(func.coalesce(User.full_name, '')).like(func.lower(search_pattern))
                email_condition = func.lower(func.coalesce(User.email, '')).like(func.lower(search_pattern))
                
                # Объединяем условия через OR
                search_conditions = or_(
                    username_condition,
                    full_name_condition,
                    email_condition
                )
                
                # Применяем фильтр
                query = query.filter(search_conditions)
                
                logger.info(f"[SEARCH] Applied search filter with pattern: '{search_pattern}'")
                
                # Проверяем результат сразу после применения фильтра
                test_count = query.count()
                logger.info(f"[SEARCH] Candidates found: {test_count}")
                
                if test_count > 0:
                    # Логируем найденных кандидатов
                    test_candidates = query.limit(5).all()
                    for cand in test_candidates:
                        logger.info(f"[SEARCH] ✓ Found: id={cand.id}, username='{cand.username}', email='{cand.email or 'N/A'}'")
                else:
                    logger.warning(f"[SEARCH] ✗ No candidates found for: '{search_trimmed}'")
                    
                    # Дополнительная диагностика: проверяем всех кандидатов
                    all_candidates = db.query(User).filter(User.role == Role.CANDIDATE).limit(10).all()
                    logger.info(f"[SEARCH] Sample of all candidates (first 10):")
                    for u in all_candidates:
                        logger.info(f"[SEARCH]   - id={u.id}, username='{u.username}'")
                    
                    # Проверяем точное совпадение username (без фильтра по роли)
                    exact_user = db.query(User).filter(
                        func.lower(User.username) == func.lower(search_trimmed)
                    ).first()
                    if exact_user:
                        logger.warning(f"[SEARCH] ⚠ User exists but role='{exact_user.role}' (not CANDIDATE): id={exact_user.id}, username='{exact_user.username}'")
        
        # Фильтр по языкам программирования
        if programming_languages:
            languages = [lang.strip() for lang in programming_languages.split(",")]
            # Ищем кандидатов, у которых есть хотя бы один из указанных языков
            from sqlalchemy import or_, func, String
            conditions = []
            for lang in languages:
                # Для JSON полей в SQLite (хранятся как TEXT) используем простой LIKE
                # Проверяем в skills и programming_languages
                lang_lower = lang.lower()
                lang_pattern = f"%{lang_lower}%"
                # В SQLite JSON хранится как TEXT, поэтому можно использовать простой LIKE
                # Используем COALESCE для обработки NULL значений
                conditions.append(
                    func.lower(func.coalesce(func.cast(User.skills, String), '')).like(lang_pattern) |
                    func.lower(func.coalesce(func.cast(User.programming_languages, String), '')).like(lang_pattern)
                )
            if conditions:
                query = query.filter(or_(*conditions))
        
        # Фильтр по типу роли
        if role_type:
            try:
                role_type_enum = RoleType(role_type.lower())
                query = query.filter(User.role_type == role_type_enum)
            except ValueError:
                pass  # Игнорируем неверное значение
        
        # Фильтр по уровню опыта
        if experience_level:
            try:
                level_enum = ExperienceLevel(experience_level.lower())
                query = query.filter(User.experience_level == level_enum)
            except ValueError:
                pass  # Игнорируем неверное значение
        
        # Подсчет общего количества
        total_count = query.count()
        
        # Применяем пагинацию
        candidates = query.offset(offset).limit(limit).all()
        
        # Формируем ответ
        results = []
        for candidate in candidates:
            # Получаем среднюю оценку из интервью
            from backend.models.interview import InterviewSession
            sessions = db.query(InterviewSession).filter(
                InterviewSession.candidate_id == candidate.id,
                InterviewSession.status == InterviewStatus.COMPLETED
            ).all()
            
            avg_score = None
            if sessions:
                scores = [s.total_score for s in sessions if s.total_score is not None]
                if scores:
                    avg_score = sum(scores) / len(scores)
            
            results.append({
                "id": candidate.id,
                "username": candidate.username,
                "email": candidate.email,
                "full_name": candidate.full_name,
                "github_username": candidate.github_username,
                "linkedin_url": candidate.linkedin_url,
                "skills": candidate.skills or [],
                "programming_languages": candidate.programming_languages or [],
                "role_type": candidate.role_type.value if candidate.role_type else None,
                "experience_level": candidate.experience_level.value if candidate.experience_level else None,
                "success_prediction": candidate.success_prediction,
                "average_score": avg_score,
                "interviews_count": len(sessions),
                "created_at": candidate.created_at.isoformat() if candidate.created_at else None
            })
        
        logger.info(f"Search completed: found {len(results)} candidates out of {total_count} total (before filters: {total_before_filters})")
        
        return {
            "candidates": results,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error in HR search candidates: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/candidates/{user_id}/profile/metadata")
async def update_candidate_metadata(
    user_id: int,
    role_type: Optional[str] = None,
    experience_level: Optional[str] = None,
    programming_languages: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновление метаданных кандидата (role_type, experience_level, programming_languages)"""
    try:
        # Проверка прав доступа
        if current_user.id != user_id and current_user.role not in [Role.ADMIN, Role.HR]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Обновляем поля
        if role_type is not None:
            try:
                user.role_type = RoleType(role_type.lower()) if role_type else None
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid role_type: {role_type}")
        
        if experience_level is not None:
            try:
                user.experience_level = ExperienceLevel(experience_level.lower()) if experience_level else None
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid experience_level: {experience_level}")
        
        if programming_languages is not None:
            user.programming_languages = programming_languages
        
        db.commit()
        db.refresh(user)
        
        return {
            "message": "Metadata updated successfully",
            "user_id": user.id,
            "role_type": user.role_type.value if user.role_type else None,
            "experience_level": user.experience_level.value if user.experience_level else None,
            "programming_languages": user.programming_languages
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Chat & Invitations v2.0.0 ====================

class SendMessageRequest(BaseModel):
    recipient_id: int
    message_text: str

@app.post("/api/messages/send")
async def send_message(
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отправка сообщения"""
    try:
        from backend.services.message_service import message_service
        
        message = await message_service.send_message(
            db=db,
            sender_id=current_user.id,
            recipient_id=request.recipient_id,
            message_text=request.message_text
        )
        
        return {
            "id": message.id,
            "sender_id": message.sender_id,
            "recipient_id": message.recipient_id,
            "message_text": message.message_text,
            "status": message.status.value,
            "created_at": message.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/messages/conversation/{user_id}")
async def get_conversation(
    user_id: int,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение истории переписки с пользователем"""
    try:
        from backend.services.message_service import message_service
        
        messages = await message_service.get_conversation(
            db=db,
            user1_id=current_user.id,
            user2_id=user_id,
            limit=limit
        )
        
        return [
            {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "recipient_id": msg.recipient_id,
                "message_text": msg.message_text,
                "status": msg.status.value,
                "created_at": msg.created_at.isoformat(),
                "read_at": msg.read_at.isoformat() if msg.read_at else None,
                "is_from_me": msg.sender_id == current_user.id
            }
            for msg in messages
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/messages/conversations")
async def get_conversations_list(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение списка всех переписок"""
    try:
        from backend.services.message_service import message_service
        
        conversations = await message_service.get_conversations_list(
            db=db,
            user_id=current_user.id
        )
        
        return conversations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/messages/{message_id}/read")
async def mark_message_as_read(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отметка сообщения как прочитанного"""
    try:
        from backend.services.message_service import message_service
        
        message = await message_service.mark_as_read(
            db=db,
            message_id=message_id,
            user_id=current_user.id
        )
        
        return {
            "id": message.id,
            "status": message.status.value,
            "read_at": message.read_at.isoformat() if message.read_at else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/messages/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение количества непрочитанных сообщений"""
    try:
        from backend.services.message_service import message_service
        
        count = await message_service.get_unread_count(
            db=db,
            user_id=current_user.id
        )
        
        return {"unread_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/invitations/my-invitations")
async def get_my_invitations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение приглашений текущего пользователя (кандидата)"""
    try:
        from backend.services.message_service import invitation_service
        
        invitations = await invitation_service.get_candidate_invitations(
            db=db,
            candidate_id=current_user.id
        )
        
        result = []
        for inv in invitations:
            # Пропускаем завершенные приглашения (интервью пройдено)
            if inv.status == "completed":
                continue
                
            interview = db.query(Interview).filter(Interview.id == inv.interview_id).first()
            hr = db.query(User).filter(User.id == inv.hr_id).first()
            
            # Проверяем, завершено ли интервью для этого приглашения
            completed_session = db.query(InterviewSession).filter(
                InterviewSession.interview_id == inv.interview_id,
                InterviewSession.candidate_id == current_user.id,
                InterviewSession.status == InterviewStatus.COMPLETED
            ).first()
            
            # Если интервью завершено, пропускаем приглашение
            if completed_session:
                continue
            
            result.append({
                "id": inv.id,
                "interview_id": inv.interview_id,
                "interview_title": interview.title if interview else None,
                "interview_description": interview.description if interview else None,
                "hr_name": hr.full_name or hr.username if hr else None,
                "hr_id": inv.hr_id,
                "message": inv.message,
                "status": inv.status,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
                "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
                "responded_at": inv.responded_at.isoformat() if inv.responded_at else None
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/invitations/{invitation_id}/accept")
async def accept_invitation(
    invitation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Принятие приглашения на собеседование"""
    try:
        from backend.services.message_service import invitation_service
        
        invitation = await invitation_service.accept_invitation(
            db=db,
            invitation_id=invitation_id,
            candidate_id=current_user.id
        )
        
        return {
            "id": invitation.id,
            "status": invitation.status,
            "responded_at": invitation.responded_at.isoformat() if invitation.responded_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/invitations/{invitation_id}/decline")
async def decline_invitation(
    invitation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отклонение приглашения на собеседование"""
    try:
        from backend.services.message_service import invitation_service
        
        invitation = await invitation_service.decline_invitation(
            db=db,
            invitation_id=invitation_id,
            candidate_id=current_user.id
        )
        
        return {
            "id": invitation.id,
            "status": invitation.status,
            "responded_at": invitation.responded_at.isoformat() if invitation.responded_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/invitations/{invitation_id}/start-interview")
async def start_interview_from_invitation(
    invitation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Начало собеседования через приглашение (без кода доступа)"""
    try:
        from backend.services.message_service import invitation_service
        
        # Проверяем, что приглашение существует и принято
        invitation = db.query(InterviewInvitation).filter(
            InterviewInvitation.id == invitation_id,
            InterviewInvitation.candidate_id == current_user.id
        ).first()
        
        if not invitation:
            raise HTTPException(status_code=404, detail="Приглашение не найдено")
        
        if invitation.status != "accepted":
            raise HTTPException(status_code=400, detail="Приглашение не принято")
        
        # Проверяем срок действия
        if invitation.expires_at and invitation.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Приглашение истекло")
        
        # Проверяем, что интервью существует
        interview = db.query(Interview).filter(Interview.id == invitation.interview_id).first()
        if not interview:
            raise HTTPException(status_code=404, detail="Интервью не найдено")
        
        # Проверяем, нет ли уже активной сессии
        existing_session = db.query(InterviewSession).filter(
            InterviewSession.interview_id == invitation.interview_id,
            InterviewSession.candidate_id == current_user.id,
            InterviewSession.status.in_([InterviewStatus.SCHEDULED, InterviewStatus.IN_PROGRESS])
        ).first()
        
        if existing_session:
            return {
                "session_id": existing_session.id,
                "interview_id": interview.id,
                "message": "Сессия уже существует"
            }
        
        # Создаем новую сессию
        session = await interview_service.start_session(
            db=db,
            interview_id=invitation.interview_id,
            candidate_id=current_user.id
        )
        
        return {
            "session_id": session.id,
            "interview_id": interview.id,
            "message": "Собеседование начато"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== v3.0.0: Test Tasks API ====================

@app.post("/api/test-tasks")
async def create_test_task(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создание тестового задания (v3.0.0)"""
    try:
        from backend.services.test_task_service import test_task_service
        from backend.models.interview import ApplicationStatus
        
        if current_user.role not in [Role.HR, Role.ADMIN]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        task = await test_task_service.create_test_task(
            db=db,
            session_id=request["session_id"],
            title=request["title"],
            description=request["description"],
            task_type=request.get("task_type", "coding"),
            requirements=request.get("requirements"),
            deadline_days=request.get("deadline_days", 7),
            created_by=current_user.id
        )
        
        # Отправляем уведомление кандидату
        session = db.query(InterviewSession).filter(InterviewSession.id == request["session_id"]).first()
        if session and session.candidate:
            from backend.services.communication_automation import communication_automation
            await communication_automation.send_test_task_notification(
                candidate_email=session.candidate.email or "",
                candidate_name=session.candidate.full_name or session.candidate.username,
                task_title=task.title,
                deadline=task.deadline,
                interview_title=session.interview.title if session.interview else None
            )
        
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "status": task.status
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test-tasks/session/{session_id}")
async def get_test_tasks_for_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение тестовых заданий для сессии (v3.0.0)"""
    try:
        from backend.services.test_task_service import test_task_service
        
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Проверка прав доступа
        if current_user.id != session.candidate_id and current_user.role not in [Role.HR, Role.ADMIN]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        tasks = await test_task_service.get_test_tasks_for_session(db, session_id)
        
        return {
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "task_type": task.task_type,
                    "deadline": task.deadline.isoformat() if task.deadline else None,
                    "status": task.status,
                    "score": task.score,
                    "feedback": task.feedback,
                    "created_at": task.created_at.isoformat()
                }
                for task in tasks
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-tasks/{task_id}/submit")
async def submit_test_task_solution(
    task_id: int,
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отправка решения тестового задания (v3.0.0)"""
    try:
        from backend.services.test_task_service import test_task_service
        
        task = await test_task_service.submit_solution(
            db=db,
            task_id=task_id,
            solution=request["solution"],
            solution_files=request.get("solution_files"),
            candidate_id=current_user.id
        )
        
        return {
            "id": task.id,
            "status": task.status,
            "message": "Решение отправлено"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-tasks/{task_id}/review")
async def review_test_task(
    task_id: int,
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Проверка тестового задания HR (v3.0.0)"""
    try:
        from backend.services.test_task_service import test_task_service
        
        if current_user.role not in [Role.HR, Role.ADMIN]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        task = await test_task_service.review_task(
            db=db,
            task_id=task_id,
            score=request["score"],
            feedback=request.get("feedback", ""),
            reviewer_id=current_user.id
        )
        
        # Отправляем уведомление кандидату
        session = db.query(InterviewSession).filter(InterviewSession.id == task.session_id).first()
        if session and session.candidate:
            from backend.services.communication_automation import communication_automation
            old_status = "test_task"
            new_status = session.application_status.value if session.application_status else "test_task"
            if old_status != new_status:
                await communication_automation.notify_status_change(
                    candidate_email=session.candidate.email or "",
                    candidate_name=session.candidate.full_name or session.candidate.username,
                    old_status=old_status,
                    new_status=new_status,
                    interview_title=session.interview.title if session.interview else None
                )
        
        return {
            "id": task.id,
            "score": task.score,
            "feedback": task.feedback,
            "status": task.status
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== v3.0.0: Application Status API ====================

@app.put("/api/sessions/{session_id}/application-status")
async def update_application_status(
    session_id: int,
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновление статуса заявки кандидата (v3.0.0)"""
    try:
        from backend.models.interview import ApplicationStatus
        
        if current_user.role not in [Role.HR, Role.ADMIN]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        old_status = session.application_status.value if session.application_status else "active"
        new_status = request["status"]
        
        # Валидация статуса
        try:
            app_status = ApplicationStatus(new_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")
        
        session.application_status = app_status
        session.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(session)
        
        # Отправляем уведомление кандидату
        if session.candidate and old_status != new_status:
            from backend.services.communication_automation import communication_automation
            await communication_automation.notify_status_change(
                candidate_email=session.candidate.email or "",
                candidate_name=session.candidate.full_name or session.candidate.username,
                old_status=old_status,
                new_status=new_status,
                interview_title=session.interview.title if session.interview else None
            )
        
        return {
            "session_id": session.id,
            "application_status": session.application_status.value,
            "updated_at": session.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== v3.0.0: HH.ru Integration API ====================

@app.get("/auth/hh/login")
async def hh_login():
    """Инициация OAuth авторизации через HH.ru (v3.0.0)"""
    try:
        from backend.services.hh_integration import hh_integration
        import secrets
        
        state = secrets.token_urlsafe(32)
        auth_url = hh_integration.get_authorization_url(state=state)
        
        return {"auth_url": auth_url, "state": state}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/hh/callback")
async def hh_callback(
    code: str,
    state: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обработка OAuth callback от HH.ru (v3.0.0)"""
    try:
        from backend.services.hh_integration import hh_integration
        
        # Обмениваем code на токен
        token_data = await hh_integration.exchange_code_for_token(code)
        
        # Сохраняем токены в профиль пользователя
        current_user.hh_access_token = token_data["access_token"]
        if "refresh_token" in token_data:
            current_user.hh_refresh_token = token_data["refresh_token"]
        
        expires_in = token_data.get("expires_in", 3600)
        current_user.hh_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Получаем информацию о пользователе
        user_info = await hh_integration.get_user_info(token_data["access_token"])
        
        # Получаем резюме
        resumes = await hh_integration.get_resumes(token_data["access_token"])
        if resumes:
            resume_id = resumes[0]["id"]
            current_user.hh_resume_id = resume_id
            
            # Импортируем резюме
            resume_data = await hh_integration.get_resume(token_data["access_token"], resume_id)
            current_user = await hh_integration.import_resume_to_user(db, current_user, resume_data)
        
        db.commit()
        db.refresh(current_user)
        
        return {
            "status": "success",
            "message": "HH.ru профиль успешно подключен",
            "resume_imported": len(resumes) > 0 if resumes else False
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/hh/sync-profile")
async def sync_hh_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Синхронизация профиля с HH.ru (v3.0.0)"""
    try:
        from backend.services.hh_integration import hh_integration
        
        if not current_user.hh_access_token:
            raise HTTPException(status_code=400, detail="HH.ru не подключен")
        
        current_user = await hh_integration.sync_user_profile(db, current_user)
        
        return {
            "status": "success",
            "synced_at": current_user.hh_profile_synced_at.isoformat() if current_user.hh_profile_synced_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/hh/resume")
async def get_hh_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение данных резюме из HH.ru (v3.0.0)"""
    try:
        from backend.services.hh_integration import hh_integration
        
        if not current_user.hh_access_token:
            raise HTTPException(status_code=400, detail="HH.ru не подключен")
        
        if not current_user.hh_resume_id:
            raise HTTPException(status_code=404, detail="Резюме не найдено")
        
        resume_data = await hh_integration.get_resume(
            current_user.hh_access_token,
            current_user.hh_resume_id
        )
        
        return {
            "resume_id": current_user.hh_resume_id,
            "data": resume_data,
            "synced_at": current_user.hh_profile_synced_at.isoformat() if current_user.hh_profile_synced_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import os
    
    # Отключаем цветные логи в uvicorn
    os.environ["UVICORN_NO_COLORS"] = "1"
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None  # Используем нашу конфигурацию логирования
    )

