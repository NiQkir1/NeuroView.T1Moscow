"""
Шаблонные вопросы для первых двух этапов интервью
Эти вопросы выбираются интервьюером (HR) при создании интервью
"""
from typing import List, Dict, Any, Optional
from enum import Enum


class QuestionCategory(str, Enum):
    """Категории шаблонных вопросов"""
    EXPERIENCE = "experience"  # Опыт работы
    PROJECTS = "projects"  # Проекты
    MOTIVATION = "motivation"  # Мотивация
    TEAMWORK = "teamwork"  # Работа в команде
    GOALS = "goals"  # Цели
    PERSONAL = "personal"  # Личная информация


# Шаблонные вопросы для этапа READY_CHECK (проверка готовности)
READY_CHECK_TEMPLATES = [
    {
        "id": "ready_1",
        "text": "Здравствуйте! Готовы ли вы начать собеседование?",
        "category": "ready",
        "order": 0
    }
]

# Шаблонные вопросы для этапа INTRODUCTION (общие вопросы)
INTRODUCTION_TEMPLATES = {
    QuestionCategory.EXPERIENCE: [
        {
            "id": "intro_exp_1",
            "text": "Расскажите о своем профессиональном опыте. Где вы работали и какие задачи решали?",
            "category": QuestionCategory.EXPERIENCE,
            "triggers": ["проект", "работал", "участвовал", "разрабатывал", "создавал"]
        },
        {
            "id": "intro_exp_2",
            "text": "Какой у вас опыт работы в сфере разработки?",
            "category": QuestionCategory.EXPERIENCE,
            "triggers": ["опыт", "работа", "разработка"]
        },
        {
            "id": "intro_exp_3",
            "text": "Какие технологии и инструменты вы использовали в своих проектах?",
            "category": QuestionCategory.EXPERIENCE,
            "triggers": ["технологии", "инструменты", "стек"]
        }
    ],
    QuestionCategory.PROJECTS: [
        {
            "id": "intro_proj_1",
            "text": "Расскажите о самом интересном проекте, над которым вы работали. Что вы делали и какие результаты достигли?",
            "category": QuestionCategory.PROJECTS,
            "triggers": ["проект", "разрабатывал", "создавал", "участвовал"]
        },
        {
            "id": "intro_proj_2",
            "text": "Опишите проект, который вас больше всего мотивировал. Почему?",
            "category": QuestionCategory.PROJECTS,
            "triggers": ["проект", "мотивировал", "интересный"]
        }
    ],
    QuestionCategory.MOTIVATION: [
        {
            "id": "intro_mot_1",
            "text": "Что вас мотивирует в работе? Почему вы выбрали профессию разработчика?",
            "category": QuestionCategory.MOTIVATION,
            "triggers": ["мотивация", "нравится", "интересно"]
        },
        {
            "id": "intro_mot_2",
            "text": "Что для вас важно в работе? Какие факторы влияют на ваше решение о смене работы?",
            "category": QuestionCategory.MOTIVATION,
            "triggers": ["важно", "факторы", "решение"]
        }
    ],
    QuestionCategory.TEAMWORK: [
        {
            "id": "intro_team_1",
            "text": "Расскажите о своем опыте работы в команде. Как вы взаимодействуете с коллегами?",
            "category": QuestionCategory.TEAMWORK,
            "triggers": ["команда", "коллеги", "взаимодействие"]
        },
        {
            "id": "intro_team_2",
            "text": "Как вы решаете конфликты в команде? Приведите пример.",
            "category": QuestionCategory.TEAMWORK,
            "triggers": ["конфликт", "проблема", "спор"]
        }
    ],
    QuestionCategory.GOALS: [
        {
            "id": "intro_goal_1",
            "text": "Какие у вас карьерные цели? Где вы видите себя через 3-5 лет?",
            "category": QuestionCategory.GOALS,
            "triggers": ["цели", "планы", "будущее"]
        },
        {
            "id": "intro_goal_2",
            "text": "Что вы хотите изучить или улучшить в ближайшее время?",
            "category": QuestionCategory.GOALS,
            "triggers": ["изучить", "улучшить", "развить"]
        }
    ],
    QuestionCategory.PERSONAL: [
        {
            "id": "intro_pers_1",
            "text": "Расскажите немного о себе. Что вас интересует помимо работы?",
            "category": QuestionCategory.PERSONAL,
            "triggers": ["о себе", "интересы", "хобби"]
        }
    ]
}


