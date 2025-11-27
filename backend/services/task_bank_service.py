"""
Task Bank Service v4.2.0 - управление банком задач

Возможности:
- Импорт/экспорт задач (JSON, YAML)
- Поиск и фильтрация задач
- Категоризация задач
- Статистика использования
- Рекомендации задач
"""
import json
import yaml
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import datetime

from backend.models.task_bank import TaskTemplate, TaskCategory
from backend.utils.logger import get_module_logger

logger = get_module_logger("TaskBankService")


class TaskBankService:
    """Сервис управления банком задач"""
    
    def __init__(self):
        pass
    
    # ========== CRUD операции ==========
    
    async def create_task(
        self,
        db: Session,
        task_data: Dict[str, Any],
        created_by: Optional[int] = None
    ) -> TaskTemplate:
        """Создает новую задачу в банке"""
        task = TaskTemplate(
            title=task_data["title"],
            description=task_data["description"],
            category_id=task_data.get("category_id"),
            task_type=task_data["task_type"],
            difficulty=task_data["difficulty"],
            topic=task_data.get("topic"),
            tags=task_data.get("tags", []),
            programming_languages=task_data.get("programming_languages", []),
            test_cases=task_data.get("test_cases", []),
            test_suite=task_data.get("test_suite"),
            hints=task_data.get("hints", []),
            solution_template=task_data.get("solution_template"),
            example_solution=task_data.get("example_solution"),
            explanation=task_data.get("explanation"),
            created_by=created_by,
        )
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        logger.info(f"Создана новая задача в банке: {task.title} (ID: {task.id})")
        
        return task
    
    async def get_task(self, db: Session, task_id: int) -> Optional[TaskTemplate]:
        """Получает задачу по ID"""
        return db.query(TaskTemplate).filter(TaskTemplate.id == task_id).first()
    
    async def update_task(
        self,
        db: Session,
        task_id: int,
        updates: Dict[str, Any]
    ) -> Optional[TaskTemplate]:
        """Обновляет задачу"""
        task = await self.get_task(db, task_id)
        if not task:
            return None
        
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        db.commit()
        db.refresh(task)
        
        return task
    
    async def delete_task(self, db: Session, task_id: int) -> bool:
        """Удаляет задачу (soft delete - помечает как неактивную)"""
        task = await self.get_task(db, task_id)
        if not task:
            return False
        
        task.is_active = False
        db.commit()
        
        return True
    
    # ========== Поиск и фильтрация ==========
    
    async def search_tasks(
        self,
        db: Session,
        query: Optional[str] = None,
        task_type: Optional[str] = None,
        difficulty: Optional[str] = None,
        topic: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category_id: Optional[int] = None,
        programming_language: Optional[str] = None,
        is_verified: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TaskTemplate]:
        """Поиск задач с фильтрами"""
        filters = [TaskTemplate.is_active == True]
        
        # Текстовый поиск
        if query:
            filters.append(
                or_(
                    TaskTemplate.title.ilike(f"%{query}%"),
                    TaskTemplate.description.ilike(f"%{query}%")
                )
            )
        
        # Фильтры
        if task_type:
            filters.append(TaskTemplate.task_type == task_type)
        
        if difficulty:
            filters.append(TaskTemplate.difficulty == difficulty)
        
        if topic:
            filters.append(TaskTemplate.topic == topic)
        
        if category_id:
            filters.append(TaskTemplate.category_id == category_id)
        
        if is_verified is not None:
            filters.append(TaskTemplate.is_verified == is_verified)
        
        # Поиск по тегам
        if tags:
            for tag in tags:
                filters.append(TaskTemplate.tags.contains([tag]))
        
        # Поиск по языку программирования
        if programming_language:
            filters.append(TaskTemplate.programming_languages.contains([programming_language]))
        
        tasks = db.query(TaskTemplate).filter(and_(*filters)).offset(offset).limit(limit).all()
        
        return tasks
    
    async def get_recommended_tasks(
        self,
        db: Session,
        difficulty: str,
        topic: Optional[str] = None,
        limit: int = 10
    ) -> List[TaskTemplate]:
        """Получает рекомендованные задачи на основе критериев"""
        filters = [
            TaskTemplate.is_active == True,
            TaskTemplate.difficulty == difficulty,
        ]
        
        if topic:
            filters.append(TaskTemplate.topic == topic)
        
        # Сортируем по quality_score и usage_count
        tasks = (
            db.query(TaskTemplate)
            .filter(and_(*filters))
            .order_by(
                TaskTemplate.quality_score.desc().nullslast(),
                TaskTemplate.usage_count.asc()  # Предпочитаем менее использованные
            )
            .limit(limit)
            .all()
        )
        
        return tasks
    
    # ========== Импорт/Экспорт ==========
    
    async def export_tasks(
        self,
        db: Session,
        task_ids: Optional[List[int]] = None,
        format: str = "json"
    ) -> str:
        """
        Экспортирует задачи в JSON или YAML
        
        Args:
            db: Database session
            task_ids: Список ID задач (None = все задачи)
            format: "json" или "yaml"
        
        Returns:
            Строка с экспортированными данными
        """
        if task_ids:
            tasks = db.query(TaskTemplate).filter(TaskTemplate.id.in_(task_ids)).all()
        else:
            tasks = db.query(TaskTemplate).filter(TaskTemplate.is_active == True).all()
        
        # Сериализуем задачи
        tasks_data = []
        for task in tasks:
            task_dict = {
                "title": task.title,
                "description": task.description,
                "task_type": task.task_type,
                "difficulty": task.difficulty,
                "topic": task.topic,
                "tags": task.tags,
                "programming_languages": task.programming_languages,
                "test_cases": task.test_cases,
                "test_suite": task.test_suite,
                "hints": task.hints,
                "solution_template": task.solution_template,
                "example_solution": task.example_solution,
                "explanation": task.explanation,
                # Метаданные
                "quality_score": task.quality_score,
                "is_verified": task.is_verified,
            }
            tasks_data.append(task_dict)
        
        export_data = {
            "version": "4.2.0",
            "exported_at": datetime.utcnow().isoformat(),
            "tasks_count": len(tasks_data),
            "tasks": tasks_data
        }
        
        if format == "yaml":
            return yaml.dump(export_data, allow_unicode=True, default_flow_style=False)
        else:
            return json.dumps(export_data, ensure_ascii=False, indent=2)
    
    async def import_tasks(
        self,
        db: Session,
        data: str,
        format: str = "json",
        created_by: Optional[int] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Импортирует задачи из JSON или YAML
        
        Args:
            db: Database session
            data: Данные для импорта
            format: "json" или "yaml"
            created_by: ID создателя
            overwrite: Перезаписывать существующие задачи
        
        Returns:
            Статистика импорта
        """
        try:
            if format == "yaml":
                import_data = yaml.safe_load(data)
            else:
                import_data = json.loads(data)
        except Exception as e:
            logger.error(f"Ошибка парсинга данных импорта: {e}")
            return {
                "success": False,
                "error": f"Ошибка парсинга: {str(e)}",
                "imported": 0,
                "skipped": 0,
                "errors": 0
            }
        
        if not isinstance(import_data, dict) or "tasks" not in import_data:
            return {
                "success": False,
                "error": "Неверный формат данных",
                "imported": 0,
                "skipped": 0,
                "errors": 0
            }
        
        tasks_data = import_data["tasks"]
        imported_count = 0
        skipped_count = 0
        errors_count = 0
        
        for task_data in tasks_data:
            try:
                # Проверяем, существует ли задача с таким названием
                existing_task = db.query(TaskTemplate).filter(
                    TaskTemplate.title == task_data["title"]
                ).first()
                
                if existing_task:
                    if overwrite:
                        # Обновляем существующую задачу
                        await self.update_task(db, existing_task.id, task_data)
                        imported_count += 1
                    else:
                        skipped_count += 1
                        logger.info(f"Пропущена существующая задача: {task_data['title']}")
                else:
                    # Создаем новую задачу
                    await self.create_task(db, task_data, created_by)
                    imported_count += 1
            
            except Exception as e:
                errors_count += 1
                logger.error(f"Ошибка импорта задачи {task_data.get('title', 'unknown')}: {e}")
        
        return {
            "success": True,
            "imported": imported_count,
            "skipped": skipped_count,
            "errors": errors_count,
            "total": len(tasks_data)
        }
    
    # ========== Категории ==========
    
    async def create_category(
        self,
        db: Session,
        name: str,
        description: Optional[str] = None,
        parent_id: Optional[int] = None,
        icon: Optional[str] = None
    ) -> TaskCategory:
        """Создает новую категорию"""
        category = TaskCategory(
            name=name,
            description=description,
            parent_id=parent_id,
            icon=icon
        )
        
        db.add(category)
        db.commit()
        db.refresh(category)
        
        return category
    
    async def get_categories(self, db: Session) -> List[TaskCategory]:
        """Получает все категории"""
        return db.query(TaskCategory).all()
    
    # ========== Статистика ==========
    
    async def update_task_stats(
        self,
        db: Session,
        task_id: int,
        score: Optional[float] = None,
        time_spent: Optional[float] = None,
        passed: Optional[bool] = None
    ) -> None:
        """Обновляет статистику использования задачи"""
        task = await self.get_task(db, task_id)
        if not task:
            return
        
        # Увеличиваем счетчик использования
        task.usage_count += 1
        
        # Обновляем среднюю оценку
        if score is not None:
            if task.average_score is None:
                task.average_score = score
            else:
                # Скользящее среднее
                task.average_score = (task.average_score * (task.usage_count - 1) + score) / task.usage_count
        
        # Обновляем среднее время
        if time_spent is not None:
            if task.average_time is None:
                task.average_time = time_spent
            else:
                task.average_time = (task.average_time * (task.usage_count - 1) + time_spent) / task.usage_count
        
        # Обновляем процент прохождения
        if passed is not None:
            if task.pass_rate is None:
                task.pass_rate = 100.0 if passed else 0.0
            else:
                passed_count = int(task.pass_rate * (task.usage_count - 1) / 100)
                if passed:
                    passed_count += 1
                task.pass_rate = (passed_count / task.usage_count) * 100
        
        db.commit()


# Глобальный экземпляр
task_bank_service = TaskBankService()

