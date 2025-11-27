"""
Сервис для генерации отчетов о собеседованиях
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload

from backend.models import InterviewSession, Question, Answer, User, Interview
from backend.utils.report_generator import ReportGenerator
from backend.services.agents.report_agent import report_agent
from backend.utils.logger import get_module_logger

logger = get_module_logger("ReportService")


class ReportService:
    """Сервис для генерации отчетов"""
    
    def __init__(self, reports_dir: Optional[str] = None):
        """
        Инициализация сервиса отчетов
        
        Args:
            reports_dir: Директория для сохранения отчетов (опционально)
        """
        # Если директория не указана, используем backend/reports
        if reports_dir is None:
            backend_dir = Path(__file__).parent.parent
            reports_dir = str(backend_dir / "reports")
        
        self.reports_dir = reports_dir
        # Создаем директорию, если она не существует
        Path(self.reports_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"Директория отчетов: {self.reports_dir}")
        
        self._initialize_pdf_generator()
    
    def _initialize_pdf_generator(self):
        """Инициализация PDF генератора"""
        try:
            # Проверяем доступность reportlab перед созданием генератора
            try:
                import reportlab
                import sys
                logger.info(f"reportlab обнаружен (версия: {reportlab.Version}, Python: {sys.executable})")
            except ImportError as e:
                self.report_generator = None
                self.pdf_available = False
                import sys
                logger.warning(
                    f"PDF генератор недоступен: reportlab не установлен в {sys.executable}. "
                    f"Установите: pip install reportlab>=4.0.0"
                )
                return
            
            self.report_generator = ReportGenerator(output_dir=self.reports_dir)
            self.pdf_available = True
            logger.info(f"PDF генератор инициализирован (директория: {self.reports_dir})")
        except ImportError as e:
            # reportlab не установлен
            self.report_generator = None
            self.pdf_available = False
            import sys
            logger.warning(f"PDF генератор недоступен: {e} (Python: {sys.executable})")
        except Exception as e:
            # Другие ошибки при инициализации
            self.report_generator = None
            self.pdf_available = False
            logger.error(f"Ошибка инициализации PDF генератора: {e}", exc_info=True)
    
    def export_session_to_json(
        self,
        db: Session,
        session_id: int
    ) -> Dict[str, Any]:
        """
        Экспорт данных сессии интервью в JSON формат
        
        Args:
            db: Сессия базы данных
            session_id: ID сессии интервью
            
        Returns:
            Словарь с данными сессии в формате для генератора PDF
        """
        # Загружаем сессию с связанными данными
        session = db.query(InterviewSession).options(
            joinedload(InterviewSession.candidate),
            joinedload(InterviewSession.interview),
            joinedload(InterviewSession.questions).joinedload(Question.answers)
        ).filter(InterviewSession.id == session_id).first()
        
        if not session:
            raise ValueError(f"Сессия {session_id} не найдена")
        
        # Получаем кандидата
        candidate = session.candidate
        if not candidate:
            logger.error(f"Кандидат не найден для сессии {session_id} (candidate_id={session.candidate_id})")
            raise ValueError(f"Кандидат не найден для сессии {session_id}")
        
        # Получаем интервью
        interview = session.interview
        if not interview:
            logger.error(f"Интервью не найдено для сессии {session_id} (interview_id={session.interview_id})")
            raise ValueError(f"Интервью не найдено для сессии {session_id}")
        
        # Формируем список вопросов и ответов
        # Исключаем вопрос готовности из отчета (он служит только для старта)
        questions_answers = []
        for question in sorted(session.questions, key=lambda q: q.order):
            # Пропускаем вопрос готовности - он не является частью интервью
            if question.topic == "ready_check":
                continue
                
            # Получаем ответ (может быть несколько, берем первый)
            answer = question.answers[0] if question.answers else None
            
            # Получаем тип вопроса
            question_type = question.question_type
            if hasattr(question_type, 'value'):
                question_type_str = question_type.value
            else:
                question_type_str = str(question_type)
            
            qa_data = {
                "question_id": question.id,
                "question_text": question.question_text or "",
                "question_type": question_type_str,
                "topic": question.topic or "",
                "difficulty": question.difficulty or "medium",
                "order": question.order,
            }
            
            if answer:
                qa_data["answer_text"] = answer.answer_text if answer.answer_text else None
                qa_data["code_solution"] = answer.code_solution if answer.code_solution else None
                qa_data["score"] = float(answer.score) if answer.score is not None else 0.0
                
                # Обработка evaluation (может быть JSON строка или dict)
                evaluation = answer.evaluation
                if isinstance(evaluation, str):
                    try:
                        evaluation = json.loads(evaluation)
                    except (json.JSONDecodeError, TypeError):
                        evaluation = {}
                elif evaluation is None:
                    evaluation = {}
                elif not isinstance(evaluation, dict):
                    # Если это не dict и не строка, пытаемся преобразовать
                    try:
                        evaluation = dict(evaluation) if hasattr(evaluation, '__iter__') else {}
                    except:
                        evaluation = {}
                
                qa_data["evaluation"] = evaluation
                
                # Явно добавляем маркеры о пропуске и статусе ответа
                qa_data["is_skipped"] = evaluation.get("is_skip", False)
                qa_data["is_answered"] = True
                qa_data["skip_reason"] = evaluation.get("skip_reason", None) if qa_data["is_skipped"] else None
            else:
                qa_data["answer_text"] = None
                qa_data["code_solution"] = None
                qa_data["score"] = 0.0
                qa_data["evaluation"] = {}
                qa_data["is_skipped"] = False
                qa_data["is_answered"] = False
                qa_data["skip_reason"] = None
            
            questions_answers.append(qa_data)
        
        # Определяем, было ли интервью завершено досрочно
        # Досрочное завершение = есть вопросы, но нет ответов на некоторые или все вопросы
        # Вопрос готовности уже исключен из questions_answers, поэтому считаем только реальные вопросы
        total_questions = len(questions_answers)
        answered_questions = len([qa for qa in questions_answers if qa.get("is_answered", False)])
        skipped_questions = len([qa for qa in questions_answers if qa.get("is_skipped", False)])
        is_early_completion = total_questions > 0 and answered_questions < total_questions
        
        # Формируем итоговый JSON
        result = {
            "candidate_name": candidate.full_name or candidate.username or "Неизвестно",
            "candidate_email": candidate.email or "",
            "interview_title": interview.title or "Интервью",
            "interview_date": (
                session.completed_at.isoformat() 
                if session.completed_at 
                else session.started_at.isoformat() 
                if session.started_at 
                else datetime.now().isoformat()
            ),
            "total_score": float(session.total_score) if session.total_score is not None else 0.0,
            "is_early_completion": is_early_completion,
            "total_questions": total_questions,
            "answered_questions": answered_questions,
            "skipped_questions": skipped_questions,  # Количество пропущенных вопросов
            "questions_answers": questions_answers,
            # Данные античита
            "suspicion_score": float(session.suspicion_score) if session.suspicion_score is not None else 0.0,
            "typing_metrics": session.typing_metrics,
            "ai_detection_results": session.ai_detection_results
        }
        
        # ОПТИМИЗАЦИЯ: Пропускаем AI оценку при экспорте для быстрой генерации
        # AI оценка уже должна быть в БД после завершения интервью
        # Если нужна новая оценка, можно добавить параметр force_evaluate=True
        
        # Проверяем, есть ли уже сохраненная оценка в сессии
        if hasattr(session, 'ai_evaluation') and session.ai_evaluation:
            try:
                if isinstance(session.ai_evaluation, str):
                    result["evaluation"] = json.loads(session.ai_evaluation)
                else:
                    result["evaluation"] = session.ai_evaluation
                logger.info("Используем сохраненную AI оценку из БД")
            except Exception as e:
                logger.warning(f"Не удалось загрузить сохраненную оценку: {e}")
                result["evaluation"] = None
        else:
            # Если оценки нет в БД, можем её не делать для ускорения
            # или сделать это асинхронно в фоновом режиме
            logger.info("AI оценка не найдена в БД, пропускаем для ускорения генерации отчета")
            result["evaluation"] = None
            
        # ПРИМЕЧАНИЕ: Для получения свежей AI оценки можно добавить отдельный эндпоинт
        # который будет генерировать её асинхронно и сохранять в БД
        
        return result
    
    def generate_pdf_report(
        self,
        db: Session,
        session_id: int,
        output_filename: Optional[str] = None,
        force_regenerate: bool = False
    ) -> str:
        """
        Генерация PDF отчета для сессии интервью
        
        Args:
            db: Сессия базы данных
            session_id: ID сессии интервью
            output_filename: Имя выходного файла (опционально)
            force_regenerate: Принудительно пересоздать отчет (игнорировать кеш)
            
        Returns:
            Путь к созданному PDF файлу
            
        Raises:
            ImportError: Если reportlab не установлен
        """
        if not self.pdf_available or self.report_generator is None:
            raise ImportError(
                "reportlab не установлен. Установите его командой: pip install reportlab>=4.0.0"
            )
        
        # ОПТИМИЗАЦИЯ: Проверяем, существует ли уже PDF отчет для этой сессии
        if not force_regenerate:
            existing_pdf = self._find_existing_pdf(session_id)
            if existing_pdf:
                logger.info(f"Используем кешированный PDF отчет для сессии {session_id}: {existing_pdf}")
                return existing_pdf
        
        # Экспортируем данные в JSON
        json_data = self.export_session_to_json(db, session_id)
        
        # Сохраняем во временный JSON файл
        # Используем output_dir из генератора или дефолтный путь
        if self.report_generator:
            reports_dir = self.report_generator.output_dir
        else:
            reports_dir = Path(self.reports_dir)
        reports_dir.mkdir(exist_ok=True)
        temp_json_path = reports_dir / f"temp_session_{session_id}.json"
        temp_json_path.parent.mkdir(exist_ok=True)
        
        with open(temp_json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        try:
            # Генерируем PDF
            pdf_path = self.report_generator.generate_pdf(
                str(temp_json_path),
                output_filename
            )
            
            # ОПТИМИЗАЦИЯ: Сохраняем путь к PDF в кеш
            self._save_pdf_cache(session_id, pdf_path)
            
            return pdf_path
        finally:
            # Удаляем временный JSON файл
            try:
                if temp_json_path.exists():
                    temp_json_path.unlink()
            except (PermissionError, OSError) as e:
                # Игнорируем ошибки удаления файла (может быть занят другим процессом)
                logger.debug(f"Не удалось удалить временный файл {temp_json_path}: {e}")
    
    def _find_existing_pdf(self, session_id: int) -> Optional[str]:
        """
        Поиск существующего PDF отчета для сессии в БД
        
        Args:
            session_id: ID сессии интервью
            
        Returns:
            Путь к PDF файлу или None если не найден
        """
        # Импортируем здесь, чтобы избежать циклических зависимостей
        from backend.database import SessionLocal
        from backend.models import InterviewSession
        
        try:
            db = SessionLocal()
            session = db.query(InterviewSession).filter(
                InterviewSession.id == session_id
            ).first()
            
            if session and session.cached_pdf_path:
                pdf_path = Path(session.cached_pdf_path)
                # Проверяем, существует ли файл
                if pdf_path.exists():
                    logger.info(f"Найден кешированный PDF для сессии {session_id}: {session.cached_pdf_path}")
                    return str(pdf_path)
                else:
                    # Файл был удален, обновляем БД
                    logger.warning(f"Кешированный PDF не существует: {session.cached_pdf_path}")
                    session.cached_pdf_path = None
                    db.commit()
            
            return None
        except Exception as e:
            logger.error(f"Ошибка при поиске кешированного PDF: {e}")
            return None
        finally:
            if 'db' in locals():
                db.close()
    
    def _save_pdf_cache(self, session_id: int, pdf_path: str) -> None:
        """
        Сохранение пути к PDF в кеш БД
        
        Args:
            session_id: ID сессии интервью
            pdf_path: Путь к PDF файлу
        """
        from backend.database import SessionLocal
        from backend.models import InterviewSession
        
        try:
            db = SessionLocal()
            session = db.query(InterviewSession).filter(
                InterviewSession.id == session_id
            ).first()
            
            if session:
                session.cached_pdf_path = pdf_path
                db.commit()
                logger.info(f"PDF путь сохранен в кеш для сессии {session_id}: {pdf_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении PDF в кеш: {e}")
        finally:
            if 'db' in locals():
                db.close()


# Глобальный экземпляр сервиса
report_service = ReportService()

# Если reportlab был установлен после первого импорта, можно переинициализировать
def reinitialize_report_service():
    """Переинициализация сервиса отчетов (например, после установки reportlab)"""
    global report_service
    report_service._initialize_pdf_generator()
    return report_service

