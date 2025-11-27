"""
Task Bank API Routes v4.2.0
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from backend.database import get_db
from backend.services.task_bank_service import task_bank_service
from backend.utils.auth import get_current_user
from backend.models.user import User

router = APIRouter(prefix="/api/task-bank", tags=["task-bank"])


# ========== Pydantic Models ==========

class TaskCreate(BaseModel):
    title: str
    description: str
    category_id: Optional[int] = None
    task_type: str  # coding, theory, system_design, algorithm
    difficulty: str  # easy, medium, hard, expert
    topic: Optional[str] = None
    tags: Optional[List[str]] = None
    programming_languages: Optional[List[str]] = None
    test_cases: Optional[List[dict]] = None
    test_suite: Optional[dict] = None
    hints: Optional[List[str]] = None
    solution_template: Optional[str] = None
    example_solution: Optional[str] = None
    explanation: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    task_type: Optional[str] = None
    difficulty: Optional[str] = None
    topic: Optional[str] = None
    tags: Optional[List[str]] = None
    programming_languages: Optional[List[str]] = None
    test_cases: Optional[List[dict]] = None
    test_suite: Optional[dict] = None
    hints: Optional[List[str]] = None
    solution_template: Optional[str] = None
    example_solution: Optional[str] = None
    explanation: Optional[str] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    icon: Optional[str] = None


# ========== Routes ==========

@router.post("/tasks")
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создание новой задачи в банке"""
    # Только HR и Admin могут создавать задачи
    if current_user.role not in ["hr", "admin"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    task = await task_bank_service.create_task(
        db,
        task_data.dict(),
        created_by=current_user.id
    )
    
    return {"success": True, "task_id": task.id, "message": "Задача создана"}


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение задачи по ID"""
    task = await task_bank_service.get_task(db, task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    return task


@router.put("/tasks/{task_id}")
async def update_task(
    task_id: int,
    updates: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновление задачи"""
    if current_user.role not in ["hr", "admin"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    task = await task_bank_service.update_task(
        db,
        task_id,
        {k: v for k, v in updates.dict().items() if v is not None}
    )
    
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    return {"success": True, "message": "Задача обновлена"}


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удаление задачи (soft delete)"""
    if current_user.role not in ["hr", "admin"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    success = await task_bank_service.delete_task(db, task_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    return {"success": True, "message": "Задача удалена"}


@router.get("/tasks")
async def search_tasks(
    query: Optional[str] = None,
    task_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    topic: Optional[str] = None,
    category_id: Optional[int] = None,
    programming_language: Optional[str] = None,
    is_verified: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Поиск задач с фильтрами"""
    tasks = await task_bank_service.search_tasks(
        db,
        query=query,
        task_type=task_type,
        difficulty=difficulty,
        topic=topic,
        category_id=category_id,
        programming_language=programming_language,
        is_verified=is_verified,
        limit=limit,
        offset=offset
    )
    
    return {"tasks": tasks, "count": len(tasks)}


@router.get("/tasks/recommended")
async def get_recommended_tasks(
    difficulty: str,
    topic: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение рекомендованных задач"""
    tasks = await task_bank_service.get_recommended_tasks(
        db,
        difficulty=difficulty,
        topic=topic,
        limit=limit
    )
    
    return {"tasks": tasks, "count": len(tasks)}


@router.post("/export")
async def export_tasks(
    task_ids: Optional[List[int]] = None,
    format: str = "json",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Экспорт задач в JSON или YAML"""
    if current_user.role not in ["hr", "admin"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    if format not in ["json", "yaml"]:
        raise HTTPException(status_code=400, detail="Формат должен быть json или yaml")
    
    data = await task_bank_service.export_tasks(db, task_ids, format)
    
    return {"success": True, "data": data, "format": format}


@router.post("/import")
async def import_tasks(
    data: str,
    format: str = "json",
    overwrite: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Импорт задач из JSON или YAML"""
    if current_user.role not in ["hr", "admin"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    if format not in ["json", "yaml"]:
        raise HTTPException(status_code=400, detail="Формат должен быть json или yaml")
    
    result = await task_bank_service.import_tasks(
        db,
        data,
        format=format,
        created_by=current_user.id,
        overwrite=overwrite
    )
    
    return result


# ========== Categories ==========

@router.post("/categories")
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создание новой категории"""
    if current_user.role not in ["hr", "admin"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    category = await task_bank_service.create_category(
        db,
        name=category_data.name,
        description=category_data.description,
        parent_id=category_data.parent_id,
        icon=category_data.icon
    )
    
    return {"success": True, "category_id": category.id}


@router.get("/categories")
async def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение всех категорий"""
    categories = await task_bank_service.get_categories(db)
    
    return {"categories": categories}

