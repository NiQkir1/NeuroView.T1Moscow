"""
Interview Service - управление собеседованиями
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import re

from backend.models import Interview, InterviewSession, Question, Answer
from backend.models.interview import InterviewStatus, QuestionType
from backend.services.ai_engine import ai_engine
from backend.services.interview_stage_manager import (
    InterviewStageManager,
    InterviewStage,
)
from backend.services.agents import emotion_agent, coding_agent
from backend.services.ai_injection_guard import ai_injection_guard
from backend.utils.logger import get_module_logger

logger = get_module_logger("InterviewService")

# Импортируем процессор ответов для фоновой обработки
try:
    from backend.services.answer_processor import answer_processor
    ANSWER_PROCESSOR_AVAILABLE = True
except ImportError:
    logger.warning("Answer processor not available")
    ANSWER_PROCESSOR_AVAILABLE = False


class InterviewService:
    """Сервис для управления собеседованиями"""
    
    def __init__(self):
        self.ai_engine = ai_engine
    
    def _build_effective_config(self, interview: Interview) -> Dict[str, Any]:
        """
        Формирует рабочую конфигурацию интервью, объединяя настройки шаблона,
        кандидата и HR-конструктора.
        """
        config = dict(interview.interview_config or {})
        
        def ensure(key: str, value: Optional[Any]):
            if key not in config and value:
                config[key] = value
        
        ensure("stages", interview.stages)
        ensure("topics", interview.topics)
        ensure("position", interview.position)
        ensure("level", interview.level)
        ensure("programming_languages", interview.programming_languages)
        ensure("timer", interview.timer)
        if interview.hr_prompt and "hr_prompt" not in config:
            config["hr_prompt"] = interview.hr_prompt
        
        # Поддерживаем старое название ключа required_skills
        if "required_skills" not in config and config.get("topics"):
            config["required_skills"] = config["topics"]
        
        return config
    
    def _resolve_topics(self, interview: Interview, interview_config: Dict[str, Any]) -> List[str]:
        """Определяем список тем для текущего интервью."""
        topics = (
            interview_config.get("topics")
            or interview_config.get("required_skills")
            or interview.topics
        )
        if not topics:
            return ["programming"]
        if isinstance(topics, list):
            return topics or ["programming"]
        return [str(topics)]
    
    def _resolve_primary_language(self, interview: Interview, interview_config: Dict[str, Any]) -> str:
        """Определяем основной язык программирования для кодинга."""
        languages = (
            interview_config.get("programming_languages")
            or interview.programming_languages
            or ["python"]
        )
        if isinstance(languages, list) and len(languages) > 0:
            return languages[0]
        if isinstance(languages, str):
            return languages
        return "python"
    
    def _sanitize_agent_feedback(self, feedback: str) -> str:
        """
        Очистка фидбека агента от ответов, подсказок и объяснений.
        Если агент пытается объяснить тему или дать правильный ответ - заменяем на заглушку.
        """
        if not feedback:
            return ""
            
        # Паттерны "доброго учителя", которые запрещены
        forbidden_patterns = [
            r"давайте (я )?объясню",
            r"давайте (я )?расскажу",
            r"вот (правильный )?ответ",
            r"правильный ответ(:)?",
            r"вот пример",
            r"например,",
            r"смотрите,",
            r"давайте разберем",
            r"объяснение:",
            r"def solution",
            r"class solution",
            r"import ",
            r"```python",
            r"```java",
            r"```cpp",
        ]
        
        feedback_lower = feedback.lower()
        for pattern in forbidden_patterns:
            if re.search(pattern, feedback_lower):
                logger.warning(f"Санитайзер: обнаружен запрещенный паттерн '{pattern}' в фидбеке. Фидбек удален.")
                return "Интервьюер не дает подсказок, объяснений и правильных ответов во время интервью. Пожалуйста, переходите к следующему вопросу."
        
        return feedback

    async def create_interview(
        self,
        db: Session,
        title: str,
        description: Optional[str] = None,
        topics: Optional[List[str]] = None,
        stages: Optional[dict] = None,
        access_code: Optional[str] = None,
        difficulty: str = "medium",
        duration_minutes: int = 60,
        created_by: Optional[int] = None,
        hr_prompt: Optional[str] = None,
        interview_config: Optional[Dict[str, Any]] = None,
        position: Optional[str] = None,
        level: Optional[str] = None,
        programming_languages: Optional[List[str]] = None,
        timer: Optional[Dict[str, Any]] = None
    ) -> Interview:
        """Создание нового собеседования"""
        interview = Interview(
            title=title,
            description=description,
            topics=topics or [],
            stages=stages or {},
            access_code=access_code,
            difficulty=difficulty,
            duration_minutes=duration_minutes,
            position=position,
            level=level,
            programming_languages=programming_languages or [],
            timer=timer,
            created_by=created_by,
            hr_prompt=hr_prompt,
            interview_config=interview_config or {},
        )
        db.add(interview)
        db.commit()
        db.refresh(interview)
        return interview
    
    async def start_session(
        self,
        db: Session,
        interview_id: int,
        candidate_id: int
    ) -> InterviewSession:
        """Начало сессии собеседования"""
        interview = db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise ValueError("Собеседование не найдено")
        
        # Логируем конфигурацию для отладки
        interview_config = self._build_effective_config(interview)
        logger.info(f"[START_SESSION] interview_id={interview_id}, config keys: {list(interview_config.keys())}")
        logger.info(f"[START_SESSION] stages: {interview_config.get('stages', {})}")
        logger.info(f"[START_SESSION] questions_per_stage: {interview_config.get('questions_per_stage', interview_config.get('questionsPerStage', {}))}")
        logger.info(f"[START_SESSION] template_questions: {list(interview_config.get('template_questions', {}).keys()) if interview_config.get('template_questions') else 'None'}")
        
        # Инициализируем прогресс по стадиям
        stage_progress = InterviewStageManager.initialize_stage_progress(
            interview_config
        )
        
        logger.info(f"[START_SESSION] Initialized stage_progress: {stage_progress}")
        
        session = InterviewSession(
            interview_id=interview_id,
            candidate_id=candidate_id,
            status=InterviewStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
            current_stage=InterviewStage.READY_CHECK.value,  # Начинаем с проверки готовности
            stage_progress=stage_progress,
            emotion_history=[],
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        # Создаем начальный вопрос "Готовы ли вы начать?"
        from backend.models.interview import Question, QuestionType
        ready_question = Question(
            session_id=session.id,
            question_text="Здравствуйте! Готовы ли вы начать собеседование?",
            question_type=QuestionType.BEHAVIORAL,
            topic="ready_check",
            difficulty="easy",
            expected_keywords=[],
            hints=[],
            order=0,  # Нулевой порядок для начального вопроса
            shown_at=datetime.utcnow(),  # Записываем время показа вопроса
        )
        db.add(ready_question)
        db.commit()
        db.refresh(session)
        
        return session
    
    async def generate_question_for_session(
        self,
        db: Session,
        session_id: int,
        topic: Optional[str] = None
    ) -> Question:
        """Генерация вопроса для сессии с учетом текущей стадии"""
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        
        if not session:
            raise ValueError("Сессия не найдена")
        
        interview = session.interview
        interview_config = self._build_effective_config(interview)
        hr_prompt = interview_config.get("hr_prompt") or interview.hr_prompt or ""
        primary_language = self._resolve_primary_language(interview, interview_config)
        current_stage = session.current_stage or InterviewStage.INTRODUCTION.value
        
        # Устанавливаем current_stage, если его нет (для старых записей)
        if not session.current_stage:
            session.current_stage = InterviewStage.INTRODUCTION.value
            db.commit()
        
        # Получаем агента для текущей стадии
        agent = InterviewStageManager.get_agent_for_stage(current_stage)
        
        # Получение темы из собеседования или использование переданной
        if not topic:
            topic = self._resolve_topics(interview, interview_config)[0]
        
        # Формируем контекст для агента
        context = {
            "previous_questions": [],
            "previous_questions_scores": [],
            "stage": current_stage,
            "interview_config": interview_config,
        }
        
        stage_progress = session.stage_progress or {}
        stage_info = stage_progress.get(current_stage, {})
        context["stage_questions_asked"] = stage_info.get("questions_asked", 0)
        context["stage_questions_required"] = stage_info.get("questions_required", 0)
        context["stage_completed"] = stage_info.get("completed", False)
        
        def infer_stage_from_question(question: Question) -> str:
            """Определяем стадию, на которой был задан вопрос."""
            if question.topic == InterviewStage.READY_CHECK.value:
                return InterviewStage.READY_CHECK.value
            if question.topic == InterviewStage.SOFT_SKILLS.value:
                return InterviewStage.SOFT_SKILLS.value
            if question.question_type == QuestionType.CODING:
                return InterviewStage.LIVE_CODING.value
            if question.question_type == QuestionType.THEORY:
                return InterviewStage.TECHNICAL.value
            return InterviewStage.INTRODUCTION.value
        previous_questions_query = db.query(Question).filter(
            Question.session_id == session_id
        ).order_by(Question.order.asc()).all() # Берем все, чтобы построить историю
        
        for q in previous_questions_query:
            question_stage = infer_stage_from_question(q)
            context["previous_questions"].append({
                "question": q.question_text,
                "type": q.question_type.value if hasattr(q.question_type, "value") else str(q.question_type),
                "stage": question_stage,
            })
            # Ищем ответ на этот вопрос
            ans = db.query(Answer).filter(Answer.question_id == q.id).first()
            if ans and ans.score is not None:
                context["previous_questions_scores"].append(ans.score)
        
        # Проверяем, нужно ли генерировать follow-up вопрос для LIVE_CODING
        stage_info = session.stage_progress.get(current_stage, {})
        if current_stage == InterviewStage.LIVE_CODING.value and stage_info.get("followups_remaining", 0) > 0:
            # Генерируем follow-up вопрос по коду
            last_code = stage_info.get("last_code", "")
            # Используем CodingAgent для генерации вопроса по алгоритму
            # (импорт уже выполнен в начале файла)
            
            # Промпт для генерации follow-up вопроса
            prompt = f"""Кандидат решил задачу по программированию. Сгенерируй вопрос по алгоритму его решения.
            
            Код кандидата:
            ```
            {last_code}
            ```
            
            Задача агента:
            1. Проанализировать код.
            2. Задать вопрос про:
               - Временную сложность (Time Complexity)
               - Пространственную сложность (Space Complexity)
               - Выбор структур данных
               - Возможные оптимизации
            
            Вопрос должен быть коротким и конкретным.
            Формат ответа: JSON {{ "question": "текст вопроса" }}
            """
            
            try:
                response = await coding_agent.invoke(prompt)
                import json
                try:
                    result = json.loads(response)
                    question_text = result.get("question", response)
                except json.JSONDecodeError:
                    question_text = response
            except Exception as e:
                logger.error(f"Ошибка генерации follow-up вопроса: {e}")
                question_text = "Объясните алгоритмическую сложность вашего решения."

            question_type_enum = "THEORY"  # Это теоретический вопрос по коду
            question_data = {"question": question_text, "is_followup": True}

        # Генерация вопроса через соответствующего агента
        elif current_stage == InterviewStage.READY_CHECK.value:
            # Проверяем, есть ли уже вопрос готовности
            existing_ready_question = db.query(Question).filter(
                Question.session_id == session_id,
                Question.order == 0,
                Question.topic == "ready_check"
            ).first()
            
            if existing_ready_question:
                # Если вопрос уже существует, возвращаем его
                return existing_ready_question
            
            # Для проверки готовности используем шаблонный вопрос или вопрос от HR
            from backend.services.question_templates import get_hr_template_questions, get_template_question
            
            hr_questions = get_hr_template_questions(interview_config, "ready_check")
            if hr_questions and isinstance(hr_questions, list) and len(hr_questions) > 0:
                # Используем вопрос от HR
                hr_q = hr_questions[0]
                if isinstance(hr_q, dict):
                    question_text = hr_q.get("text") or hr_q.get("question", "Здравствуйте! Готовы ли вы начать собеседование?")
                else:
                    question_text = str(hr_q)
            else:
                # Используем встроенный шаблон
                template = get_template_question("ready_check")
                question_text = template["text"] if template else "Здравствуйте! Готовы ли вы начать собеседование?"
            
            question_type_enum = "BEHAVIORAL"
            question_data = {"question": question_text}
        
        elif current_stage == InterviewStage.INTRODUCTION.value:
            # Для этапа INTRODUCTION используем шаблонные вопросы из конфигуратора HR
            # Получаем вопросы от HR из конфигурации
            from backend.services.question_templates import get_hr_template_questions, get_template_question
            hr_questions = get_hr_template_questions(interview_config, "introduction")
            
            if hr_questions:
                # Используем вопросы от HR
                # Проверяем, какие вопросы уже заданы
                asked_questions = db.query(Question).filter(
                    Question.session_id == session_id,
                    Question.topic != "ready_check"
                ).all()
                asked_question_texts = [q.question_text for q in asked_questions]
                
                # Находим следующий неиспользованный вопрос от HR
                next_question = None
                for hr_q in hr_questions:
                    # Если это ID (строка), ищем по ID в шаблонах
                    if isinstance(hr_q, str):
                        # Это ID, пытаемся найти вопрос в шаблонах
                        template = get_template_question("introduction", question_id=hr_q, hr_questions=hr_questions)
                        if template and template.get("text") not in asked_question_texts:
                            next_question = template
                            break
                    elif isinstance(hr_q, dict):
                        # Это объект вопроса (из конфигуратора HR)
                        q_text = hr_q.get("text") or hr_q.get("question")
                        if q_text and q_text not in asked_question_texts:
                            next_question = hr_q
                            break
                
                if next_question:
                    question_text = next_question.get("text") or next_question.get("question", "")
                    question_type_enum = "BEHAVIORAL"
                    question_data = {
                        "question": question_text,
                        "template_id": next_question.get("id")
                    }
                else:
                    # Все вопросы от HR использованы, генерируем через агента
                    question_type = "experience"
                    question_data = await agent.process({
                        "action": "generate_question",
                        "question_type": question_type,
                        "context": context,
                        "interview_config": interview_config,
                        "hr_prompt": hr_prompt,
                    })
                    question_text = question_data.get("question", "")
                    question_type_enum = "BEHAVIORAL"
            else:
                # Нет вопросов от HR, используем встроенные шаблоны или генерируем
                template_questions = interview_config.get("template_questions", {})
                intro_question_ids = template_questions.get("introduction", [])
                
                if intro_question_ids:
                    # Используем встроенные шаблоны по ID
                    asked_question_ids = [
                        q.expected_keywords[0] if q.expected_keywords and len(q.expected_keywords) > 0 
                        else None
                        for q in asked_questions
                    ]
                    asked_question_ids = [qid for qid in asked_question_ids if qid]
                    
                    next_template_id = None
                    for qid in intro_question_ids:
                        if qid not in asked_question_ids:
                            next_template_id = qid
                            break
                    
                    if next_template_id:
                        template = get_template_question("introduction", question_id=next_template_id)
                        if template:
                            question_text = template["text"]
                            question_type_enum = "BEHAVIORAL"
                            question_data = {"question": question_text, "template_id": next_template_id}
                        else:
                            # Fallback на генерацию
                            question_type = "experience"
                            question_data = await agent.process({
                                "action": "generate_question",
                                "question_type": question_type,
                                "context": context,
                                "interview_config": interview_config,
                                "hr_prompt": hr_prompt,
                            })
                            question_text = question_data.get("question", "")
                            question_type_enum = "BEHAVIORAL"
                    else:
                        # Все шаблоны использованы
                        question_type = "experience"
                        question_data = await agent.process({
                            "action": "generate_question",
                            "question_type": question_type,
                            "context": context,
                            "interview_config": interview_config,
                            "hr_prompt": hr_prompt,
                        })
                        question_text = question_data.get("question", "")
                        question_type_enum = "BEHAVIORAL"
                else:
                    # Нет шаблонов, генерируем через агента
                    question_type = "experience"
                    question_data = await agent.process({
                        "action": "generate_question",
                        "question_type": question_type,
                        "context": context,
                        "interview_config": interview_config,
                        "hr_prompt": hr_prompt,
                    })
                    question_text = question_data.get("question", "")
                    question_type_enum = "BEHAVIORAL"
        
        elif current_stage == InterviewStage.SOFT_SKILLS.value:
            # Для этапа SOFT_SKILLS используем шаблонные вопросы из конфигуратора HR
            # Получаем вопросы от HR из конфигурации
            from backend.services.question_templates import get_hr_template_questions, get_template_question
            hr_questions = get_hr_template_questions(interview_config, "softSkills")
            
            if hr_questions:
                # Используем вопросы от HR
                # Проверяем, какие вопросы уже заданы
                asked_questions = db.query(Question).filter(
                    Question.session_id == session_id,
                    Question.topic == "softSkills"
                ).all()
                asked_question_texts = [q.question_text for q in asked_questions]
                
                # Находим следующий неиспользованный вопрос от HR
                next_question = None
                for hr_q in hr_questions:
                    # Если это ID (строка), ищем по ID в шаблонах
                    if isinstance(hr_q, str):
                        # Это ID, пытаемся найти вопрос в шаблонах
                        template = get_template_question("introduction", question_id=hr_q, hr_questions=hr_questions)
                        if template and template.get("text") not in asked_question_texts:
                            next_question = template
                            break
                    elif isinstance(hr_q, dict):
                        # Это объект вопроса (из конфигуратора HR)
                        q_text = hr_q.get("text") or hr_q.get("question")
                        if q_text and q_text not in asked_question_texts:
                            next_question = hr_q
                            break
                
                if next_question:
                    question_text = next_question.get("text") or next_question.get("question", "")
                    question_type_enum = "BEHAVIORAL"
                    question_data = {
                        "question": question_text,
                        "template_id": next_question.get("id")
                    }
                else:
                    # Все вопросы от HR использованы, генерируем через агента
                    question_type = "teamwork"
                    question_data = await agent.process({
                        "action": "generate_question",
                        "question_type": question_type,
                        "context": context,
                        "interview_config": interview_config,
                        "hr_prompt": hr_prompt,
                    })
                    question_text = question_data.get("question", "")
                    question_type_enum = "BEHAVIORAL"
            else:
                # Нет вопросов от HR, генерируем через агента
                question_type = "teamwork"
                question_data = await agent.process({
                    "action": "generate_question",
                    "question_type": question_type,
                    "context": context,
                    "interview_config": interview_config,
                "hr_prompt": hr_prompt,
                })
                question_text = question_data.get("question", "")
                question_type_enum = "BEHAVIORAL"
        
        elif current_stage == InterviewStage.TECHNICAL.value:
            question_data = await agent.process({
                "action": "generate_question",
                "topic": topic,
                "difficulty": interview.difficulty,
                "context": context, # Здесь передаются scores для адаптивности
                "interview_config": interview_config,
                "hr_prompt": hr_prompt,
            })
            question_text = question_data.get("question", "")
            question_type_enum = "THEORY"
            
            # Сохраняем время начала для технических вопросов (может быть код)
            if not session.stage_progress:
                session.stage_progress = {}
            session.stage_progress["coding_start_time"] = datetime.utcnow().isoformat()
        
        elif current_stage == InterviewStage.LIVE_CODING.value:
            question_data = await agent.process({
                "action": "generate_task",
                "topic": topic,
                "difficulty": interview.difficulty,
                "context": context,
                "interview_config": interview_config,
                "hr_prompt": hr_prompt,
            })
            question_text = question_data.get("question", "")
            question_type_enum = "CODING"
            
            # Сохраняем время начала написания кода в контексте сессии
            if not session.stage_progress:
                session.stage_progress = {}
            session.stage_progress["coding_start_time"] = datetime.utcnow().isoformat()
            
            # Сохраняем тестовые случаи в expected_keywords (временное решение)
            # В будущем можно добавить отдельное поле для test_cases
            test_cases = question_data.get("test_cases", [])
            if test_cases:
                import json
                # Сохраняем test_cases как JSON строки в expected_keywords
                test_cases_json = [json.dumps(tc, ensure_ascii=False) for tc in test_cases]
                question_data["expected_keywords"] = test_cases_json
        
        else:
            # Fallback на старый метод
            question_data = await self.ai_engine.generate_question(
                topic=topic,
                difficulty=interview.difficulty,
                question_type=current_stage,
                interview_config=interview_config  # Передаем конфигурацию
            )
            question_text = question_data.get("question", "")
            question_type_enum = "THEORY"
        
        # Подсчет порядка вопроса
        # Для вопроса готовности order=0, для остальных - начиная с 1
        if current_stage == InterviewStage.READY_CHECK.value:
            question_order = 0
        else:
            existing_questions = db.query(Question).filter(
                Question.session_id == session_id,
                Question.order > 0  # Исключаем вопрос готовности (order=0)
            ).count()
            question_order = existing_questions + 1
        
        # Создание вопроса в БД
        question = Question(
            session_id=session_id,
            question_text=question_text,
            question_type=QuestionType[question_type_enum],
            topic=(
                "ready_check" if current_stage == InterviewStage.READY_CHECK.value
                else "softSkills" if current_stage == InterviewStage.SOFT_SKILLS.value
                else topic
            ),
            difficulty=question_data.get("difficulty", interview.difficulty), # Используем динамическую сложность
            expected_keywords=question_data.get("expected_keywords", []),
            hints=question_data.get("hints", []),
            order=question_order,
            shown_at=datetime.utcnow(),  # Записываем время показа вопроса для расчета time_to_answer
        )
        
        db.add(question)
        
        # Обновляем прогресс по стадии (вопрос задан)
        # Инициализируем прогресс, если его нет
        if not session.stage_progress:
            session.stage_progress = InterviewStageManager.initialize_stage_progress(
                interview_config
            )
        
        # Проверяем, является ли вопрос follow-up (вспомогательным)
        # Если да, то не увеличиваем счетчик основных вопросов
        is_followup = question_data.get("is_followup", False)
        
        updated_progress = InterviewStageManager.update_stage_progress(
            session.stage_progress.copy() if session.stage_progress else {},
            current_stage,
            question_asked=not is_followup  # Не увеличиваем счетчик для follow-up
        )
        session.stage_progress = updated_progress
        
        # SQLAlchemy не отслеживает изменения в JSON полях автоматически
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "stage_progress")
        
        # Сохраняем изменения
        db.commit()
        db.refresh(session)
        
        # Проверяем, нужно ли перейти на следующую стадию
        # (не переходим сразу, ждем ответа кандидата)
        # Переход произойдет после отправки ответа в submit_answer
        
        db.refresh(question)
        
        return question
    
    async def submit_answer(
        self,
        db: Session,
        question_id: int,
        answer_text: Optional[str] = None,
        code_solution: Optional[str] = None,
        emotions: Optional[Dict[str, Any]] = None,  # Данные от GigaAM emo
        time_to_answer: Optional[float] = None,  # Время в секундах от показа вопроса до ответа
        typing_metrics: Optional[Dict[str, Any]] = None,  # Метрики печати
        activity_during_answer: Optional[List[Dict[str, Any]]] = None  # Активность во время ответа
    ) -> Answer:
        """Отправка ответа на вопрос с анализом эмоций в фоне"""
        question = db.query(Question).filter(Question.id == question_id).first()
        
        if not question:
            raise ValueError("Вопрос не найден")
        
        session = question.session
        interview = session.interview
        interview_config = self._build_effective_config(interview)
        primary_language = self._resolve_primary_language(interview, interview_config)
        current_stage = session.current_stage or InterviewStage.READY_CHECK.value
        
        # Устанавливаем current_stage, если его нет (для старых записей)
        if not session.current_stage:
            session.current_stage = InterviewStage.READY_CHECK.value
            db.commit()
        
        # Получаем агента для текущей стадии
        agent = InterviewStageManager.get_agent_for_stage(current_stage)
        
        # Валидация ответа на наличие AI-инъекций
        answer_content = answer_text or code_solution or ""
        
        # Проверка на явный отказ от ответа (skip logic)
        # Если кандидат пишет "дальше", "пропустить" и т.д., засчитываем 0 баллов без обращения к LLM
        # НО: НЕ применяем эту проверку к code_solution - код оценивается отдельно в coding_agent
        skip_keywords = [
            "дальше", "далее", "следующий", "следующий вопрос", "пропустить", "скип", "skip", "next", 
            "pass", "idk", "не знаю", "без понятия", "затрудняюсь ответить", "no answer",
            "все", "всё", "ok", "ок", "да", "нет", "+", "хз", "незнаю", "dunno"
        ]
        # Нормализуем ответ: убираем пробелы, приводим к нижнему регистру, убираем знаки препинания в конце
        normalized_answer = answer_content.lower().strip().rstrip(".,!?")
        
        # Проверка на пропуск:
        # 1. Очень короткий ответ (меньше 10 символов) - скорее всего не ответ
        # 2. Содержит ключевые слова пропуска
        # ВАЖНО: НЕ применяем к коду! Код оценивается в coding_agent
        is_very_short = len(normalized_answer) < 10
        contains_skip_keyword = (
            normalized_answer in skip_keywords or 
            any(normalized_answer.startswith(kw) for kw in skip_keywords) or
            any(normalized_answer.endswith(kw) for kw in skip_keywords)
        )
        
        # Если отправлен code_solution, НЕ применяем проверку на пропуск
        # Код будет оценен в coding_agent (он проверяет пустой код/заглушки)
        is_skip_request = (
            not code_solution and  # КРИТИЧНО: не применяем к коду!
            (is_very_short or contains_skip_keyword) and 
            len(normalized_answer) < 50
        )
        
        if is_skip_request and current_stage != InterviewStage.READY_CHECK.value:
            logger.info(f"[SKIP] Обнаружен пропуск вопроса (question_id={question_id}) пользователем: '{answer_content}'")
            logger.info(f"[SKIP] Текущая стадия: {current_stage}, session_id={session.id}")
            
            # Получаем прогресс для логирования
            skip_stage_progress = session.stage_progress or {}
            skip_stage_info = skip_stage_progress.get(current_stage, {})
            logger.info(f"[SKIP] Прогресс стадии: questions_asked={skip_stage_info.get('questions_asked', 0)}, questions_required={skip_stage_info.get('questions_required', 0)}")
            
            evaluation = {
                "score": 0,
                "correctness": 0,
                "completeness": 0,
                "quality": 0,
                "optimality": 0,
                "feedback": "", # Пустой фидбек для пропуска
                "strengths": [],
                "improvements": ["Отвечайте на вопросы, чтобы продемонстрировать знания."],
                "is_skip": True,
                "skip_reason": answer_content  # Сохраняем причину пропуска для отчета
            }
        else:
            # Если не пропуск, проводим валидацию
            validation_result = ai_injection_guard.validate_answer(
                answer_text=answer_content,
                question_text=question.question_text,
                current_stage=current_stage
            )
            
            # Если ответ невалидный из-за инъекции, выдаем предупреждение
            if not validation_result["is_valid"] and validation_result.get("should_warn"):
                logger.warning(
                    f"Обнаружена AI-инъекция в ответе кандидата {session.candidate_id}: "
                    f"{validation_result['reason']}"
                )
                
                # Увеличиваем счетчик предупреждений
                session.warning_count = (session.warning_count or 0) + 1
                
                # Сохраняем информацию о попытке манипуляции в anti-cheat
                if not session.ai_detection_results:
                    session.ai_detection_results = []
                
                session.ai_detection_results.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "question_id": question_id,
                    "injection_type": validation_result.get("injection_type"),
                    "confidence": validation_result.get("confidence"),
                    "reason": validation_result["reason"],
                })
                
                # Если это уже третья попытка манипуляции, помечаем сессию
                if session.warning_count >= 3:
                    session.suspicion_score = min(session.suspicion_score + 0.5, 1.0)
                    logger.error(
                        f"Кандидат {session.candidate_id} превысил лимит попыток манипуляции"
                    )
                
                # Возвращаем низкую оценку с предупреждением
                evaluation = {
                    "score": 0,
                    "correctness": 0,
                    "completeness": 0,
                    "quality": 0,
                    "optimality": 0,
                    "feedback": "", # Пустой фидбек при инъекции (безопасность)
                    "strengths": [],
                    "improvements": ["Предоставьте честный ответ на вопрос без попыток манипуляции"],
                    "is_injection_attempt": True,
                }
                
                # Сохраняем информацию и переходим к созданию ответа
                answer_content = validation_result.get("sanitized_answer", answer_content)
            
            # Если ответ невалидный по другим причинам (слишком короткий и т.д.)
            elif not validation_result["is_valid"]:
                logger.info(f"Невалидный ответ от кандидата: {validation_result['reason']}")
                evaluation = {
                    "score": 10,  # Минимальная оценка, но не 0
                    "correctness": 1,
                    "completeness": 1,
                    "quality": 1,
                    "optimality": 1,
                    "feedback": "", # Пустой фидбек
                    "strengths": [],
                    "improvements": ["Дайте более развернутый и полный ответ на вопрос"],
                }
                answer_content = validation_result.get("sanitized_answer", answer_content)

        # Если оценка уже сформирована (skip logic или injection), пропускаем вызовы агентов
        if 'evaluation' in locals() and evaluation is not None:
            pass
        
        # Для вопроса готовности не оцениваем ответ, просто принимаем
        elif current_stage == InterviewStage.READY_CHECK.value:
            evaluation = {
                "score": None,  # Не ставим оценку - вопрос готовности не учитывается
                "correctness": None,
                "completeness": None,
                "quality": None,
                "optimality": None,
                "feedback": "Спасибо за подтверждение готовности. Начинаем собеседование.",
                "strengths": [],
                "improvements": [],
                "is_ready_check": True,  # Помечаем как вопрос готовности
            }
        
        elif current_stage == InterviewStage.INTRODUCTION.value:
            question_subtype = "experience"
            result = await agent.process({
                "action": "evaluate_answer",
                "question": question.question_text,
                "answer": answer_content,
                "question_type": question_subtype,
            })
            evaluation = {
                "score": result.get("evaluation", 5) * 10,
                "correctness": result.get("evaluation", 5),
                "completeness": result.get("evaluation", 5),
                "quality": result.get("evaluation", 5),
                "optimality": 5,
                "feedback": self._sanitize_agent_feedback(result.get("feedback", "")),
                "strengths": result.get("strengths", []),
                "improvements": result.get("improvements", []),
                "extracted_info": result.get("extracted_info", {}),
                "needs_follow_up": result.get("needs_follow_up", False),
                "mentioned_projects": result.get("mentioned_projects", []),
            }
            
            # Если упомянуты проекты и нужен дополнительный вопрос, генерируем его
            if result.get("needs_follow_up", False) and result.get("mentioned_projects"):
                try:
                    follow_up_question = await agent.generate_follow_up_question(
                        previous_question=question.question_text,
                        previous_answer=answer_content,
                        extracted_info=result.get("extracted_info", {})
                    )
                    # Сохраняем информацию о необходимости дополнительного вопроса
                    evaluation["follow_up_question"] = follow_up_question.get("question")
                except Exception as e:
                    # Если метод не существует или ошибка, игнорируем
                    logger.debug(f"Не удалось сгенерировать дополнительный вопрос: {e}")
        
        elif current_stage == InterviewStage.TECHNICAL.value:
            # Если на этапе TECHNICAL отправлен код, оцениваем его как код
            if code_solution and len(code_solution.strip()) > 20:
                # Используем coding agent для оценки кода
                
                # Получаем тестовые случаи из вопроса (если есть)
                test_cases = []
                if question.expected_keywords:
                    try:
                        import json
                        for kw in question.expected_keywords:
                            if isinstance(kw, dict) and "input" in kw:
                                test_cases.append(kw)
                            elif isinstance(kw, str) and kw.startswith("{"):
                                test_case = json.loads(kw)
                                if "input" in test_case:
                                    test_cases.append(test_case)
                    except Exception:
                        pass
                
                # Получаем время начала написания кода из контекста сессии
                session_context = session.stage_progress or {}
                coding_start_time = session_context.get("coding_start_time")
                
                result = await coding_agent.process({
                    "action": "evaluate_code",
                    "question": question.question_text,
                    "code": code_solution,
                    "language": primary_language,
                    "test_cases": test_cases,
                    "start_time": coding_start_time,
                })
                evaluation = {
                    "score": result.get("score", 0),
                    "correctness": result.get("correctness", 0),
                    "completeness": result.get("readability", 5),
                    "quality": result.get("readability", 5),
                    "optimality": result.get("efficiency", 5),
                    "feedback": "", # Убираем фидбек для кода тоже
                    "strengths": result.get("strengths", []),
                    "improvements": result.get("improvements", []),
                    "test_results": result.get("test_results", []),
                    "performance": result.get("performance", 5),
                    "coding_speed": result.get("coding_speed", 5),
                    "tests_passed": result.get("tests_passed", 0),
                    "tests_total": result.get("tests_total", 0),
                    "tests_passed_ratio": result.get("tests_passed_ratio", 0),
                    "avg_execution_time": result.get("avg_execution_time", 0),
                }
            else:
                # Обычная оценка текстового ответа
                result = await agent.process({
                    "action": "evaluate_answer",
                    "question": question.question_text,
                    "answer": answer_content,
                    "expected_keywords": question.expected_keywords or [],
                })
                # Принудительно убираем feedback
                evaluation = {
                    "score": result.get("score", 50),
                    "correctness": result.get("correctness", 5),
                    "completeness": result.get("completeness", 5),
                    "quality": result.get("quality", 5),
                    "optimality": result.get("optimality", 5),
                    "feedback": "",  # ПРИНУДИТЕЛЬНО ПУСТОЙ ФИДБЕК
                    "strengths": result.get("strengths", []),
                    "improvements": result.get("improvements", []),
                }
        
        elif current_stage == InterviewStage.LIVE_CODING.value and code_solution:
            # Получаем тестовые случаи из вопроса (они должны быть сохранены при генерации)
            test_cases = []
            if question.expected_keywords:
                # Пытаемся извлечь test_cases из expected_keywords
                try:
                    import json
                    for kw in question.expected_keywords:
                        if isinstance(kw, dict) and "input" in kw:
                            test_cases.append(kw)
                        elif isinstance(kw, str) and kw.startswith("{"):
                            test_case = json.loads(kw)
                            if "input" in test_case:
                                test_cases.append(test_case)
                except Exception:
                    pass
            
            # Получаем время начала написания кода из контекста сессии
            session_context = session.stage_progress or {}
            coding_start_time = session_context.get("coding_start_time")
            
            result = await agent.process({
                "action": "evaluate_code",
                "question": question.question_text,
                "code": code_solution,
                "language": primary_language,
                "test_cases": test_cases if test_cases else (question.expected_keywords or []),
                "start_time": coding_start_time,
            })
            evaluation = {
                "score": result.get("score", 0),
                "correctness": result.get("correctness", 0),
                "completeness": result.get("readability", 5),
                "quality": result.get("readability", 5),
                "optimality": result.get("efficiency", 5),
                "feedback": self._sanitize_agent_feedback(result.get("feedback", "")),
                "strengths": result.get("strengths", []),
                "improvements": result.get("improvements", []),
                "test_results": result.get("test_results", []),
                "performance": result.get("performance", 5),
                "coding_speed": result.get("coding_speed", 5),
                "tests_passed": result.get("tests_passed", 0),
                "tests_total": result.get("tests_total", 0),
                "tests_passed_ratio": result.get("tests_passed_ratio", 0),
                "avg_execution_time": result.get("avg_execution_time", 0),
            }
        
        else:
            # Fallback на старый метод
            evaluation = await self.ai_engine.evaluate_answer(
                question=question.question_text,
                answer=answer_content,
                expected_keywords=question.expected_keywords,
                question_type=current_stage
            )
            if evaluation and "feedback" in evaluation:
                evaluation["feedback"] = self._sanitize_agent_feedback(evaluation["feedback"])
        
        # Анализ эмоций в фоновом режиме (если предоставлены данные от GigaAM emo)
        emotion_analysis = None
        if emotions:
            try:
                emotion_analysis = await emotion_agent.process({
                    "text": answer_content,
                    "emotions": emotions,
                    "context": {
                        "question": question.question_text,
                        "question_type": current_stage,
                        "session_id": session.id,
                    }
                })
                
                # Сохраняем в историю эмоций
                emotion_history = session.emotion_history or []
                emotion_history.append({
                    "question_id": question_id,
                    "emotion_analysis": emotion_analysis,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                session.emotion_history = emotion_history
            except Exception as e:
                # Не прерываем процесс, если анализ эмоций не удался
                logger.warning(f"Ошибка анализа эмоций: {e}")
        
        # Добавляем анализ эмоций в оценку
        if emotion_analysis:
            evaluation["emotion_analysis"] = emotion_analysis
        
        # Обновляем прогресс по стадии после ответа
        # Вопрос уже был задан при генерации, теперь он отвечен
        # Прогресс уже обновлен при генерации вопроса, но нужно проверить переход
        
        # Убеждаемся, что прогресс инициализирован
        if not session.stage_progress:
            session.stage_progress = InterviewStageManager.initialize_stage_progress(
                interview_config
            )
        
        # Сохраняем изменения перед проверкой перехода
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "stage_progress")
        db.commit()
        db.refresh(session)
        
        # Проверяем, нужно ли перейти на следующую стадию после ответа
        # Используем обновленный прогресс из БД
        current_progress = session.stage_progress or {}
        if InterviewStageManager.should_advance_stage(
            current_progress,
            current_stage,
            interview_config
        ):
            next_stage = InterviewStageManager.get_next_stage(current_stage, interview_config)
            if next_stage:
                session.current_stage = next_stage
                updated_progress = InterviewStageManager.complete_stage(
                    current_progress.copy(),
                    current_stage
                )
                session.stage_progress = updated_progress
                flag_modified(session, "stage_progress")
                db.commit()
                db.refresh(session)
        
        # Создание ответа
        # Для вопроса готовности score = None (не учитывается в оценке)
        answer = Answer(
            question_id=question_id,
            answer_text=answer_text,
            code_solution=code_solution,
            score=evaluation.get("score"),  # Может быть None для вопроса готовности
            evaluation=evaluation,
            time_to_answer=time_to_answer,
            typing_speed=typing_metrics.get("typingSpeed") if (typing_metrics and isinstance(typing_metrics, dict)) else None,
            activity_during_answer=activity_during_answer,
        )
        
        db.add(answer)
        db.commit()
        db.refresh(answer)
        
        # Запускаем фоновую обработку ответа для структурирования (если доступна)
        if ANSWER_PROCESSOR_AVAILABLE and answer_content and len(answer_content) > 10:
            try:
                # Определяем тип вопроса для процессора
                question_type_for_processor = current_stage
                if current_stage == InterviewStage.READY_CHECK.value:
                    question_type_for_processor = "ready_check"
                
                # Запускаем фоновую обработку (fire and forget)
                answer_processor.schedule_processing(
                    db=db,
                    answer_id=answer.id,
                    question_text=question.question_text,
                    answer_text=answer_content,
                    question_type=question_type_for_processor
                )
                logger.info(f"[INTERVIEW_SERVICE] Запущена фоновая обработка ответа {answer.id}")
            except Exception as e:
                # Не прерываем основной процесс, если фоновая обработка не удалась
                logger.warning(f"[INTERVIEW_SERVICE] Не удалось запустить фоновую обработку: {e}")
        
        # Проверяем, нужно ли генерировать следующий вопрос
        
        # Если текущий вопрос был follow-up, уменьшаем счетчик
        stage_info = session.stage_progress.get(session.current_stage, {})
        current_followups = stage_info.get("followups_remaining", 0)
        
        if current_followups > 0:
             # Если мы здесь, значит ответ на follow-up получен
             # Уменьшаем счетчик
             stage_info["followups_remaining"] = current_followups - 1
             
             # Если follow-up еще остались, генерируем следующий
             if stage_info["followups_remaining"] > 0:
                 flag_modified(session, "stage_progress")
                 db.commit()
                 await self.generate_question_for_session(db, session.id)
                 return answer
             
             # Если follow-up закончились, сбрасываем контекст кода и продолжаем стандартный поток
             if stage_info["followups_remaining"] == 0:
                 stage_info.pop("last_code", None)
                 flag_modified(session, "stage_progress")
                 db.commit()
                 # Продолжаем выполнение, чтобы проверить переход на след. стадию или завершение
        
        # Если текущий ответ - это код (LIVE_CODING), инициируем follow-up вопросы
        if current_stage == InterviewStage.LIVE_CODING.value and code_solution:
            # Устанавливаем количество follow-up вопросов (1-2)
            stage_info["followups_remaining"] = 2
            stage_info["last_code"] = code_solution
            flag_modified(session, "stage_progress")
            db.commit()
            
            # Генерируем первый follow-up вопрос
            await self.generate_question_for_session(db, session.id)
            return answer

        # После получения ответа автоматически генерируем следующий вопрос
        # (если это не был последний вопрос и интервью не завершено)
        try:
            # Проверяем, нужно ли генерировать следующий вопрос
            session = question.session
            interview = session.interview
            effective_config = self._build_effective_config(interview)
            
            # Получаем все вопросы сессии
            all_questions = db.query(Question).filter(
                Question.session_id == session.id
            ).all()
            
            # Получаем все ответы
            all_answers = db.query(Answer).join(Question).filter(
                Question.session_id == session.id
            ).all()
            
            # Если на все вопросы есть ответы, не генерируем новый вопрос
            questions_with_answers = {a.question_id for a in all_answers}
            unanswered_questions = [q for q in all_questions if q.id not in questions_with_answers]
            
            # Исключаем вопрос готовности из проверки (он уже должен быть отвечен)
            unanswered_except_ready = [q for q in unanswered_questions if q.order > 0]
            
            # Если есть неотвеченные вопросы (кроме только что отвеченного), не генерируем новый
            if len(unanswered_except_ready) > 0:
                return answer
            
            # Если это был вопрос готовности, переходим к первой активной стадии
            if session.current_stage == InterviewStage.READY_CHECK.value:
                # Получаем следующую активную стадию из конфигурации
                next_stage = InterviewStageManager.get_next_stage(
                    InterviewStage.READY_CHECK.value,
                    effective_config
                )
                
                if next_stage:
                    session.current_stage = next_stage
                    logger.info(f"[READY_CHECK] Переход от ready_check к {next_stage}")
                else:
                    # Если нет следующей стадии, используем introduction по умолчанию
                    session.current_stage = InterviewStage.INTRODUCTION.value
                    logger.warning(f"[READY_CHECK] Нет следующей стадии в конфиге, переход к introduction")
                
                db.commit()
                
                # Генерируем первый реальный вопрос
                await self.generate_question_for_session(db, session.id)
                return answer
            
            # Проверяем, нужно ли генерировать следующий вопрос
            # Генерируем только если:
            # 1. Интервью еще не завершено
            # 2. Есть еще вопросы для текущей стадии
            # 3. Это не был последний вопрос
            
            if session.status == InterviewStatus.IN_PROGRESS:
                # Проверяем прогресс по стадиям
                stage_progress = session.stage_progress or {}
                current_stage = session.current_stage
                stage_info = stage_progress.get(current_stage, {})
                questions_asked = stage_info.get("questions_asked", 0)
                questions_required = stage_info.get("questions_required", 0)
                
                logger.debug(f"[STAGE_CHECK] current_stage={current_stage}, questions_asked={questions_asked}, questions_required={questions_required}")
                
                # Если еще есть вопросы для текущей стадии, генерируем следующий
                # ВАЖНО: если questions_required == 0, это значит стадия не требует вопросов - нужно переходить дальше
                if questions_required > 0 and questions_asked < questions_required:
                    # Генерируем следующий вопрос
                    await self.generate_question_for_session(db, session.id)
                else:
                    # Переходим на следующую стадию, если есть
                    next_stage = InterviewStageManager.get_next_stage(current_stage, effective_config)
                    if next_stage:
                        session.current_stage = next_stage
                        session.stage_progress = InterviewStageManager.complete_stage(
                            session.stage_progress,
                            current_stage
                        )
                        db.commit()
                        
                        # Генерируем первый вопрос новой стадии
                        await self.generate_question_for_session(db, session.id)
                    else:
                        # Если следующей стадии нет, и все вопросы отвечены - завершаем интервью
                        # Проверяем, действительно ли все вопросы отвечены (включая follow-up)
                        if stage_info.get("followups_remaining", 0) == 0:
                            logger.info(f"Интервью {session.id} завершено автоматически.")
                            await self.complete_session(db, session.id)
                            
        except Exception as e:
            # Не прерываем процесс, если не удалось сгенерировать следующий вопрос
            logger.debug(f"Не удалось автоматически сгенерировать следующий вопрос: {e}")
        
        return answer
    
    async def complete_session(
        self,
        db: Session,
        session_id: int,
        wait_for_pdf: bool = False
    ) -> InterviewSession:
        """Завершение сессии собеседования с анализом Mercor AI v2.0.0
        
        Args:
            db: Сессия базы данных
            session_id: ID сессии интервью
            wait_for_pdf: Ждать завершения генерации PDF (для тестов)
        """
        from backend.services.soft_skills_analyzer import soft_skills_analyzer
        from backend.services.prediction_engine import prediction_engine
        from backend.services.communication_automation import communication_automation
        from backend.models.user import User
        
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        
        if not session:
            raise ValueError("Сессия не найдена")
        
        # Подсчет общей оценки
        # Отчет генерируется даже если интервью завершено досрочно
        # Исключаем вопрос готовности из подсчета оценки
        answers = db.query(Answer).join(Question).filter(
            Question.session_id == session_id,
            Question.topic != "ready_check"  # Исключаем вопрос готовности
        ).all()
        
        if answers:
            # Вычисляем среднюю оценку только по ответам с оценками
            scored_answers = [a for a in answers if a.score is not None]
            if scored_answers:
                total_score = sum(a.score for a in scored_answers) / len(scored_answers)
                session.total_score = total_score
            else:
                # Если есть ответы, но без оценок, устанавливаем 0
                session.total_score = 0.0
        else:
            # Если нет ответов (досрочное завершение), устанавливаем 0
            session.total_score = 0.0
        
        # Получаем кандидата один раз для всех операций
        candidate = db.query(User).filter(User.id == session.candidate_id).first()
        
        # Mercor AI v2.0.0: Анализ soft skills
        if candidate:
            try:
                soft_skills_analysis = await soft_skills_analyzer.analyze_session(db, session_id)
                candidate.soft_skills_score = soft_skills_analysis
                # Расчет culture fit
                culture_fit = await soft_skills_analyzer.calculate_culture_fit(soft_skills_analysis)
                candidate.culture_fit_score = culture_fit
            except Exception as e:
                logger.warning(f"Ошибка анализа soft skills: {e}")
            
            # Mercor AI v2.0.0: Прогнозирование успешности
            try:
                prediction = await prediction_engine.predict_success(db, candidate.id)
                candidate.success_prediction = prediction
            except Exception as e:
                logger.warning(f"Ошибка прогнозирования: {e}")

        # v4.2.0: Финальная оценка LLM (Technical + Soft Skills + Verdict)
        try:
            from backend.services.agents.report_agent import report_agent
            from backend.services.report_service import report_service
            
            # Получаем данные для оценки (используем метод экспорта из report_service)
            interview_data = report_service.export_session_to_json(db, session_id)
            
            # Запускаем оценку
            logger.info(f"Запуск финальной LLM оценки для сессии {session_id}")
            evaluation_result = await report_agent.evaluate_candidate(
                interview_data=interview_data,
                interview_config=self._build_effective_config(session.interview) if session.interview else None
            )
            
            # Сохраняем результат в сессию
            session.ai_evaluation = evaluation_result
            
            # Если вердикт "RECOMMENDED", можем обновить статус заявки
            if evaluation_result.get("verdict") == "RECOMMENDED":
                # Логика обновления статуса кандидата
                pass
                
        except Exception as e:
            logger.error(f"Ошибка финальной LLM оценки: {e}", exc_info=True)
        
        session.status = InterviewStatus.COMPLETED
        session.completed_at = datetime.utcnow()
        
        # Chat & Invitations v2.0.0: Обновляем статус приглашения на "completed"
        try:
            from backend.models.message import InterviewInvitation
            invitation = db.query(InterviewInvitation).filter(
                InterviewInvitation.interview_id == session.interview_id,
                InterviewInvitation.candidate_id == session.candidate_id,
                InterviewInvitation.status == "accepted"
            ).first()
            
            if invitation:
                invitation.status = "completed"
        except Exception as e:
            logger.warning(f"Ошибка обновления статуса приглашения: {e}")
        
        db.commit()
        db.refresh(session)
        
        # Mercor AI v2.0.0: Отправка уведомления
        if candidate and candidate.email:
            try:
                await communication_automation.send_interview_completed_notification(
                    candidate.email,
                    session.interview.title,
                    session.total_score
                )
            except Exception as e:
                logger.warning(f"Ошибка отправки уведомления: {e}")
        
        # v3.0.0: Автоматическая генерация PDF отчета при завершении
        # Генерируем отчет в фоновом режиме (не блокируем ответ)
        # Используем отдельный поток для генерации PDF
        try:
            # Проверяем доступность reportlab перед импортом
            try:
                import reportlab
            except ImportError:
                logger.debug("reportlab не установлен, пропускаем генерацию PDF отчета")
                return session
            
            from backend.services.report_service import report_service
            import threading
            
            def generate_report_async():
                try:
                    # Создаем новую сессию БД для фонового потока
                    from backend.database import SessionLocal
                    background_db = SessionLocal()
                    try:
                        report_service.generate_pdf_report(background_db, session.id)
                    finally:
                        background_db.close()
                except Exception as e:
                    logger.warning(f"Не удалось сгенерировать PDF отчет в фоне: {e}")
            
            # Запускаем в отдельном потоке
            thread = threading.Thread(target=generate_report_async, daemon=True)
            thread.start()
            
            # Для тестов: ждем завершения генерации PDF
            if wait_for_pdf:
                logger.info(f"Ожидание завершения генерации PDF (timeout: 15 сек)...")
                thread.join(timeout=15)
                if thread.is_alive():
                    logger.warning("Генерация PDF не завершилась за 15 секунд")
                else:
                    logger.info("Генерация PDF завершена")
                    # Обновляем сессию из БД чтобы получить cached_pdf_path
                    db.refresh(session)
        except Exception as e:
            logger.warning(f"Не удалось запустить генерацию PDF отчета: {e}")
            # Не прерываем процесс, если генерация отчета не удалась
        
        return session


# Глобальный экземпляр
interview_service = InterviewService()
