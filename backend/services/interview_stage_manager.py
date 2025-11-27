"""
Менеджер стадий интервью
Управляет переходами между стадиями и выбором агентов
"""
from typing import Dict, Any, Optional, List
from enum import Enum

from backend.services.agents import (
    general_agent,
    technical_agent,
    coding_agent,
)


class InterviewStage(str, Enum):
    """Стадии интервью"""
    READY_CHECK = "ready_check"  # Проверка готовности к началу
    INTRODUCTION = "introduction"  # Общие вопросы
    SOFT_SKILLS = "softSkills"  # Софт-скиллы
    TECHNICAL = "technical"  # Технические вопросы
    LIVE_CODING = "liveCoding"  # Лайвкодинг


class InterviewStageManager:
    """Менеджер для управления стадиями интервью"""

    DEFAULT_STAGE_QUESTION_LIMITS = {
        InterviewStage.READY_CHECK.value: 1,
        InterviewStage.INTRODUCTION.value: 2,
        InterviewStage.SOFT_SKILLS.value: 2,
        InterviewStage.TECHNICAL.value: 3,
        InterviewStage.LIVE_CODING.value: 1,
    }
    
    # Маппинг стадий на агентов
    STAGE_AGENT_MAP = {
        InterviewStage.READY_CHECK: general_agent,  # Для вопроса готовности используем general_agent
        InterviewStage.INTRODUCTION: general_agent,
        InterviewStage.SOFT_SKILLS: general_agent,  # Софт-скиллы обрабатываются general_agent
        InterviewStage.TECHNICAL: technical_agent,
        InterviewStage.LIVE_CODING: coding_agent,
    }
    
    # Порядок стадий
    STAGE_ORDER = [
        InterviewStage.READY_CHECK,
        InterviewStage.INTRODUCTION,
        InterviewStage.SOFT_SKILLS,
        InterviewStage.TECHNICAL,
        InterviewStage.LIVE_CODING,
    ]
    
    @staticmethod
    def get_agent_for_stage(stage: str):
        """Получить агента для стадии"""
        try:
            stage_enum = InterviewStage(stage)
            return InterviewStageManager.STAGE_AGENT_MAP.get(stage_enum)
        except ValueError:
            return general_agent  # По умолчанию
    
    @staticmethod
    def _is_stage_enabled(stage_value: str, interview_config: Optional[Dict[str, Any]]) -> bool:
        """Проверяем, активна ли стадия в конфиге"""
        if stage_value == InterviewStage.READY_CHECK.value:
            return True
        config = interview_config or {}
        stages_config = config.get("stages") or {}
        # По умолчанию стадия активна, если явно не отключена
        return stages_config.get(stage_value, True)
    
    @staticmethod
    def get_stage_sequence(interview_config: Optional[Dict[str, Any]] = None) -> List[str]:
        """Возвращает упорядоченный список активных стадий без ready_check"""
        sequence: List[str] = []
        for stage in InterviewStageManager.STAGE_ORDER:
            if stage == InterviewStage.READY_CHECK:
                continue
            if InterviewStageManager._is_stage_enabled(stage.value, interview_config):
                sequence.append(stage.value)
        return sequence
    
    @staticmethod
    def get_next_stage(current_stage: str, interview_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Получить следующую активную стадию
        
        Args:
            current_stage: Текущая стадия
            interview_config: Конфигурация интервью (для проверки активных стадий)
            
        Returns:
            Следующая стадия или None
        """
        try:
            stage_order = [InterviewStage.READY_CHECK.value] + InterviewStageManager.get_stage_sequence(interview_config)
            # Если конфиг пустой, придерживаемся полного порядка
            if len(stage_order) == 1:
                stage_order = [stage.value for stage in InterviewStageManager.STAGE_ORDER]
            
            current_index = stage_order.index(current_stage)
            for next_stage in stage_order[current_index + 1:]:
                if InterviewStageManager._is_stage_enabled(next_stage, interview_config):
                    return next_stage
        except (ValueError, IndexError):
            return None
        return None
    
    @staticmethod
    def is_last_stage(current_stage: str) -> bool:
        """Проверить, является ли стадия последней"""
        try:
            current_index = InterviewStageManager.STAGE_ORDER.index(InterviewStage(current_stage))
            return current_index == len(InterviewStageManager.STAGE_ORDER) - 1
        except (ValueError, IndexError):
            return False
    
    @staticmethod
    def should_advance_stage(
        stage_progress: Dict[str, Any],
        current_stage: str,
        interview_config: Dict[str, Any]
    ) -> bool:
        """
        Определить, нужно ли переходить на следующую стадию
        
        Args:
            stage_progress: Прогресс по стадиям
            current_stage: Текущая стадия
            interview_config: Конфигурация интервью
        
        Returns:
            True, если нужно перейти на следующую стадию
        """
        if not stage_progress:
            return False
        
        stage_info = stage_progress.get(current_stage, {})
        questions_asked = stage_info.get("questions_asked", 0)
        questions_required = stage_info.get("questions_required", 0)
        
        # Для ready_check переходим после первого ответа (независимо от счетчика)
        if current_stage == InterviewStage.READY_CHECK.value:
            return True  # Всегда переходим после ready_check
        
        # Переходим, если задано достаточно вопросов
        if questions_required > 0 and questions_asked >= questions_required:
            return True
        
        # Переходим, если стадия завершена
        if stage_info.get("completed", False):
            return True
        
        return False
    
    @staticmethod
    def initialize_stage_progress(interview_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Инициализировать прогресс по стадиям на основе конфигурации
        
        Args:
            interview_config: Конфигурация интервью
        
        Returns:
            Словарь с прогрессом по стадиям
        """
        config = interview_config or {}
        
        # Получаем количество вопросов для каждой стадии
        # Поддерживаем оба формата: snake_case и camelCase
        questions_per_stage = config.get("questions_per_stage", {}) or config.get("questionsPerStage", {})
        
        # Также проверяем template_questions для introduction и softSkills
        template_questions = config.get("template_questions", {})
        
        stage_progress = {}
        for stage in InterviewStageManager.STAGE_ORDER:
            stage_value = stage.value
            questions_required = 0
            questions_defaults = InterviewStageManager.DEFAULT_STAGE_QUESTION_LIMITS.get(stage_value, 0)
            
            stage_enabled = InterviewStageManager._is_stage_enabled(stage_value, config)
            if not stage_enabled:
                stage_progress[stage_value] = {
                    "questions_asked": 0,
                    "questions_required": 0,
                    "completed": True,
                }
                continue
            
            if stage_value == InterviewStage.READY_CHECK.value:
                questions_required = questions_defaults
            elif stage_value in ["introduction", "softSkills"]:
                template_list = template_questions.get(stage_value, [])
                if isinstance(template_list, list) and len(template_list) > 0:
                    questions_required = len(template_list)
                else:
                    questions_list = questions_per_stage.get(stage_value, [])
                    if isinstance(questions_list, list):
                        questions_required = len(questions_list)
                    elif isinstance(questions_list, int):
                        questions_required = questions_list
            else:
                questions_required = questions_per_stage.get(stage_value, 0)
                if not isinstance(questions_required, int):
                    if isinstance(questions_required, list):
                        questions_required = len(questions_required)
                    else:
                        questions_required = 0
            
            if questions_required <= 0:
                questions_required = questions_defaults
            
            stage_progress[stage_value] = {
                "questions_asked": 0,
                "questions_required": questions_required,
                "completed": False,
            }
        
        return stage_progress
    
    @staticmethod
    def update_stage_progress(
        stage_progress: Dict[str, Any],
        current_stage: str,
        question_asked: bool = True
    ) -> Dict[str, Any]:
        """
        Обновить прогресс по стадии
        
        Args:
            stage_progress: Текущий прогресс
            current_stage: Текущая стадия
            question_asked: Был ли задан вопрос
        
        Returns:
            Обновленный прогресс
        """
        if not stage_progress:
            stage_progress = {}
        
        if current_stage not in stage_progress:
            stage_progress[current_stage] = {
                "questions_asked": 0,
                "questions_required": 0,
                "completed": False,
            }
        
        if question_asked:
            stage_progress[current_stage]["questions_asked"] = (
                stage_progress[current_stage].get("questions_asked", 0) + 1
            )
        
        return stage_progress
    
    @staticmethod
    def complete_stage(
        stage_progress: Dict[str, Any],
        stage: str
    ) -> Dict[str, Any]:
        """Отметить стадию как завершенную"""
        if not stage_progress:
            stage_progress = {}
        
        if stage not in stage_progress:
            stage_progress[stage] = {}
        
        stage_progress[stage]["completed"] = True
        return stage_progress