def get_template_question(
    stage: str, 
    category: Optional[str] = None, 
    question_id: Optional[str] = None,
    hr_questions: Optional[List[Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """
    Получить шаблонный вопрос для этапа
    
    Args:
        stage: Этап интервью (ready_check, introduction)
        category: Категория вопроса (для introduction)
        question_id: ID конкретного вопроса
        hr_questions: Вопросы из конфигуратора HR (приоритет над встроенными)
    
    Returns:
        Шаблонный вопрос или None
    """
    # Если есть вопросы от HR, используем их в первую очередь
    if hr_questions:
        if question_id:
            for q in hr_questions:
                if q.get("id") == question_id or q.get("text") == question_id:
                    return q
        # Возвращаем первый вопрос из HR, если ID не указан
        if hr_questions:
            return hr_questions[0]
    
    # Fallback на встроенные шаблоны
    if stage == "ready_check":
        if question_id:
            for q in READY_CHECK_TEMPLATES:
                if q["id"] == question_id:
                    return q
        return READY_CHECK_TEMPLATES[0] if READY_CHECK_TEMPLATES else None
    
    elif stage == "introduction":
        if question_id:
            # Ищем во всех категориях
            for cat_questions in INTRODUCTION_TEMPLATES.values():
                for q in cat_questions:
                    if q["id"] == question_id:
                        return q
            return None
        
        if category:
            try:
                cat_enum = QuestionCategory(category)
                questions = INTRODUCTION_TEMPLATES.get(cat_enum, [])
                return questions[0] if questions else None
            except ValueError:
                return None
        
        # Возвращаем первый вопрос из первой категории
        first_category = list(INTRODUCTION_TEMPLATES.values())[0]
        return first_category[0] if first_category else None
    
    return None


def get_hr_template_questions(interview_config: Dict[str, Any], stage: str) -> Optional[List[Dict[str, Any]]]:
    """
    Получить шаблонные вопросы из конфигуратора HR
    
    Args:
        interview_config: Конфигурация интервью
        stage: Этап интервью (ready_check, introduction, softSkills)
    
    Returns:
        Список вопросов от HR или None
    """
    # Сначала проверяем template_questions (правильное место)
    template_questions = interview_config.get("template_questions", {})
    questions = None
    
    if stage == "ready_check":
        questions = template_questions.get("ready_check", [])
    elif stage == "introduction":
        questions = template_questions.get("introduction", [])
    elif stage == "softSkills":
        questions = template_questions.get("softSkills", [])
    
    # Если не найдено в template_questions, проверяем questions_per_stage (для обратной совместимости)
    if not questions:
        questions_per_stage = interview_config.get("questions_per_stage", {})
        if stage == "introduction":
            questions = questions_per_stage.get("introduction", [])
        elif stage == "softSkills":
            questions = questions_per_stage.get("softSkills", [])
        
        # Преобразуем строки в объекты, если нужно
        if questions and isinstance(questions, list) and questions:
            if isinstance(questions[0], str):
                # Это массив строк, преобразуем в объекты
                questions = [
                    {
                        "id": f"hr_{stage}_{i}",
                        "text": q,
                        "category": "custom"
                    }
                    for i, q in enumerate(questions)
                ]
    
    if questions:
        # Если это список ID (строк), возвращаем как есть (будет использован для поиска)
        if isinstance(questions, list):
            if questions and isinstance(questions[0], str):
                # Это список ID, возвращаем как есть
                return questions
            # Это уже список объектов вопросов
            return questions
        # Это один вопрос
        return [questions]
    
    return None


def get_all_templates_for_stage(stage: str) -> List[Dict[str, Any]]:
    """
    Получить все шаблонные вопросы для этапа
    
    Args:
        stage: Этап интервью
    
    Returns:
        Список шаблонных вопросов
    """
    if stage == "ready_check":
        return READY_CHECK_TEMPLATES.copy()
    
    elif stage == "introduction":
        all_questions = []
        for cat_questions in INTRODUCTION_TEMPLATES.values():
            all_questions.extend(cat_questions)
        return all_questions
    
    return []


def find_follow_up_question(answer_text: str, previous_question: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Найти вопрос для уточнения на основе ответа кандидата
    
    Args:
        answer_text: Текст ответа кандидата
        previous_question: Предыдущий вопрос
    
    Returns:
        Вопрос для уточнения или None
    """
    answer_lower = answer_text.lower()
    
    # Проверяем упоминание проектов
    project_keywords = ["проект", "разрабатывал", "создавал", "участвовал", "работал над", "делал"]
    if any(keyword in answer_lower for keyword in project_keywords):
        # Ищем вопросы о проектах
        project_questions = INTRODUCTION_TEMPLATES.get(QuestionCategory.PROJECTS, [])
        if project_questions:
            # Возвращаем вопрос, который еще не задавался
            for q in project_questions:
                if q["id"] != previous_question.get("id"):
                    return q
    
    # Проверяем упоминание технологий
    tech_keywords = ["python", "javascript", "java", "react", "django", "flask", "sql", "api"]
    if any(keyword in answer_lower for keyword in tech_keywords):
        # Возвращаем вопрос о технологиях
        exp_questions = INTRODUCTION_TEMPLATES.get(QuestionCategory.EXPERIENCE, [])
        for q in exp_questions:
            if "технологии" in q["text"].lower() and q["id"] != previous_question.get("id"):
                return q
    
    return None

